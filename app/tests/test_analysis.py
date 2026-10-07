import numpy as np
import pytest

from labops.analysis import GAMMA_NV_HZ_PER_T, SpectrumError, analyse, parse_csv, synthetic_spectrum


@pytest.mark.parametrize("field_mt", [1.0, 2.0, 3.5])
def test_recovers_magnetic_field(field_mt):
    x, y = parse_csv(synthetic_spectrum(field_tesla=field_mt / 1e3, seed=42))
    r = analyse(x, y)
    assert len(r.dips) == 2
    assert r.field_tesla == pytest.approx(field_mt / 1e3, rel=0.03)
    assert r.zero_field_splitting_hz == pytest.approx(2.870e9, rel=1e-3)
    assert all(0.01 < d.contrast < 0.06 for d in r.dips)


def test_splitting_matches_formula():
    x, y = parse_csv(synthetic_spectrum(field_tesla=2e-3, seed=1))
    r = analyse(x, y)
    assert r.splitting_hz == pytest.approx(2 * GAMMA_NV_HZ_PER_T * 2e-3, rel=0.03)


def test_single_dip_at_zero_field():
    x = np.linspace(2.8e9, 2.94e9, 300)
    y = 1 - 0.03 * (4e6) ** 2 / ((x - 2.87e9) ** 2 + (4e6) ** 2)
    r = analyse(x, y, max_dips=1)
    assert len(r.dips) == 1
    assert r.field_tesla is None
    assert r.dips[0].center_hz == pytest.approx(2.87e9, rel=1e-4)


def test_flat_spectrum_has_no_dips():
    x = np.linspace(2.8e9, 2.94e9, 100)
    with pytest.raises(SpectrumError):
        analyse(x, np.ones_like(x))


@pytest.mark.parametrize(
    "raw",
    [b"", b"a,b\n1,2\n", "\xff\xfe".encode("latin-1"), b"f,i\n" + b"1,2\n" * 30 + b"oops,x\n"],
)
def test_rejects_bad_files(raw):
    with pytest.raises(SpectrumError):
        parse_csv(raw)


def test_parse_sorts_and_skips_comments():
    rows = "\n".join(f"{f},{1.0}" for f in range(30, 0, -1))
    x, _ = parse_csv(("# comment\nfrequency_hz,intensity\n" + rows).encode())
    assert list(x) == sorted(x)
