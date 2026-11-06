"""The hand-overs between areas and the steps they start (calibrate, photometry, period, minima, spectra,
automations): a mixin of MainWindow moved out of main_window.py (plans/architecture.md ARC-4.4); texts keep the
main window's translation context."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication

from . import automatic

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("MainWindow", "…") calls


class AreaActions:
    """Methods of MainWindow (self is the main window)."""

    def send_to_photometry(self, paths, ask=True):
        """Images to the Photometry window, which is then shown. Several filters: one light curve per filter, so the
        user picks the filter (the largest group first)."""
        from PySide6.QtWidgets import QInputDialog

        from .calibrate_page import by_filter

        paths = [str(p) for p in paths if p]
        if not paths:
            return None
        groups = by_filter(paths)
        all_paths = None
        if len(groups) > 1 and ask:
            names = sorted(groups, key=lambda k: -len(groups[k]))
            labels = [translate("MainWindow", "{f} ({n} images)").format(f=k or "—", n=len(groups[k])) for k in names]
            both = translate(
                "MainWindow", "All of them: a curve per filter and the colour index (stars marked in {f})"
            ).format(f=names[0] or "—")  # item 11
            question = translate("MainWindow", "A light curve is measured in one filter. Which one?")
            label, ok = QInputDialog.getItem(
                self, translate("MainWindow", "Filter"), question, [*labels, both], 0, False
            )
            if not ok:
                return None
            if label == both:
                all_paths, paths = paths, groups[names[0]]
            else:
                paths = groups[names[labels.index(label)]]
        elif len(groups) > 1:
            paths = max(groups.values(), key=len)
        self.photometry_page.set_images(paths)
        self.photometry_page.all_filter_images = all_paths
        self.show_workspace("photometry")
        return paths

    def photometry_from_image(self, x, y, comparison=False):
        """Start photometry from the Images page: the open images (or the shown one) go to the Photometry window with
        this star as the target, or add it as a comparison star."""
        phot = self.photometry_page
        if not comparison:
            paths = self.image_page.open_paths() or [str(self.current_path)]
            phot.set_images(paths if str(self.current_path) in paths else [str(self.current_path)])
            if str(phot.images[0]) != str(self.current_path):  # stars are marked on the first frame in time
                self.statusBar().showMessage(
                    translate(
                        "MainWindow", "Click the target on the first image in time, shown in the Photometry window."
                    ),
                    10000,
                )
                self.show_workspace("photometry")
                return False
            phot.target = (x, y)
        else:
            phot.comps.append((x, y))
        phot._draw_markers()
        if not comparison:
            self.show_workspace("photometry")
        return True

    def measure_light_curve(self, images, target, comps, coord, params):
        inputs = {"images": images, "target_xy": target, "comps_xy": comps}
        if coord:
            inputs["coord"] = coord
        params = dict(params)
        if params.get("extra_xy"):  # check stars and further targets are inputs of the step
            inputs["extra_xy"] = params.pop("extra_xy")
        params.pop("extra_xy", None)
        if params.get("ref_image"):  # the frame the stars were marked on
            inputs["ref_image"] = params.pop("ref_image")
        params.pop("ref_image", None)

        def done(out):
            lc = out["light_curve"]
            self.photometry_page.show_light_curve(lc)
            if automatic.on("timeseries.take_light_curve"):  # else it goes when Period search → is pressed
                self._light_curve_to_period(lc)

        every = getattr(self.photometry_page, "all_filter_images", None)
        if every:  # item 11: every filter of the night, and the colour index

            def done_all(out):
                from .calibrate_page import by_filter

                main = next(iter(by_filter(images)), "")  # the filter the stars were marked in
                curves = out["curves"]
                done({"light_curve": curves.get(main) or next(iter(curves.values()))})
                self.photometry_page.show_colour(out["colour"], curves)

            inputs["images"] = list(every)
            return self.run_step("photometry.multifilter", inputs, params, on_done=done_all, area="photometry")
        return self.run_step("photometry.light_curve", inputs, params, on_done=done, area="photometry")

    def search_period(self, time, flux, params):
        params = dict(params)
        inputs = {"time": time, "flux": flux}
        if params.get("err") is not None:
            inputs["err"] = params.pop("err")
        params.pop("err", None)
        return self.run_step(
            "timeseries.period", inputs, params, on_done=self.period_page.show_result, area="timeseries"
        )

    def time_minimum(self, light_curve, params):
        pp, page = self.period_page, self.photometry_page
        if "period" not in params and pp.best and pp.time and len(pp.time) == len(light_curve["time"]):
            params = params | {"period": float(pp.best), "t0": float(pp._t0())}  # from the period search just made
            page.period.setText(f"{params['period']:.8f}")
            page.t0.setText(f"{params['t0']:.6f}")

        def done(out):
            m = out["minimum"]
            page.show_minimum(m)
            page.last_minima = m.get("minima", [m])  # for "Add to the O−C list" when that is not automatic
            for x in m.get("minima", [m]) if automatic.on("oc.take_minima") else ():  # ready for the O-C diagram
                self.oc_page.add_minimum(x["time"], x["error"], "this work", x.get("kind", "I"))
            obj = (page.field or {}).get("object") or {}
            if obj.get("in_field") and not self.oc_page.star.text():  # the star the files name, for Look up
                self.oc_page.star.setText(obj["name"])
            if params.get("t0") and not self.oc_page.t0.text():
                self.oc_page.t0.setText(repr(params["t0"]))
                self.oc_page.period.setText(repr(params["period"]))

        return self.run_step(
            "timeseries.minimum", {"light_curve": light_curve}, params, on_done=done, area="photometry"
        )

    def resolve_target(self, name):
        from ..settings import config_dir

        return self.run_step(
            "planning.resolve",
            {"name": name, "cache_file": str(config_dir() / "targets.json")},
            on_done=lambda out: self.plan_page.add_target(out["target"]),
            on_fail=self.plan_page.status.setText,
        )

    def lookup_ephemeris(self, name):
        return self.run_step(
            "planning.ephemeris",
            {"name": name},
            on_done=lambda out: self.plan_page.add_target(out["target"]),
            on_fail=self.plan_page.status.setText,
        )

    def _light_curve_to_period(self, lc):
        self.period_page.set_light_curve(
            lc["time"], lc["rel_flux"], translate("MainWindow", "the Photometry window"), err=lc.get("rel_flux_err")
        )

    def _photometry_next(self, where, path):
        """From a measured light curve to the page that fits it (the period page has the curve unless the user turned
        that off in Settings → Automatic steps: then it goes now)."""
        if (
            where == "timeseries"
            and self.photometry_page.light_curve
            and not automatic.on("timeseries.take_light_curve")
        ):
            self._light_curve_to_period(self.photometry_page.light_curve)
        if where == "orbits" and path:
            self.models_page.file.edit.setText(path)
        self.show_workspace(where)

    def _spectrum_done(self, spectrum):
        self.spectro_page.reduce_tab.show_spectrum(spectrum)
        if spectrum.get("path"):
            if self.engine.project:
                self.engine.project.add_file(Path(spectrum["path"]), "spectrum")
            if automatic.on("spectroscopy.take_spectra"):
                self.spectro_page.velocity_tab.add_files([spectrum["path"]])  # ready for radial velocities

    def _echelle_done(self, result):
        self.spectro_page.echelle_tab.show_result(result)
        if result.get("path"):
            if self.engine.project:
                self.engine.project.add_file(Path(result["path"]), "spectrum")
            if automatic.on("spectroscopy.take_spectra"):
                self.spectro_page.velocity_tab.add_files([result["path"]])

    def _telluric_done(self, result):
        self.spectro_page.telluric_tab.show_result(result)
        if result.get("path") and self.engine.project:
            self.engine.project.add_file(Path(result["path"]), "spectrum")

    def scan_raw(self, folder, lights=""):
        if folder or lights:
            inputs = {"folder": folder or ""}
            if lights:
                inputs["lights"] = lights
            return self.run_step(
                "calibration.scan",
                inputs,
                {"clock_utc_offset": self.calibrate_page.clock_offset.value()},
                on_done=lambda out: self.calibrate_page.show_frames(
                    out["frames"], out["problems"], out.get("raw_converted", 0)
                ),
                area="calibrate",
            )

    def calibrate(self, frames, output_dir, params):
        def done(out):
            if self.engine.project:
                for p in out["masters"]:
                    self.engine.project.add_file(Path(p), "master")
                for p in out["calibrated"]:
                    self.engine.project.add_file(Path(p), "calibrated")
            self.calibrate_page.show_result(out)
            if out["calibrated"] and not self.photometry_page.images:  # next step of the workflow is ready
                from .calibrate_page import by_filter

                groups = by_filter(out["calibrated"])  # one filter only; a colour camera's green (TG) first
                self.photometry_page.set_images(groups.get("TG") or max(groups.values(), key=len))

        return self.run_step(
            "calibration.run", {"frames": frames, "output_dir": output_dir}, params, on_done=done, area="calibrate"
        )

    def run_automation(self, auto, inputs):
        """Run an automation task by task: each step starts when the previous one has finished."""
        from ..engine import automation

        gen, page, n = automation.calls(auto, inputs), self.automation_page, [0]

        def advance(out=None):
            try:
                call = next(gen) if out is None else gen.send(out)
                n[0] += 1
                page.step_started(n[0], call[0])
                self.run_step(*call, on_done=advance, on_fail=page.failed)  # a failed step stops the chain
            except StopIteration as stop:
                page.finished(stop.value, out)
            except Exception as e:  # a link to a missing field, a refused input: say where it stopped
                page.failed(str(e))

        advance()

    def _load_sequence(self, target):
        self.observe_page.load_sequence(target)
        self.show_workspace("observe")
