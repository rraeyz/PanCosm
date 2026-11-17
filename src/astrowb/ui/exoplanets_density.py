"""The stellar-density line of the Exoplanets window's Results stage (plans/interface.md UI-16.7)."""

from PySide6.QtCore import QCoreApplication

from ..photometry.stellar_density import stellar_density

translate = QCoreApplication.translate


def density_line(out, period, expected=0.0):
    """ "Stellar density: x ± y g/cm³ (z ρ☉)"; with an expected ρ★ (g/cm³, 0: none) also the σ apart."""
    d = stellar_density(out, period)
    text = translate("ExoplanetsPage", "Stellar density: {rho:.2f} ± {err:.2f} g/cm³ ({sun:.2f} ρ☉)").format(
        rho=d["rho"], err=d["err"], sun=d["rho_sun"]
    )
    if expected > 0 and d["err"] > 0:
        text += " " + translate("ExoplanetsPage", "{n:.1f}σ from the expected {exp:.2f} g/cm³.").format(
            n=abs(d["rho"] - expected) / d["err"], exp=expected
        )
    return text
