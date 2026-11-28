"""What each plot says while it is empty (plans/interface.md UI-6): what will appear there and the one thing to do to
get it, written for a newcomer. One table, so a page names its plot's words by a key: `plot_box(self, "period")`."""

from PySide6.QtCore import QCoreApplication

translate = QCoreApplication.translate


def empty_text(key):
    """The words of plot `key` (KeyError for a key not in the table: a typo shows at once)."""
    return {
        "period": translate("EmptyPlot", "The light curve, its periodogram and the folded curve appear here: load a "
                            "light curve (Load CSV / AAVSO / ZTF / ASAS-SN… or Download)"),
        "frequency": translate("EmptyPlot", "The amplitude spectrum appears here: load a light curve in Period "
                               "search, then press Analyse frequencies"),
        "varfind": translate("EmptyPlot", "The magnitude–scatter diagram of the field appears here: press Choose "
                             "frames…, then Search for variables"),
        "occultation": translate("EmptyPlot", "The light curve and the fitted occultation appear here: press Load "
                                 "light curve…"),
        "oc": translate("EmptyPlot", "The O−C diagram appears here: load the times of minimum (Load file…), then "
                        "press Fit and draw O-C"),
        "exoplanets": translate("EmptyPlot", "The light curve and the fitted transit appear here: press Open light "
                                "curves…, then Fit the transit"),
        "chains": translate("EmptyPlot", "The MCMC chains appear here after a fit with MCMC steps above 0"),
        "corner": translate("EmptyPlot", "The posterior corner plot appears here after a fit with MCMC steps above 0"),
        "oc_periodogram": translate("EmptyPlot", "The periodogram of the O−C residuals appears here after a fit"),
        "midtimes": translate("EmptyPlot", "The O−C of the mid-transit times appears here once the files are fitted"),
        "plan": translate("EmptyPlot", "The altitude chart of the night appears here: add targets, then press Plan "
                          "the night"),
        "weather": translate("EmptyPlot", "Cloud cover, humidity and wind appear here: press Get the forecast"),
        "pixel": translate("EmptyPlot", "The band values of a pixel appear here: open an image and click a pixel"),
        "histogram": translate("EmptyPlot", "The histogram of the shown band appears here once an image is open"),
        "frame_histogram": translate("EmptyPlot", "The histogram of the clicked frame appears here"),
        "reduce": translate("EmptyPlot", "The extracted spectrum and its arc lines appear here: choose the frames, "
                            "then press 3. Extract"),
        "echelle": translate("EmptyPlot", "The orders and their arc lines appear here: press 4. Extract the orders"),
        "telluric": translate("EmptyPlot", "The telluric correction appears here: press Correct and save"),
        "velocity": translate("EmptyPlot", "Line profiles, radial velocities and the orbit appear here: add spectra "
                              "(Add…), then press Measure radial velocities"),
        "cube": translate("EmptyPlot", "The spectrum of a spaxel appears here: press Load cube, then click a spaxel"),
        "spectrum": translate("EmptyPlot", "The spectrum appears here: press Open spectrum…"),
        "models": translate("EmptyPlot", "The light curve and the fitted model appear here: choose the light curve, "
                            "then press Fit"),
        "visual_orbit": translate("EmptyPlot", "The orbit appears here: press Load measures…, then Fit the orbit"),
        "photometry": translate("EmptyPlot", "The light curve appears here: press Measure light curve"),
        "observe": translate("EmptyPlot", "The camera temperature and the focuser position are drawn here while the "
                             "observatory runs"),
        "coefficients": translate("EmptyPlot", "The extinction or transformation fit appears here: press one of the "
                                  "buttons above"),
    }[key]  # fmt: skip
