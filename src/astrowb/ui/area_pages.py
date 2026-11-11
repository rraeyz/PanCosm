"""The area pages that need the main window's wiring (tasks, hand-overs between areas), built the first time they
are shown; moved out of main_window.py (plans/architecture.md ARC-4.4). Texts keep the main window's translation
context ("MainWindow")."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication

from .messages import translate
from .workspaces import ImagePage, LightCurvePage, OCPage, PhotometryPage


def make_spectro_page(main):
    from .spectro_page import SpectroscopyPage  # imported with its page: start-up stays fast

    page = SpectroscopyPage(main, main.settings)
    rt, vt, et, tt = page.reduce_tab, page.velocity_tab, page.echelle_tab, page.telluric_tab
    rt.reduce_requested.connect(
        lambda inputs, params: main.run_step_for(
            "spectroscopy",
            "spectroscopy.reduce",
            inputs,
            params,
            on_done=lambda out: main._spectrum_done(out["spectrum"]),
            on_fail=rt.status.setText,  # not "Working…" behind an error box
        )
    )
    et.reduce_requested.connect(
        lambda inputs, params: main.run_step_for(
            "spectroscopy",
            "spectroscopy.echelle",
            inputs,
            params,
            on_done=lambda out: main._echelle_done(out["echelle"]),
            on_fail=et.status.setText,
        )
    )
    et.orders_requested.connect(
        lambda inputs, params: main.run_step_for(
            "spectroscopy",
            "spectroscopy.orders",
            inputs,
            params,
            on_done=lambda out: et.show_orders(out["orders"]),
            on_fail=et.status.setText,
        )
    )
    tt.correct_requested.connect(
        lambda inputs, params: main.run_step_for(
            "spectroscopy",
            "spectroscopy.telluric",
            inputs,
            params,
            on_done=lambda out: main._telluric_done(out["telluric"]),
            on_fail=tt.status.setText,
        )
    )
    vt.rv_requested.connect(
        lambda inputs, params: main.run_step_for(
            "spectroscopy",
            "spectroscopy.rv",
            inputs | ({"site": main.settings.get("site")} if main.settings.get("site") else {}),
            params,
            on_done=lambda out: vt.show_rvs(out["rvs"], out.get("skipped")),
            on_fail=vt.status.setText,
        )
    )
    vt.disentangle_requested.connect(
        lambda inputs, params: main.run_step_for(
            "spectroscopy",
            "spectroscopy.disentangle",
            inputs,
            params,
            on_done=lambda out: vt.show_components(out["components"]),
            on_fail=vt.status.setText,
        )
    )
    page.tools_tab.combine_requested.connect(
        lambda inputs, params: main.run_step_for(
            "spectroscopy",
            "spectroscopy.combine",
            inputs,
            params,
            on_done=lambda out: page.tools_tab.show_combined(out["combined"]),
            on_fail=page.tools_tab.source.setText,
        )
    )
    page.tools_tab.atmosphere_requested.connect(
        lambda inputs, params: main.run_step_for(
            "spectroscopy",
            "spectroscopy.atmosphere",
            inputs | {"cache": str(main.settings.path.parent / "phoenix")},
            params,
            on_done=lambda out: page.tools_tab.show_atmosphere(out["atmosphere"]),
        )
    )
    vt.classify_requested.connect(
        lambda spectrum: main.run_step_for(
            "spectroscopy",
            "spectroscopy.classify",
            {"spectrum": spectrum, "library": str(main.settings.path.parent / "templates")},
            {},
            on_done=lambda out: vt.show_classes(
                out["classes"], out.get("mk"), out.get("mk_note"), out.get("mk_model"), out.get("classes_note")
            ),
        )
    )
    vt.orbit_requested.connect(
        lambda inputs, params: main.run_step_for(
            "spectroscopy",
            "spectroscopy.orbit",
            inputs,
            params,
            on_done=lambda out: (vt.show_orbit(out["orbit"]), main.models_page.set_orbit(out["orbit"])),
            on_fail=vt.status.setText,
        )
    )
    return page


def make_models_page(main):
    from .models_page import ModelsPage  # imported with its page: start-up stays fast

    page = ModelsPage(main)
    page.fit_requested.connect(
        lambda inputs, params: main.run_step_for(
            "orbits",
            "models.eb_fit",
            inputs,
            params,
            on_done=lambda out: page.show_fit(out["model"]),
            on_fail=page.status.setText,
        )
    )
    page.visual_tab.fit_requested.connect(
        lambda inputs, params: main.run_step_for(
            "orbits",
            "models.visual_orbit",
            inputs,
            params,
            on_done=lambda out: page.visual_tab.show_orbit(out["orbit"]),
            on_fail=page.visual_tab.status.setText,
        )
    )
    return page


def make_photometry_page(main):
    page = PhotometryPage(main)
    page.measure_requested.connect(main.measure_light_curve)
    page.catalog_requested.connect(
        lambda inputs, params: main.run_step(
            "photometry.catalog",
            inputs,
            params,
            on_done=lambda out: page.show_catalog(out["catalog"]),
            area="photometry",
        )
    )
    page.quality_requested.connect(
        lambda images: main.run_step(
            "photometry.quality",
            {"images": images},
            {},
            on_done=lambda out: page.show_quality(out["quality"]),
            area="photometry",
        )
    )
    page.minimum_requested.connect(main.time_minimum)
    page.next_requested.connect(main._photometry_next)
    page.apertures_requested.connect(
        lambda images, target, comps, rule: main.run_step(
            "photometry.apertures",
            {"images": images, "target_xy": target, "comps_xy": comps},
            {"rule": rule},
            on_done=lambda out: page.show_apertures(out["apertures"]),
            area="photometry",
        )
    )
    page.polarimetry_requested.connect(
        lambda images, o, e, params: main.run_step(
            "photometry.polarimetry",
            {"images": images, "o_xy": o, "e_xy": e},
            params,
            on_done=lambda out: page.show_polarimetry(out["polarimetry"]),
            area="photometry",
        )
    )
    page.suggest_requested.connect(
        lambda images, target, params: main.run_step(
            "photometry.suggest_comparisons",
            # the Gaia stars of the field when it was solved on the frame the stars are marked on
            {"images": images, "target_xy": target} | ({"field": page.field} if page.field and page.ref == 0 else {}),
            params,
            on_done=lambda out: page.set_comparisons(out["comps_xy"], out.get("catalogue")),
            area="photometry",
        )
    )
    page.field_requested.connect(
        lambda image: main.run_step(
            "photometry.identify_field",
            {"image": image},
            on_done=lambda out: page.show_field(out["field"]),
            on_fail=page.field_failed,
            area="photometry",
        )
    )
    return page


def make_oc_page(main):
    """O-C in a window of its own (the owner, 2026-11-08); minima timed in Photometry and maxima from the
    frequency analysis arrive here."""
    oc = OCPage(main)
    oc.ephemeris_requested.connect(
        lambda name: main.run_step_for(
            "oc",
            "planning.ephemeris",
            {"name": name},
            {"catalogue": "vsx"},
            on_done=lambda out: oc.set_ephemeris(out["target"]),
            on_fail=lambda msg: oc.result.setText(translate(msg)),
        )
    )

    def oc_background(model, text, t0, period, steps, minima):
        from .messages import translate

        params = {"model": model, "t0": t0, "period": period, "mcmc_steps": steps}
        fail = QCoreApplication.translate("MainWindow", "Cannot fit: {error}")
        main.run_step_for(
            "oc",
            "timeseries.oc_fit",
            {"minima": text},
            params,
            on_done=lambda out: oc.show_fit(out["fit"], minima),
            on_fail=lambda msg: oc.result.setText(fail.format(error=translate(msg))),
        )

    oc.background = oc_background
    return oc


def make_lightcurve_page(main):
    page = LightCurvePage(main)
    page.period_page.search_requested.connect(main.search_period)
    vf = page.varfind_page
    vf.search_requested.connect(
        lambda images, params: main.run_step_for(
            "timeseries", "photometry.varfind", {"images": images}, params, on_done=vf.show_result
        )
    )
    vf.light_curve_chosen.connect(
        lambda t, f, label: (
            page.period_page.set_light_curve(t, f, label),
            page.setCurrentWidget(page.period_page),
        )
    )
    fp = page.frequency_page
    fp.analyse_requested.connect(
        lambda t, y, params: main.run_step_for(
            "timeseries", "timeseries.frequencies", {"time": t, "flux": y}, params, on_done=fp.show_result
        )
    )
    fp.to_oc.clicked.connect(  # to the O-C window, opened so the user sees them arrive
        lambda: (
            [main.oc_page.add_minimum(tm, err, "maximum") for tm, err in (fp.result or {}).get("maxima", [])],
            main.open_area("oc"),
        )
    )
    pp = page.period_page

    def fetch(target, mission):
        from ..settings import config_dir

        def done(out):
            lc = out["light_curve"]
            pp.set_light_curve(lc["time"], lc["rel_flux"], f"{target} ({lc['source']})", err=lc.get("rel_flux_err"))

        if mission in ("ZTF", "AAVSO"):
            inputs = {"target": target, "cache_file": str(config_dir() / "targets.json")}
            return main.run_step_for(
                "timeseries",
                "timeseries.survey_lc",
                inputs,
                {"source": mission},
                on_done=done,
                on_fail=pp.source.setText,
            )
        inputs = {"target": target, "folder": str(main.settings.path.parent / "archive")}
        return main.run_step_for(
            "timeseries",
            "timeseries.mission_lc",
            inputs,
            {"mission": mission},
            on_done=done,
            on_fail=pp.source.setText,
        )

    pp.archive_requested.connect(fetch)
    return page


def make_image_page(main):
    page = ImagePage(main)
    page.header_save_requested.connect(main.save_header_changes)
    page.image_chosen.connect(lambda p: main.open_fits(Path(p)))
    page.viewer.context_requested.connect(lambda x, y, pos: main.image_menu(x, y).exec(pos))
    return page
