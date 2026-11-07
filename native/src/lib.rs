//! Compiled routines (plans/architecture.md ARC-9). Conventions: float64 inputs, the GIL released while working,
//! threads through rayon, results independent of the thread count, no panic crosses into Python.

use numpy::{PyArray1, PyReadonlyArray1, PyReadonlyArray2, PyUntypedArrayMethods};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use rayon::prelude::*;

const PARALLEL_ABOVE: usize = 20_000;

/// Eccentric anomaly E of mean anomaly m for eccentricity e (Kepler's equation m = E - e sin E):
/// Danby's starting value, then Halley steps to 1e-14 rad (at most 60).
fn kepler_one(m: f64, e: f64) -> f64 {
    if !m.is_finite() {
        return f64::NAN;
    }
    use std::f64::consts::{PI, TAU};
    let m = m - TAU * (m / TAU).floor(); // 0 <= m < 2 pi, cheaper than fmod
    let mut big_e = m + if m < PI { 0.85 * e } else { -0.85 * e }; // the sign of sin m without a sine
    for _ in 0..60 {
        let (s, c) = big_e.sin_cos();
        let f = big_e - e * s - m;
        let f1 = 1.0 - e * c;
        let d = f / (f1 - 0.5 * f * e * s / f1); // Halley: cubic convergence, the same sin and cos
        big_e -= d;
        if d.abs() < 1e-14 {
            break;
        }
    }
    big_e
}

#[pyfunction]
fn kepler_e<'py>(py: Python<'py>, m: PyReadonlyArray1<'py, f64>, e: f64) -> PyResult<Bound<'py, PyArray1<f64>>> {
    if !(0.0..1.0).contains(&e) {
        return Err(PyValueError::new_err(format!("eccentricity {e} is outside 0 <= e < 1")));
    }
    let m = m.as_slice()?.to_vec();
    let out = py.detach(move || {
        std::panic::catch_unwind(move || {
            if m.len() > PARALLEL_ABOVE {
                m.par_iter().map(|&x| kepler_one(x, e)).collect::<Vec<f64>>()
            } else {
                m.iter().map(|&x| kepler_one(x, e)).collect::<Vec<f64>>()
            }
        })
    });
    match out {
        Ok(v) => Ok(PyArray1::from_vec(py, v)),
        Err(_) => Err(PyValueError::new_err("the compiled Kepler solver failed")),
    }
}

/// Median of the first `c` (>= 1) values of a sorted slice, as compute/combine._median_sorted: (lo + hi) * 0.5 in f32.
fn sorted_median(xs: &[f32], c: usize) -> f32 {
    (xs[(c - 1) / 2] + xs[c / 2]) * 0.5f32
}

/// One pixel of compute/combine._cpu_block: the median / MAD-clipped mean of its frames and the count kept.
/// Every step in the twin's order and precision (f32 bounds, an f64 sum in frame order), so both agree exactly.
fn clipped_one(col: &mut [f32], buf: &mut Vec<f32>, sigma: f32, maxiters: u32) -> (f32, i32) {
    for v in col.iter_mut() {
        if !v.is_finite() {
            *v = f32::NAN;
        }
    }
    let (mut lo, mut hi) = (f32::NEG_INFINITY, f32::INFINITY);
    let (mut last_lo, mut last_hi) = (lo, hi);
    let mut prev: Option<usize> = None;
    let mad_to_std = 1.482602218505602f32;
    for it in 0..=maxiters {
        buf.clear();
        buf.extend(col.iter().copied().filter(|&v| v >= lo && v <= hi));
        let cnt = buf.len();
        if it == maxiters || prev == Some(cnt) {
            break;
        }
        prev = Some(cnt);
        let (med, scale) = if cnt == 0 {
            (f32::NAN, f32::NAN)
        } else {
            buf.sort_unstable_by(|a, b| a.partial_cmp(b).unwrap()); // equal floats are the same value
            let med = sorted_median(buf, cnt);
            for v in buf.iter_mut() {
                *v = (*v - med).abs();
            }
            buf.sort_unstable_by(|a, b| a.partial_cmp(b).unwrap()); // equal floats are the same value
            (med, mad_to_std * sorted_median(buf, cnt))
        };
        last_lo = med - sigma * scale;
        last_hi = med + sigma * scale;
        lo = lo.max(last_lo); // f32::max ignores NaN, as np.fmax
        hi = hi.min(last_hi);
    }
    let mut sum = 0.0f64;
    let mut cnt = 0i32;
    for &v in col.iter() {
        if v >= last_lo && v <= last_hi {
            sum += v as f64;
            cnt += 1;
        }
    }
    ((sum / cnt as f64) as f32, cnt)
}

/// stack (n frames, npix) float32 -> (clipped mean, count kept) per pixel, every pixel on its own (rayon).
#[pyfunction]
fn clipped_mean<'py>(
    py: Python<'py>,
    stack: PyReadonlyArray2<'py, f32>,
    sigma: f32,
    maxiters: u32,
) -> PyResult<(Bound<'py, PyArray1<f32>>, Bound<'py, PyArray1<i32>>)> {
    let shape = stack.shape();
    let (n, npix) = (shape[0], shape[1]);
    let data = stack.as_slice()?.to_vec();
    let out = py.detach(move || {
        std::panic::catch_unwind(move || {
            (0..npix)
                .into_par_iter()
                .map_init(
                    || (vec![0f32; n], Vec::with_capacity(n)),
                    |(col, buf), i| {
                        for f in 0..n {
                            col[f] = data[f * npix + i];
                        }
                        clipped_one(col, buf, sigma, maxiters)
                    },
                )
                .unzip::<f32, i32, Vec<f32>, Vec<i32>>()
        })
    });
    match out {
        Ok((mean, cnt)) => Ok((PyArray1::from_vec(py, mean), PyArray1::from_vec(py, cnt))),
        Err(_) => Err(PyValueError::new_err("the compiled clipped mean failed")),
    }
}

fn theta(x: f64, d: f64, ra: f64) -> f64 {
    // occult/flux.py's _theta: the half-angle of the circle of radius x behind the occulter
    if d == 0.0 {
        return if x < ra { std::f64::consts::PI } else { 0.0 };
    }
    if x >= d + ra || d >= x + ra {
        return 0.0;
    }
    if x + d <= ra {
        return std::f64::consts::PI;
    }
    let c = (x * x + d * d - ra * ra) / (2.0 * x * d);
    c.clamp(-1.0, 1.0).acos()
}

/// z (separations), k, quadratic u1 u2, Gauss-Legendre nodes and weights -> the occulted fraction of the flux,
/// the same quadrature as occult/flux.py's occulted_fraction (its NumPy twin).
#[pyfunction]
fn occulted_quadratic<'py>(
    py: Python<'py>,
    z: PyReadonlyArray1<'py, f64>,
    k: f64,
    u1: f64,
    u2: f64,
    nodes: PyReadonlyArray1<'py, f64>,
    weights: PyReadonlyArray1<'py, f64>,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let z = z.as_slice()?;
    let (nodes, weights) = (nodes.as_slice()?, weights.as_slice()?);
    let half_pi = 0.5 * std::f64::consts::PI;
    let norm = std::f64::consts::PI * (1.0 - u1 / 3.0 - u2 / 6.0);
    // the nodes' angles are the same for every z: their cosine and sine once (the twin's arithmetic, in its order)
    let trig: Vec<(f64, f64, f64)> = nodes
        .iter()
        .zip(weights.iter())
        .map(|(n, w)| {
            let phi = half_pi * (n + 1.0);
            (phi.cos(), phi.sin(), *w)
        })
        .collect();
    let out: Vec<f64> = z
        .iter()
        .map(|&zz| {
            let d = zz.abs();
            if !(d < k + 1.0) || k <= 0.0 {
                return 0.0;
            }
            let mut edges = [0.0, (d - k).abs().clamp(0.0, 1.0), (d + k).clamp(0.0, 1.0), 1.0];
            edges.sort_by(|a, b| a.partial_cmp(b).unwrap());
            let mut total = 0.0;
            for j in 0..3 {
                let (a, b) = (edges[j], edges[j + 1]);
                let mut part = 0.0;
                if b <= a {
                    continue; // an empty piece adds nothing
                }
                for &(cos_phi, sin_phi, w) in trig.iter() {
                    let x = a + 0.5 * (b - a) * (1.0 - cos_phi);
                    let mu = (1.0 - x * x).clamp(0.0, 1.0).sqrt();
                    let i = 1.0 - u1 * (1.0 - mu) - u2 * (1.0 - mu) * (1.0 - mu);
                    part += i * 2.0 * x * theta(x, d, k) * 0.5 * (b - a) * sin_phi * w;
                }
                total += part * half_pi;
            }
            total / norm
        })
        .collect();
    Ok(PyArray1::from_vec(py, out))
}

#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(kepler_e, m)?)?;
    m.add_function(wrap_pyfunction!(clipped_mean, m)?)?;
    m.add_function(wrap_pyfunction!(occulted_quadratic, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;
    Ok(())
}
