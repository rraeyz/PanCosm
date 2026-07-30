"""Files for the Wilson-Devinney (WD) program: observations in WD's columns and a starting-parameter sheet
under WD's parameter names, from a light-curve fit (and a double-lined orbit when there is one).

The surface potentials come from the fitted radii (fractions of the separation) through the Roche potential
of a synchronous, circular orbit, at each star's pole:
    star 1:  Omega1 = 1/r1 + q / sqrt(1 + r1^2)
    star 2:  Omega2 = q/r2 + 1/sqrt(1 + r2^2) + (1 - q)/2     (Wilson 1979 transformation, q = M2/M1)
shortcut: the fitted radii are volume-equivalent, used here as polar radii (within ~1 % for detached stars);
WD refines them anyway. The deck layout (lcin.active) differs between WD versions, so the values are given
as a sheet to type into the version you use; temperatures, albedos and gravity darkening are left for you.
"""

from pathlib import Path

import numpy as np


def omega1(r1, q):
    return 1.0 / r1 + q / np.sqrt(1.0 + r1**2)


def omega2(r2, q):
    return q / r2 + 1.0 / np.sqrt(1.0 + r2**2) + (1.0 - q) / 2.0


def write_wd_files(folder, t, flux, err, fit, q=None, rv=None, orbit=None):
    """lc.dat (HJD/BJD, flux, weight), rv1.dat / rv2.dat, wd_parameters.txt; returns the paths."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    t, flux = np.asarray(t, float), np.asarray(flux, float)
    sig = np.full(len(t), np.nanstd(flux) or 1.0) if err is None else np.asarray(err, float)
    w = 1.0 / sig**2
    w /= np.nanmedian(w)  # WD wants relative weights
    written = [folder / "lc.dat"]
    np.savetxt(written[0], np.column_stack([t, flux, w]), fmt="%14.6f %11.6f %8.3f")
    if rv:
        for comp in ("1", "2"):
            if rv.get("v" + comp) is not None:
                e = rv.get("e" + comp)
                rw = np.ones(len(rv["t"])) if e is None else 1.0 / np.asarray(e, float) ** 2
                path = folder / f"rv{comp}.dat"
                np.savetxt(
                    path,
                    np.column_stack([rv["t"], np.asarray(rv["v" + comp]) / 100.0, rw / np.median(rw)]),
                    fmt="%14.6f %11.5f %8.3f",
                )  # WD velocities in units of 100 km/s
                written.append(path)
    p, d = fit["params"], fit["derived"]
    lines = [
        "# Wilson-Devinney starting values (type them into your WD version's input deck).",
        "# Observations: lc.dat = time, flux, weight; rv1.dat / rv2.dat = time, velocity / (100 km/s), weight.",
        f"PERIOD  {p['period']:.8f}      # days",
        f"HJD0    {p['t0']:.6f}      # time of primary minimum (same time system as the data: BJD_TDB if so)",
        f"XINCL   {p['incl']:.4f}        # degrees",
        f"E       {d['e']:.5f}",
        f"PERR0   {np.radians(d['omega']):.5f}        # radians",
        f"EL3     {p['l3']:.4f}          # third light, fraction of the total (set L3 PERC accordingly)",
    ]
    if q:
        lines += [
            f"RM      {q:.5f}          # q = M2 / M1",
            f"PHSV    {omega1(d['r1'], q):.5f}        # potential of star 1 (from r1 = {d['r1']:.5f})",
            f"PCSV    {omega2(d['r2'], q):.5f}        # potential of star 2 (from r2 = {d['r2']:.5f})",
        ]
    else:
        lines.append(
            "# RM, PHSV, PCSV: need the mass ratio q (a double-lined orbit); r1 = "
            f"{d['r1']:.5f}, r2 = {d['r2']:.5f} of the separation"
        )
    if orbit:
        lines.append(f"VGA     {orbit.get('gamma', 0.0) / 100.0:.5f}        # systemic velocity / (100 km/s)")
        if orbit.get("a"):
            lines.append(f"A       {orbit['a']:.4f}         # separation, solar radii")
    lines += [
        "# Not known from this fit: TAVH, TAVC (temperatures), ALB1/ALB2, GR1/GR2, limb-darkening law and",
        f"# coefficients for your band; surface brightness ratio J = {p['j']:.4f} (from the fit) helps choose TAVC.",
    ]
    sheet = folder / "wd_parameters.txt"
    sheet.write_text("\n".join(lines) + "\n", encoding="utf-8")
    written.append(sheet)
    return [str(x) for x in written]
