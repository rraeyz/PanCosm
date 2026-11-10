//! Compiled routines (plans/architecture.md ARC-9). Conventions: float64 inputs, the GIL released while working,
//! threads through rayon, results independent of the thread count, no panic crosses into Python.

use numpy::{PyArray1, PyReadonlyArray1};
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

#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(kepler_e, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;
    Ok(())
}
