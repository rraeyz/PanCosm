"""Spectrum tools tab: stellar-parameter fit, opening, reading and combining spectra."""

from pathlib import Path

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QFileDialog

from . import spectro_figures
from .messages import translate as translate_error

SPECTRA = "Spectra (*.fits *.fit *.fts *.txt *.dat *.csv *.asc)"
translate = QCoreApplication.translate


class SpectrumFiles:
    """Mixed into SpectrumToolsTab; its texts are translated in the SpectrumToolsTab context."""

    # --- stellar parameters ----------------------------------------------------
    def _atmosphere(self):
        if self.wave is None:
            self.status.setText(translate("SpectrumToolsTab", "Open a spectrum first."))
            return
        if not self.resolution.value():
            self.status.setText(translate("SpectrumToolsTab", "Give the spectrograph's resolution R first."))
            return
        path = self.path
        if self.history:  # changed here (cleaned, cut, ...): the fit uses what is shown
            import tempfile

            from ..spectroscopy import spectrum_io

            path = str(Path(tempfile.mkdtemp()) / Path(self.path).name)
            spectrum_io.write(path, self.wave, self.flux, np.full_like(self.flux, np.nan), self.header)
        inputs = {"spectrum": path} | ({"sun": self.sun_file.text()} if self.sun_file.text().strip() else {})
        self.status.setText(
            translate("SpectrumToolsTab", "Fitting stellar parameters (the first time, model spectra are downloaded)…")
        )
        self.atmosphere_requested.emit(inputs, {"resolution": self.resolution.value()})

    def show_atmosphere(self, o):
        e = o["errors"]
        text = translate("SpectrumToolsTab",
            "Teff = {t:.0f} ± {et:.0f} K, log g = {g:.2f} ± {eg:.2f}, [Fe/H] = {z:+.2f} ± {ez:.2f}, "
            "v sin i = {v:.1f} ± {ev:.1f} km/s, RV = {rv:.2f} ± {erv:.2f} km/s. Relative to the Sun fitted the same "
            "way; {pct:.0f} % of the pixels used (where the models reproduce the Sun); χ²ᵣ = {chi:.2f}."
        ).format(
            t=o["teff"], et=e["teff"], g=o["logg"], eg=e["logg"], z=o["feh"], ez=e["feh"], v=o["vsini"],
            ev=e["vsini"], rv=o["rv"], erv=e["rv"], pct=100 * o["used_fraction"], chi=o["chi2_red"],
        )  # fmt: skip
        if o["far_from_sun"]:
            text += " " + translate(
                "SpectrumToolsTab", "This star is far from the Sun: the solar reference is less reliable here."
            )
        if o["at_edge"]:
            text += " " + translate("SpectrumToolsTab", "The fit stopped at the edge of the model grid.")
        text += " " + translate("SpectrumToolsTab", "So far checked on the Sun only; see the guide before publishing.")
        self.status.setText(text)
        self.plot.set_figure(spectro_figures.atmosphere_figure(o["plot"]))

    # --- data ----------------------------------------------------------------
    def _read(self, path):
        from ..spectroscopy import spectrum_io

        try:
            return spectrum_io.read(path)
        except (OSError, ValueError, IndexError) as e:
            self.status.setText(
                translate("SpectrumToolsTab", "Cannot read {file}: {error}").format(
                    file=Path(path).name, error=translate_error(e)
                )
            )
            return None

    def _open(self, path=None):
        path = path or QFileDialog.getOpenFileName(self, translate("SpectrumToolsTab", "Open spectrum"), "", SPECTRA)[0]
        if not path:
            return False
        got = self._read(path)
        if got is None:
            return False
        self.wave, self.flux, _, self.header = got
        self.wave, self.flux = np.asarray(self.wave, float), np.asarray(self.flux, float)
        self.path, self.history, self.points, self.last = path, [], [], None
        self.undo_stack.clear()  # another spectrum: earlier steps do not apply to it
        text = translate("SpectrumToolsTab", "{file}: {n} points, {a:.1f}–{b:.1f} Å").format(
            file=Path(path).name, n=self.wave.size, a=self.wave.min(), b=self.wave.max()
        )
        if "converted to air" in str(self.header.comments["VACUUM"] if "VACUUM" in self.header else ""):
            text += " " + translate("SpectrumToolsTab", "(vacuum wavelengths in the file, converted to air)")
        self.source.setText(text)
        self._plot()
        self.guide.reset()
        self.guide.set_state(0, "done")
        return True

    def _combine(self, paths=None):
        paths = (
            paths
            or QFileDialog.getOpenFileNames(self, translate("SpectrumToolsTab", "Combine exposures"), "", SPECTRA)[0]
        )
        if len(paths) < 2:
            if paths:
                self.source.setText(translate("SpectrumToolsTab", "Choose at least two exposures to combine."))
            return False
        first = Path(paths[0])
        output = first.with_name(f"{first.stem.removesuffix('.fits')}_combined{len(paths)}.fits")
        self.source.setText(translate("SpectrumToolsTab", "Combining {n} exposures…").format(n=len(paths)))
        self.combine_requested.emit({"spectra": [str(p) for p in paths], "output": str(output)}, {})
        return True

    def show_combined(self, out):
        """The combined spectrum opened here, with what was done and any warning."""
        if not self._open(out["path"]):
            return
        text = (
            self.source.text()
            + "\n"
            + translate("SpectrumToolsTab", "{n} exposures combined, {r} pixels rejected.").format(
                n=out["count"], r=out["rejected"]
            )
        )
        for warning in out.get("warnings") or []:
            warning = translate_error(warning)
            text += "\n⚠ " + warning[:1].upper() + warning[1:]
        self.source.setText(text)

    def _open_b(self, path=None):
        path = path or QFileDialog.getOpenFileName(self, translate("SpectrumToolsTab", "Spectrum B"), "", SPECTRA)[0]
        got = self._read(path) if path else None
        if got:
            self.b = (np.asarray(got[0], float), np.asarray(got[1], float))
            self.status.setText(translate("SpectrumToolsTab", "Spectrum B: {file}").format(file=Path(path).name))
