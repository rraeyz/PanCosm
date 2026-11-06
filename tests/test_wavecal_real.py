"""Wavelength solutions on the lines of a real arc: ESO EFOSC2, grism 11, He-Ar, 2019-01-01 (PESSTO night)."""

import numpy as np
import pytest

from astrowb.spectroscopy import wavecal

# the 16 lines found in the extracted arc (pixels along the dispersion, 2x2 binned)
PEAKS = [166.992, 204.672, 240.075, 250.496, 320.664, 380.86, 431.838, 454.421, 656.363, 839.674, 904.688, 927.385]
PEAKS += [945.744, 974.798, 999.139, 1014.712]


@pytest.mark.parametrize(
    "guesses",
    [
        [[656, 5875.62], [840, 6678.15], [927, 7065.19], [455, 5015.68], [321, 4471.48]],  # by hand, the middle only
        [[656, 5875.62], [927, 7065.19]],  # two lines
        [[166.99, 3888.7], [320.66, 4471.5], [656.36, 5875.62], [999.14, 7383.9]],  # PESSTO's IRAF database lines
    ],
)
def test_efosc2_arc_is_solved_like_iraf_from_a_few_lines(guesses):
    catalogue = np.union1d(wavecal.load_line_list("henear"), [g[1] for g in guesses])
    sol = wavecal.solve(PEAKS, catalogue, guesses, order=5)
    assert sol.n_lines >= 12 and sol.degree == 4 and sol.rms < 0.3  # PESSTO uses order 5; IRAF-level residuals
    for p, w in guesses:  # an identified line keeps its wavelength
        i = int(np.argmin(np.abs(sol.pixels - p)))
        assert abs(sol.pixels[i] - p) > 2 or sol.waves[i] == pytest.approx(w)
