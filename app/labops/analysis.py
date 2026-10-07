"""Spectrum analysis: find and fit resonance dips.

Input is a 1-D spectrum (frequency in Hz, normalised intensity). This mirrors
optically detected magnetic resonance (ODMR) data from NV centres in diamond,
where fluorescence dips at the spin resonances. With an external magnetic
field the single dip near 2.87 GHz splits into two; the splitting gives the
field strength:

    B = delta_f / (2 * gamma),   gamma = 28.024 GHz/T  (NV electron spin)

The fitting is deliberately simple and robust (Lorentzian dips via
scipy.optimize.curve_fit) because the point of the project is the platform,
but the numbers are physically meaningful.
"""

from __future__ import annotations

import csv
import io
from dataclasses import asdict, dataclass

import numpy as np
from scipy.optimize import curve_fit
from scipy.signal import find_peaks

GAMMA_NV_HZ_PER_T = 28.024e9


class SpectrumError(ValueError):
    """Raised when an uploaded spectrum cannot be parsed or analysed."""


@dataclass
class Dip:
    center_hz: float
    width_hz: float
    contrast: float


@dataclass
class AnalysisResult:
    n_points: int
    dips: list[Dip]
    zero_field_splitting_hz: float | None
    splitting_hz: float | None
    field_tesla: float | None
    fit_rms: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["dips"] = [asdict(x) for x in self.dips]
        return d


def parse_csv(raw: bytes) -> tuple[np.ndarray, np.ndarray]:
    """Parse a two-column CSV (frequency_hz, intensity). Header optional."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SpectrumError("file is not UTF-8 text") from exc

    freqs: list[float] = []
    vals: list[float] = []
    for row in csv.reader(io.StringIO(text)):
        if not row or row[0].strip().startswith("#"):
            continue
        try:
            f, v = float(row[0]), float(row[1])
        except (ValueError, IndexError):
            # Tolerate a single header line; reject garbage elsewhere.
            if not freqs:
                continue
            raise SpectrumError(f"bad row: {row!r}") from None
        freqs.append(f)
        vals.append(v)

    if len(freqs) < 20:
        raise SpectrumError("need at least 20 data points")
    x = np.asarray(freqs, dtype=float)
    y = np.asarray(vals, dtype=float)
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise SpectrumError("non-finite values in spectrum")
    order = np.argsort(x)
    return x[order], y[order]


def _multi_lorentzian(x: np.ndarray, baseline: float, *params: float) -> np.ndarray:
    y = np.full_like(x, baseline, dtype=float)
    for i in range(0, len(params), 3):
        center, width, depth = params[i], params[i + 1], params[i + 2]
        y -= depth * (width / 2) ** 2 / ((x - center) ** 2 + (width / 2) ** 2)
    return y


def analyse(x: np.ndarray, y: np.ndarray, max_dips: int = 2) -> AnalysisResult:
    """Detect up to `max_dips` dips and fit them jointly."""
    baseline = float(np.median(y))
    inverted = baseline - y
    span = float(x[-1] - x[0])
    lower_half = inverted[inverted < np.percentile(inverted, 50)]
    # A perfectly flat spectrum has no points below its median.
    noise = (float(np.std(lower_half)) if lower_half.size > 1 else 0.0) or 1e-6

    peaks, props = find_peaks(inverted, prominence=max(5 * noise, 1e-4))
    if len(peaks) == 0:
        raise SpectrumError("no resonance dips found")
    # Keep the most prominent dips, then order by frequency.
    keep = np.argsort(props["prominences"])[::-1][:max_dips]
    peaks = np.sort(peaks[keep])

    p0: list[float] = [baseline]
    for p in peaks:
        p0 += [float(x[p]), span / 50, float(inverted[p])]

    try:
        popt, _ = curve_fit(_multi_lorentzian, x, y, p0=p0, maxfev=20000)
    except RuntimeError as exc:
        raise SpectrumError(f"fit did not converge: {exc}") from exc

    fitted_baseline = float(popt[0])
    dips = []
    for i in range(1, len(popt), 3):
        center, width, depth = float(popt[i]), abs(float(popt[i + 1])), float(popt[i + 2])
        dips.append(Dip(center_hz=center, width_hz=width, contrast=depth / fitted_baseline))
    dips.sort(key=lambda d: d.center_hz)

    residual = y - _multi_lorentzian(x, *popt)
    rms = float(np.sqrt(np.mean(residual**2)))

    splitting = field = zfs = None
    if len(dips) == 2:
        splitting = dips[1].center_hz - dips[0].center_hz
        zfs = (dips[0].center_hz + dips[1].center_hz) / 2
        field = splitting / (2 * GAMMA_NV_HZ_PER_T)
    elif len(dips) == 1:
        zfs = dips[0].center_hz

    return AnalysisResult(
        n_points=int(len(x)),
        dips=dips,
        zero_field_splitting_hz=zfs,
        splitting_hz=splitting,
        field_tesla=field,
        fit_rms=rms,
    )


def synthetic_spectrum(
    field_tesla: float = 2e-3,
    zfs_hz: float = 2.870e9,
    width_hz: float = 8e6,
    contrast: float = 0.03,
    noise: float = 0.002,
    n: int = 401,
    seed: int | None = 0,
) -> bytes:
    """Generate a realistic two-dip ODMR spectrum as CSV bytes."""
    rng = np.random.default_rng(seed)
    half = field_tesla * GAMMA_NV_HZ_PER_T
    x = np.linspace(zfs_hz - 150e6, zfs_hz + 150e6, n)
    y = _multi_lorentzian(x, 1.0, zfs_hz - half, width_hz, contrast, zfs_hz + half, width_hz, contrast)
    y += rng.normal(0, noise, size=n)
    buf = io.StringIO()
    buf.write("frequency_hz,intensity\n")
    for f, v in zip(x, y, strict=True):
        buf.write(f"{f:.1f},{v:.6f}\n")
    return buf.getvalue().encode()
