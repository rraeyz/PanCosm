"""The Calibration window's Check, Masters and Review stages and its Plan tab (plans/interface.md UI-16.2): the frames
in groups with the ones that stand apart marked (calibration/groups.py), the masters to be made and chosen by hand, the
plan (which bias, dark and flat each filter's lights get, each a choice), and after the run the masters' quality."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .kit.table_view import DataTable
from .kit.tokens import role
from .messages import translate as message

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("CalibrationWindow", "…") calls
KINDS = ("bias", "dark", "flat")


def _box(*widgets):
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    for w in widgets:
        lay.addWidget(w, 1 if isinstance(w, (QTreeWidget, DataTable)) else 0)
    return box


def _label(text=""):
    lab = QLabel(text)
    lab.setWordWrap(True)
    return lab


def _amber():
    return QBrush(QColor(role("non_linear")))


def make(page):
    """The three stage boxes (check, masters, review) and the Plan tab's widget; they refresh when the page shows
    new frames or a result."""
    page.left_out = []  # [(path, reason)]: frames the Check stage removed from the list
    page.marks = {}  # path -> why it stands apart
    check = page.check_status = _label()
    page.check_button = QPushButton(translate("CalibrationWindow", "Check the frames"))
    page.check_button.setToolTip(
        translate(
            "CalibrationWindow",
            "Reads the middle of every frame and marks the ones that stand apart from their group: another level or "
            "noise, a flat outside 20–80 % of saturation. Nothing is changed until you leave them out.",
        )
    )
    page.leave_button = QPushButton(translate("CalibrationWindow", "Leave out the marked frames"))
    page.leave_button.setToolTip(
        translate("CalibrationWindow", "Removes the marked frames from the list (Ctrl+Z brings them back)")
    )
    page.leave_button.setEnabled(False)
    page.groups_tree = QTreeWidget()
    page.groups_tree.setHeaderLabel(translate("CalibrationWindow", "Groups of frames"))
    page.frame_stats = _label()
    from .calibration_preview import BeforeAfter, FramePreview

    page.frame_preview = FramePreview()
    page.check_button.clicked.connect(lambda: check_frames(page))
    page.leave_button.clicked.connect(lambda: leave_out(page))
    page.groups_tree.currentItemChanged.connect(lambda item, _: show_stats(page, item))
    boxes = {
        "check": _box(
            check, page.check_button, page.groups_tree, page.frame_stats, page.frame_preview, page.leave_button
        )
    }
    page.masters_text = _label()
    boxes["masters"] = _box(page.masters_text)
    page.review_status = _label(translate("CalibrationWindow", "Calibrate to see how good the masters are."))
    page.review_table = DataTable()
    page.before_after = BeforeAfter()
    page.review_table.set_data(
        [
            translate("CalibrationWindow", "Master"),
            translate("CalibrationWindow", "Check"),
            translate("CalibrationWindow", "Value"),
        ],
        [],
    )
    page.left_out_text = _label()
    boxes["review"] = _box(page.review_status, page.review_table, page.before_after, page.left_out_text)
    page.plan_table = DataTable()
    for w in (page.plan_table.filter, page.plan_table.table):  # behind the front result tab too
        w.setFocusPolicy(Qt.NoFocus)
    page.problems_view = QPlainTextEdit()  # the Problems tab: the frames list's note box, mirrored
    page.problems_view.setReadOnly(True)
    # a tab behind the Plan has a stale geometry the Tab-order check reads as "goes back up"; the same text is in the
    # frames list's note box, which keeps the focus
    page.problems_view.setFocusPolicy(Qt.NoFocus)
    page.warnings.textChanged.connect(lambda: page.problems_view.setPlainText(page.warnings.toPlainText()))
    page.problems_view.setPlainText(page.warnings.toPlainText())
    from . import calibration_report

    calibration_report.make(page)
    boxes["review"].layout().insertWidget(0, page.save_report_button)
    page.changed.connect(lambda: refresh_frames(page))
    page.result_shown.connect(lambda out: refresh_review(page, out))
    return boxes


def _kind_names():
    return {
        "bias": translate("CalibrationWindow", "bias"),
        "dark": translate("CalibrationWindow", "dark"),
        "flat": translate("CalibrationWindow", "flat"),
    }


def refresh_frames(page):
    """The groups tree, the masters to be made and the Plan tab, from the frames the page now holds."""
    from ..calibration.groups import group

    page.marks = {}
    tree = page.groups_tree
    tree.clear()
    page.leave_button.setEnabled(False)
    kinds = page._kind_names()
    for g in group(page.frames):
        bits = [kinds.get(g["kind"], g["kind"]), g["filter"]]
        bits += [f"{g['exptime']:g} s"] if g["exptime"] is not None else []
        bits += [f"{g['binning'][0]}×{g['binning'][1]}"]
        bits += [f"{g['temperature']:.0f} °C"] if g["temperature"] is not None else []
        top = QTreeWidgetItem(tree, [" · ".join(b for b in bits if b) + f"  ({g['count']})"])
        for p in g["paths"]:
            child = QTreeWidgetItem(top, [Path(p).name])
            child.setData(0, Qt.UserRole, p)
    page.check_status.setText(
        translate("CalibrationWindow", "{n} groups of frames.").format(n=tree.topLevelItemCount())
        if page.frames
        else ""
    )
    page.frame_stats.setText("")
    refresh_masters(page)
    refresh_plan(page)


def refresh_masters(page):
    from ..calibration.frames import Frame
    from ..calibration.matching import make_plan

    plan = make_plan([Frame(**f | {"binning": tuple(f["binning"]), "shape": tuple(f["shape"])}) for f in page.frames])
    names = _kind_names()
    by_kind = {}
    for key, paths in plan.groups.items():
        by_kind.setdefault(key[0], []).append(len(paths))
    make = translate("CalibrationWindow", "Master {kind}: {n} to make from {m} frames")
    lines = [make.format(kind=names[k], n=len(by_kind[k]), m=sum(by_kind[k])) for k in KINDS if k in by_kind]
    page.masters_text.setText(
        "\n".join(lines) or translate("CalibrationWindow", "Scan the frames to see the masters to make.")
    )


def check_frames(page):
    """CAL-1: mark the frames that stand apart from their group; a frame that cannot be read is said, not skipped."""
    from ..calibration.groups import group, outliers

    marks, bad = {}, []
    for g in group(page.frames):
        try:
            marks |= outliers(g)
        except (OSError, ValueError) as e:
            bad.append(message(e))
    page.marks = marks
    amber = _amber()
    tree = page.groups_tree
    for i in range(tree.topLevelItemCount()):
        top = tree.topLevelItem(i)
        for j in range(top.childCount()):
            child = top.child(j)
            why = marks.get(child.data(0, Qt.UserRole))
            if why:
                child.setBackground(0, amber)
                child.setToolTip(0, why)
                top.setBackground(0, amber)
                top.setExpanded(True)
    page.leave_button.setEnabled(bool(marks))
    page.check_status.setText(
        "\n".join(
            [translate("CalibrationWindow", "{n} frames stand apart from their group.").format(n=len(marks)), *bad]
        )
    )


def show_stats(page, item):
    from ..calibration.groups import stats

    path = None if item is None else item.data(0, Qt.UserRole)
    if not path:
        page.frame_stats.setText("")
        page.frame_preview.clear()
        return
    try:
        page.frame_preview.show_path(path)
        s = stats(path)
    except (OSError, ValueError) as e:
        page.frame_stats.setText(message(e))
        return
    text = translate(
        "CalibrationWindow", "median {median:.1f}, noise {noise:.2f}, min {min:.0f}, max {max:.0f}, saturated {sat:.1%}"
    )
    page.frame_stats.setText(
        text.format(sat=s["saturated"], **s) + ("\n" + page.marks[path] if path in page.marks else "")
    )


def leave_out(page):
    marks = dict(page.marks)
    frames = [f for f in page.frames if f["path"] not in marks]
    page.left_out += [(p, why) for p, why in marks.items()]
    page.edit(translate("CalibrationWindow", "leave out the marked frames"), page.show_frames, frames, page._problems,
              page._raw_converted)  # fmt: skip
    page.left_out_text.setText(
        "\n".join(
            [translate("CalibrationWindow", "Left out:")] + [f"{Path(p).name}: {why}" for p, why in page.left_out]
        )
    )


def refresh_plan(page):
    """The Plan tab: one row per filter and exposure of the lights with the bias, dark and flat each gets (automatic
    shows the match), each a choice kept in page.master_choices; what is missing in amber, with what is done instead."""
    from ..calibration.frames import Frame
    from ..calibration.matching import make_plan
    from .master_choice import groups as master_groups

    frames = [Frame(**f | {"binning": tuple(f["binning"]), "shape": tuple(f["shape"])}) for f in page.frames]
    plan = make_plan(frames)
    key_of = {p: key for key, paths in plan.groups.items() for p in paths}
    options = master_groups(page.frames)
    desc = {key_of[p]: text for rows in options.values() for p, text in rows if p in key_of}
    names = _kind_names()
    by_path = {f.path: f for f in frames}
    seen = {}
    for entry in plan.lights:
        light = by_path[entry["light"]]
        if light.kind == "light":
            seen.setdefault((light.filter or "", light.exptime), []).append(entry)
    header = [
        translate("CalibrationWindow", "Filter"),
        translate("CalibrationWindow", "Exposure (s)"),
        translate("CalibrationWindow", "Lights"),
    ]
    header += [names[k].capitalize() for k in KINDS] + [translate("CalibrationWindow", "Missing")]
    table = page.plan_table
    table.prepare(header, len(seen))
    missing = {}
    for path, kind, why in plan.missing:
        missing.setdefault(path, []).append(page._missing_text(kind, why))
    for r, ((filt, exp), entries) in enumerate(sorted(seen.items(), key=lambda e: (e[0][0], e[0][1] or 0))):
        for c, v in enumerate((filt or "—", "" if exp is None else f"{exp:g}", len(entries))):
            table.table.setItem(r, c, QTableWidgetItem(str(v)))
        for c, kind in enumerate(KINDS, 3):
            first = entries[0][kind]
            box = QComboBox()
            auto = translate("CalibrationWindow", "automatic")
            box.addItem(f"{auto}: {desc.get(first, translate('CalibrationWindow', 'none'))}", "auto")
            for path, text in options.get(kind, []):
                box.addItem(text, path)
            box.addItem(translate("CalibrationWindow", "none"), "none")
            chosen = (page.master_choices.get(filt) or {}).get(kind, "auto")
            box.setCurrentIndex(max(0, box.findData(chosen)))
            box.activated.connect(lambda _, b=box, f=filt, k=kind: _choose(page, f, k, b.currentData()))
            table.table.setCellWidget(r, c, box)
        lines = sorted({t for e in entries for t in missing.get(e["light"], [])})
        item = QTableWidgetItem("; ".join(lines))
        if lines:
            item.setBackground(_amber())
        table.table.setItem(r, 6, item)


def _choose(page, filt, kind, value):
    choices = {k: dict(v) for k, v in page.master_choices.items()}
    if value == "auto":
        choices.get(filt, {}).pop(kind, None)
    else:
        choices.setdefault(filt, {})[kind] = value
    page.master_choices = {k: v for k, v in choices.items() if v}


def refresh_review(page, out):
    """CAL-6: the masters' checks as a table, amber where a check is not met, beside what was left out."""
    names = {
        "excess_noise": translate("CalibrationWindow", "noise beyond averaging (ADU)"),
        "banding": translate("CalibrationWindow", "row or column banding (ADU)"),
        "hot_pixels": translate("CalibrationWindow", "hot pixels"),
        "flat_levels": translate("CalibrationWindow", "input flat level (share of full well)"),
        "dust": translate("CalibrationWindow", "dust shadow depth"),
    }
    rows, bad = [], []
    for master, checks in (out.get("quality") or {}).items():
        for key, c in checks.items():
            if key in names:
                rows.append([master, names[key], round(float(c["value"]), 4)])
                bad.append(not c["ok"])
    page.review_table.set_data(
        [
            translate("CalibrationWindow", "Master"),
            translate("CalibrationWindow", "Check"),
            translate("CalibrationWindow", "Value"),
        ],
        rows,
    )
    for r, flag in enumerate(bad):
        if flag:
            page.review_table.mark(
                r, 2, role("non_linear"), translate("CalibrationWindow", "not as good as it should be")
            )
    from .calibration_preview import pair_of

    page.before_after.set_pair(pair_of(page.frames, out.get("calibrated") or []))
    page.review_status.setText(
        translate("CalibrationWindow", "{n} checks, {m} in amber.").format(n=len(rows), m=sum(bad)) if rows else
        translate("CalibrationWindow", "No quality checks were made."))  # fmt: skip
