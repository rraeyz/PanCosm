"""The frame's photometric zero point from catalogue stars (plans/images.md IMG-5): M − m = ZP (+ T · colour),
fitted with weights and 3σ clipping, its error, the residuals for the plot, and the header keywords other programs
read (MAGZP, MAGZPERR, ZPCAT).

    zp = fit(inst_mag, cat_mag, colour=None, err=None)   {"zp", "zp_err", "colour_term", "colour_term_err", "rms",
                                                          "used", "residuals"}
    write(header, zp, "Gaia DR3")
"""

import numpy as np


def fit(inst_mag, cat_mag, colour=None, err=None, clip=3.0):
    m, cat = np.asarray(inst_mag, float), np.asarray(cat_mag, float)
    y = cat - m
    w = np.ones_like(y) if err is None else 1.0 / np.square(np.asarray(err, float))
    cols = [np.ones_like(y)] + ([np.asarray(colour, float)] if colour is not None else [])
    a = np.column_stack(cols)
    ok = np.isfinite(y) & np.all(np.isfinite(a), axis=1) & np.isfinite(w)
    if ok.sum() < len(cols) + 2:
        raise ValueError("too few catalogue stars on the frame for a zero point")
    for _ in range(10):
        sw = np.sqrt(w[ok])
        coef, *_ = np.linalg.lstsq(a[ok] * sw[:, None], y[ok] * sw, rcond=None)
        res = y - a @ coef
        scale = np.sqrt(np.sum(w[ok] * res[ok] ** 2) / max(ok.sum() - len(cols), 1))
        new = ok & (np.abs(res) * np.sqrt(w) <= clip * scale)
        if np.array_equal(new, ok):
            break
        ok = new
    sw = np.sqrt(w[ok])
    cov = np.linalg.inv((a[ok] * sw[:, None]).T @ (a[ok] * sw[:, None])) * scale**2
    out = {"zp": float(coef[0]), "zp_err": float(np.sqrt(cov[0, 0])), "rms": float(np.std(res[ok])),
           "used": ok, "residuals": res}  # fmt: skip
    if colour is not None:
        out |= {"colour_term": float(coef[1]), "colour_term_err": float(np.sqrt(cov[1, 1]))}
    return out


def write(header, zp, catalogue):
    header["MAGZP"] = (round(zp["zp"], 4), "zero point: M = m_inst + MAGZP")
    header["MAGZPERR"] = (round(zp["zp_err"], 4), "its 1-sigma error")
    header["ZPCAT"] = (str(catalogue), "catalogue of the zero point")
    if "colour_term" in zp:
        header["MAGZPCT"] = (round(zp["colour_term"], 4), "colour term of the zero point")
    return header
