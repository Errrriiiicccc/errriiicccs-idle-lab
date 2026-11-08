"""Detect upgrade buy-slot centers from a full-window screenshot (pure PIL).

Uses horizontal edge energy in the upgrade-list band to find card rows, then
places left/right click circles on those rows. Also estimates whether the list
looks *snapped* (full first row under the header) vs mid-scroll (clipped).
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageOps


@dataclass(frozen=True)
class DetectedBuySlot:
    index: int  # 1-based, reading order L→R, T→B
    nx: float
    ny: float


@dataclass(frozen=True)
class BuyGridDetection:
    snapped: bool
    slots: list[DetectedBuySlot]
    reason: str
    row_nys: tuple[float, ...]
    header_ny: float | None


# Upgrade list body (below combat / above tab bar) on the 593×1028 lab window.
_LIST = {"nx": 0.04, "ny": 0.58, "nw": 0.92, "nh": 0.355}
# Click columns inside each card (buy/cost side sits toward card center-right).
_COL_NX = (0.32, 0.72)
# Expected pitch between card rows (matches shared.buy_grid.row_dy).
_MIN_ROW_GAP = 0.070
_EXPECTED_ROW_H = 0.088


def _row_edge_energy(gray_edges: Image.Image) -> list[float]:
    w, h = gray_edges.size
    px = gray_edges.load()
    out: list[float] = []
    for y in range(h):
        total = 0
        for x in range(0, w, 2):
            total += int(px[x, y])
        out.append(total / max(1, w // 2))
    return out


def _smooth(values: list[float], radius: int = 2) -> list[float]:
    out: list[float] = []
    for i in range(len(values)):
        window = values[max(0, i - radius) : i + radius + 1]
        out.append(sum(window) / len(window))
    return out


def _peaks(values: list[float], *, min_gap: int, thr_frac: float) -> list[int]:
    if not values:
        return []
    thr = max(values) * thr_frac
    raw: list[tuple[int, float]] = []
    for i in range(2, len(values) - 2):
        if values[i] >= thr and values[i] >= values[i - 1] and values[i] >= values[i + 1]:
            raw.append((i, values[i]))
    merged: list[tuple[int, float]] = []
    for i, score in raw:
        if not merged or i - merged[-1][0] > min_gap:
            merged.append((i, score))
        elif score > merged[-1][1]:
            merged[-1] = (i, score)
    return [i for i, _ in merged]


def _dedupe_spaced(values: list[float], *, min_gap: float) -> list[float]:
    """Keep values in order, dropping ones that sit too close to the previous keep."""

    kept: list[float] = []
    for value in values:
        if kept and (value - kept[-1]) < min_gap:
            continue
        kept.append(value)
    return kept


def detect_buy_grid(
    image: Image.Image,
    *,
    cols: int = 2,
    rows: int = 3,
    col_nx: tuple[float, ...] | None = None,
) -> BuyGridDetection:
    """Return up to cols*rows buy centers from edge geometry."""

    rgb = image.convert("RGB")
    w, h = rgb.size
    if w < 80 or h < 120:
        return BuyGridDetection(False, [], "image too small", (), None)

    lx = int(_LIST["nx"] * w)
    ly = int(_LIST["ny"] * h)
    lw = max(8, int(_LIST["nw"] * w))
    lh = max(8, int(_LIST["nh"] * h))
    band = rgb.crop((lx, ly, min(w, lx + lw), min(h, ly + lh)))
    edges = ImageOps.grayscale(band).filter(ImageFilter.FIND_EDGES)
    energy = _smooth(_row_edge_energy(edges), radius=2)
    # Wider peak merge so mid-card text edges do not become fake rows.
    min_gap = max(8, int(_MIN_ROW_GAP * h * 0.85))
    peak_idxs = _peaks(energy, min_gap=min_gap, thr_frac=0.48)
    if len(peak_idxs) < 2:
        return BuyGridDetection(False, [], "not enough horizontal edges", (), None)

    # Absolute ny of each edge peak.
    edge_nys = tuple((ly + i) / h for i in peak_idxs)
    header_ny = edge_nys[0]

    # Card tops = edges after the header, spaced like real cards (not mid-card lines).
    card_tops: list[float] = []
    for ny in edge_nys[1:]:
        if ny < header_ny + 0.015:
            continue
        if card_tops and (ny - card_tops[-1]) < _MIN_ROW_GAP:
            continue
        card_tops.append(ny)
    if not card_tops:
        card_tops = _dedupe_spaced(list(edge_nys[1:]), min_gap=_MIN_ROW_GAP)

    # Build row centers from consecutive tops; last row extends to list bottom.
    list_bottom = _LIST["ny"] + _LIST["nh"]
    row_centers: list[float] = []
    for i, top in enumerate(card_tops):
        bottom = card_tops[i + 1] if i + 1 < len(card_tops) else list_bottom
        height = bottom - top
        if height < 0.045:
            # Too short for a card band — noise / separator.
            continue
        if height < 0.060:
            # Partial last row still clickable near its visible mid.
            center = min(0.92, top + max(0.035, height * 0.55))
        elif height > 0.16:
            # Over-tall band: park one row near expected card mid, not stretch.
            center = top + (_EXPECTED_ROW_H * 0.55)
        else:
            center = top + height * 0.50
        if row_centers and (center - row_centers[-1]) < _MIN_ROW_GAP:
            continue
        row_centers.append(center)
        if len(row_centers) >= rows:
            break

    # Snap: first full card top should sit a healthy gap under the header.
    # Defense/Utility banners are taller than Attack → allow a wider gap.
    first_top = card_tops[0] if card_tops else None
    snapped = False
    reason = "mid-scroll or unknown"
    if first_top is not None:
        gap = first_top - header_ny
        if 0.030 <= gap <= 0.155 and len(row_centers) >= 2:
            snapped = True
            reason = f"snapped gap={gap:.3f} rows={len(row_centers)}"
        elif gap < 0.028:
            snapped = False
            reason = f"clipped first row gap={gap:.3f}"
        else:
            reason = f"odd gap={gap:.3f} rows={len(row_centers)}"

    columns = col_nx or _COL_NX
    if cols == 2 and len(columns) >= 2:
        use_cols = (float(columns[0]), float(columns[1]))
    else:
        use_cols = tuple(float(columns[i % len(columns)]) for i in range(cols))

    slots: list[DetectedBuySlot] = []
    index = 1
    for ny in row_centers[:rows]:
        for nx in use_cols[:cols]:
            slots.append(DetectedBuySlot(index=index, nx=nx, ny=float(ny)))
            index += 1

    if not slots:
        return BuyGridDetection(False, [], "no card rows parsed", edge_nys, header_ny)
    return BuyGridDetection(snapped, slots, reason, tuple(row_centers), header_ny)
