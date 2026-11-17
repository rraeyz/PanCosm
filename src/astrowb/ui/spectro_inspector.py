"""The Spectroscopy window's inspector (plans/interface.md UI-16.3): the arc line selected in the lines table of the
long-slit or échelle job, with what the page already holds about it (its row, the line list, the fit's residual
at that pixel and the fit's summary). Nothing is computed here but a lookup."""

from PySide6.QtCore import QCoreApplication

from .kit.inspector import Inspector

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("SpectroscopyWindow", "…") calls


def _number(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None  # a row whose wavelength is not typed yet


def line_rows(tab, row):
    """[(name, value, unit)] of table row `row` of a reduction tab: the line, then the fit it belongs to."""
    table = tab.guesses
    cells = [table.item(row, c).text() if table.item(row, c) else "" for c in range(table.columnCount())]
    order = cells[:-2][0] if len(cells) > 2 else None  # the échelle's table has the order first
    pixel, wave = _number(cells[-2]), _number(cells[-1])
    rows = [(translate("SpectroscopyWindow", "Order"), order, "")] if order else []
    rows += [
        (translate("SpectroscopyWindow", "Pixel"), pixel, "px"),
        (translate("SpectroscopyWindow", "Wavelength"), wave, "Å"),
        (translate("SpectroscopyWindow", "Arc line list"), tab.line_list.currentText(), ""),
    ]
    solution = (tab.result or {}).get("solution") or {}
    if pixel is not None:  # the reduce tab's fit lines are (pixel, wavelength, residual in Å)
        for line in solution.get("lines") or []:
            if len(line) == 3 and abs(line[0] - pixel) < 0.01 and order is None:
                rows.append((translate("SpectroscopyWindow", "Residual"), round(1000 * line[2], 1), "mÅ"))
                rows.append(
                    (
                        translate("SpectroscopyWindow", "Left out"),
                        translate("SpectroscopyWindow", "yes")
                        if float(line[0]) in tab.excluded_lines
                        else translate("SpectroscopyWindow", "no"),
                        "",
                    )
                )
                break
    if solution:
        rows += [
            (translate("SpectroscopyWindow", "Lines in the fit"), solution.get("n_lines"), ""),
            (translate("SpectroscopyWindow", "Degree"), solution.get("degree"), ""),
            (translate("SpectroscopyWindow", "rms"), solution.get("rms"), "Å"),
        ]
    return rows


def line_inspector(win, page):
    """The inspector beside the stages: hidden until a row of a lines table is chosen, then follows the job."""
    panel = Inspector(translate("SpectroscopyWindow", "Arc line"))
    dock = win.set_inspector(panel)
    dock.hide()
    tabs = (page.reduce_tab, page.echelle_tab)
    tools = page.tools_tab
    panel.owner = None  # the tab whose row the panel shows

    def show(tab, row):
        if row >= 0:
            panel.set_title(translate("SpectroscopyWindow", "Arc line"))
            panel.set_rows(line_rows(tab, row))
            if getattr(panel, "tool_plot_box", None) is not None:
                panel.tool_plot_box.hide()
            panel.owner = tab
            dock.show()

    def show_measure(row):
        if 0 <= row < len(tools.measures):
            from .spectro_tools_inspector import tool_plot, tool_rows

            m, data = tools.measures[row]
            panel.set_title(translate("SpectroscopyWindow", "Measured line"))
            panel.set_rows(tool_rows(tools.lines[row][0], m))
            tool_plot(panel, m, data)
            panel.owner = tools
            dock.show()

    for tab in tabs:
        tab.guesses.currentCellChanged.connect(lambda row, _c, _r, _p, t=tab: show(t, row))
    tools.table.row_chosen.connect(show_measure)

    def follow(i):
        tab = page.tabs.widget(i)
        dock.setVisible(dock.isVisible() and (tab is tools) == (panel.owner is tools) and (tab in tabs or tab is tools))

    page.tabs.currentChanged.connect(follow)
    win.line_inspector = panel
