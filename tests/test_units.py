def test_wavelengths_air_and_vacuum_and_magnitudes_with_errors():
    """ARC-15 item 1: air ↔ vacuum (Morton 2000) both ways; flux ↔ magnitude carries the error."""
    import numpy as np
    import pytest

    from astrowb.core.units import air_to_vac, flux_to_mag, mag_to_flux, vac_to_air

    assert vac_to_air(6564.61) == pytest.approx(6562.80, abs=0.01)  # H alpha, NIST
    w = np.array([3000.0, 5000.0, 6562.8, 9000.0])
    assert np.allclose(vac_to_air(air_to_vac(w)), w, atol=1e-6)
    mag, err = flux_to_mag(np.array([100.0]), np.array([1.0]))
    assert mag[0] == pytest.approx(-5.0) and err[0] == pytest.approx(0.010857, rel=1e-4)
    flux, back = mag_to_flux(mag, err)
    assert flux[0] == pytest.approx(100.0) and back[0] == pytest.approx(1.0)
