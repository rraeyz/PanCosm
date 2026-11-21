"""UI-16.1: the results dock keeps results. The buttons that carry the light curve on (Period search, Fit an eclipse
or transit model: the second saves the CSV for the Models window) leave it for the Report stage, beside the exports."""


def attach(win, page):
    win.stage_panels["report"].add(page.next_box)  # the page still shows and hides it when a light curve exists
