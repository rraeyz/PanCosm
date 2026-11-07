"""The nearby-eclipsing-binary check in the Photometry window (plans/photometry.md PHO-23): the Gaia neighbours that
could make the TESS depth measured on every frame (step photometry.neb_check), their dispositions in a table; a row
shows its star on the image."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QInputDialog, QPushButton

from .kit.dialogs import Dialog
from .kit.table_view import DataTable

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryNeb", "…") calls


def add(main, page, layout):
    page.neb_button = QPushButton(translate("PhotometryNeb", "Nearby-eclipsing-binary check…"), page)
    page.neb_button.setToolTip(
        translate(
            "PhotometryNeb",
            "TFOP: every Gaia star within 2.5′ that could make the TESS depth, measured on every frame and cleared "
            "or not (needs the identified field)",
        )
    )
    page.neb_button.clicked.connect(lambda: run(main, page))
    layout.addWidget(page.neb_button)


def _depth(page):
    fit = getattr(page, "transit_fit", None)
    start = fit[1]["derived"].get("depth_ppt", 5.0) if fit else 5.0
    depth, ok = QInputDialog.getDouble(page, translate("PhotometryNeb", "Nearby-eclipsing-binary check"),
                                       translate("PhotometryNeb", "The depth TESS saw on the target (ppt):"),
                                       round(float(start), 2), 0.01, 1000.0, 2)  # fmt: skip
    return depth if ok else None


def run(main, page, depth=None):
    if not (page.images and page.target is not None and page.comps):
        page.transit_result.setText(translate("PhotometryNeb", "Mark the target and the comparison stars first."))
        return
    if not page.field or page.ref not in (None, 0):
        page.transit_result.setText(
            translate("PhotometryNeb", "Identify the field first, with the stars marked on the first frame.")
        )
        return
    depth = depth or _depth(page)
    if not depth:
        return
    inputs = {"images": page._series(), "target_xy": list(page.target), "comps_xy": [list(c) for c in page.comps],
              "field": page.field}  # fmt: skip
    params = {"depth_ppt": depth, "r_ap": page.r_ap.value(), "r_in": page.r_in.value(), "r_out": page.r_out.value()}
    page.transit_result.setText(translate("PhotometryNeb", "Measuring the neighbours on every frame…"))
    from .messages import translate as message

    main.run_step_for("photometry", "photometry.neb_check", inputs, params,
                      on_done=lambda out: show(page, out["neb"], depth),
                      on_fail=lambda msg: page.transit_result.setText(message(msg)))  # fmt: skip


def show(page, rows, depth):
    if not rows:
        page.transit_result.setText(
            translate("PhotometryNeb", "No star near enough and bright enough to make a {d:g} ppt dip.").format(d=depth)
        )
        return None
    words = {"Cleared": translate("PhotometryNeb", "Cleared"),
             "Likely cleared": translate("PhotometryNeb", "Likely cleared"),
             "Cleared - too faint": translate("PhotometryNeb", "Cleared - too faint"),
             "Not cleared": translate("PhotometryNeb", "Not cleared"),
             "Not cleared - flux too low": translate("PhotometryNeb", "Not cleared - flux too low")}  # fmt: skip
    cleared = sum(r["disposition"].startswith("Cleared") or r["disposition"] == "Likely cleared" for r in rows)
    page.transit_result.setText(
        translate("PhotometryNeb", "{c} of {n} neighbours cleared for a {d:g} ppt dip.").format(
            c=cleared, n=len(rows), d=depth
        )
    )
    d = page.neb_dialog = Dialog(translate("PhotometryNeb", "Nearby-eclipsing-binary check"), page, None, "neb")
    view = DataTable(d)
    header = [translate("PhotometryNeb", "Disposition"), "G", translate("PhotometryNeb", "Distance (″)"),
              "Δmag", translate("PhotometryNeb", "Depth needed (ppt)"), translate("PhotometryNeb", "RMS (ppt)"),
              translate("PhotometryNeb", "Depth / RMS"), "x", "y"]  # fmt: skip
    data = [[words.get(r["disposition"], r["disposition"]), round(r["gmag"], 2), round(r["separation"]),
             round(r["dmag"], 2), round(r["required_ppt"], 1), round(r["rms_ppt"], 1), round(r["ratio"], 1),
             round(r["x"], 1), round(r["y"], 1)] for r in rows]  # fmt: skip
    view.set_data(header, data, keys=[(r["x"], r["y"]) for r in rows])
    view.row_chosen.connect(lambda key: key is not None and page.viewer.centerOn(*key))
    d.body.addWidget(view)
    d.add_buttons(translate("PhotometryNeb", "Close")).setDefault(True)
    d.resize(max(d.width(), 820), max(d.height(), 420))
    d.open()
    return d
