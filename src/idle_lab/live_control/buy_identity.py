"""Viewport buy identity: catalog entries bound into visible slots 1–6.

Keys 1–6 are viewport slots. Catalog entries are durable upgrade names.
OCR nameplates are soft evidence; the ordered catalog (neighbors, columns)
scores every possible scroll offset and fills the window when one offset wins.
Abstain beats a confident wrong label.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class CatalogEntry:
    """One upgrade in a tab's ordered scroll catalog."""

    id: str
    label: str
    index: int  # 0-based position in the catalog
    aliases: tuple[str, ...] = ()
    column: str | None = None  # "left" | "right" | None
    lines: int | None = None
    unique: tuple[str, ...] = ()
    provisional: bool = False

    @property
    def names(self) -> tuple[str, ...]:
        seen: list[str] = []
        for name in (self.label, *self.aliases):
            text = str(name).strip()
            if text and text not in seen:
                seen.append(text)
        return tuple(seen)


@dataclass(frozen=True)
class BoundBuy:
    """What LCO believes occupies a visible slot right now."""

    slot_index: int  # 1-based viewport key
    entry: CatalogEntry | None
    source: str  # "ocr" | "structure" | "page" | "offset" | "unknown"
    confidence: float = 0.0

    @property
    def known(self) -> bool:
        return self.entry is not None and self.confidence >= 0.35

    @property
    def label(self) -> str:
        return self.entry.label if self.entry is not None else "?"

    @property
    def display_label(self) -> str:
        """Hold-D label with a light confidence marker."""

        if self.entry is None or self.confidence < 0.35:
            return "?"
        if self.confidence >= 0.7:
            return self.label
        if self.confidence >= 0.5:
            return f"{self.label}~"
        return f"{self.label}?"

    @property
    def object_id(self) -> str | None:
        return self.entry.id if self.entry is not None else None


@dataclass(frozen=True)
class ViewportIdentity:
    known: bool
    offset: int  # catalog index of the top-left visible card
    bindings: tuple[BoundBuy, ...]
    reason: str = ""
    confidence: float = 0.0  # window-level 0..1
    offset_scores: tuple[tuple[int, float], ...] = ()  # top competing offsets

    def label_for(self, slot_index: int) -> str:
        for bound in self.bindings:
            if bound.slot_index == slot_index:
                return bound.label
        return "?"

    def display_label_for(self, slot_index: int) -> str:
        for bound in self.bindings:
            if bound.slot_index == slot_index:
                return bound.display_label
        return "?"

    def binding_for(self, slot_index: int) -> BoundBuy | None:
        for bound in self.bindings:
            if bound.slot_index == slot_index:
                return bound
        return None


@dataclass(frozen=True)
class OffsetHypothesis:
    offset: int
    score: float
    slot_scores: tuple[float, ...]  # per slot 1..n aligned to this offset


_WORD_RE = re.compile(r"[A-Za-z0-9%/.]+")

# Soft OCR → entry match thresholds (0..1).
_DIRECT_HIGH = 0.70
_DIRECT_MED = 0.45
_STRUCTURE_CONF = 0.55
_WINDOW_KNOWN = 0.55
_WINDOW_MARGIN = 0.18


def parse_catalog(raw: Any) -> list[CatalogEntry]:
    """Parse a scroll_list.catalog array into ordered entries."""

    if not isinstance(raw, list):
        return []
    out: list[CatalogEntry] = []
    for index, item in enumerate(raw):
        if isinstance(item, str):
            label = item.strip()
            if not label:
                continue
            out.append(
                CatalogEntry(
                    id=f"catalog.{index + 1}",
                    label=label,
                    index=len(out),
                )
            )
            continue
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("stat") or "").strip()
        oid = str(item.get("id") or "").strip()
        if not label and not oid:
            continue
        if not label:
            label = oid
        if not oid:
            oid = f"catalog.{index + 1}"
        aliases_raw = item.get("aliases") or []
        aliases = tuple(str(a).strip() for a in aliases_raw if str(a).strip()) if isinstance(aliases_raw, list) else ()
        unique_raw = item.get("unique") or item.get("unique_tokens") or []
        unique = tuple(str(u).strip() for u in unique_raw if str(u).strip()) if isinstance(unique_raw, list) else ()
        column = item.get("column")
        column_norm = str(column).strip().lower() if column else None
        if column_norm not in {"left", "right"}:
            column_norm = None
        lines = item.get("lines")
        lines_n = int(lines) if lines is not None else None
        out.append(
            CatalogEntry(
                id=oid,
                label=label,
                index=len(out),
                aliases=aliases,
                column=column_norm,
                lines=lines_n,
                unique=unique,
                provisional=bool(item.get("provisional")),
            )
        )
    return out


def catalog_from_page_labels(labels: Iterable[str], *, tab: str) -> list[CatalogEntry]:
    """Fallback catalog from first-page labels when no catalog array exists."""

    out: list[CatalogEntry] = []
    for i, label in enumerate(labels):
        text = str(label).strip()
        if not text:
            continue
        out.append(
            CatalogEntry(
                id=f"buy.{tab}.{i + 1}",
                label=text,
                index=len(out),
                column="left" if len(out) % 2 == 0 else "right",
            )
        )
    return out


def bind_by_offset(
    catalog: list[CatalogEntry],
    *,
    offset: int,
    slot_count: int = 6,
    source: str = "offset",
    confidence: float = 1.0,
) -> ViewportIdentity:
    """Map catalog[offset:] onto viewport slots 1..slot_count."""

    if offset < 0 or not catalog:
        return unknown_identity(slot_count, reason="empty catalog or bad offset")
    bindings: list[BoundBuy] = []
    for slot in range(1, slot_count + 1):
        idx = offset + slot - 1
        if idx >= len(catalog):
            bindings.append(BoundBuy(slot_index=slot, entry=None, source="unknown", confidence=0.0))
            continue
        bindings.append(
            BoundBuy(
                slot_index=slot,
                entry=catalog[idx],
                source=source,
                confidence=confidence if source in {"offset", "page"} else min(0.85, confidence),
            )
        )
    first_row_ok = all(b.known for b in bindings[: min(2, slot_count)])
    reason = f"offset={offset}" if first_row_ok else f"offset={offset} partial"
    return ViewportIdentity(
        known=bool(first_row_ok),
        offset=offset,
        bindings=tuple(bindings),
        reason=reason,
        confidence=confidence if first_row_ok else 0.0,
    )


def unknown_identity(slot_count: int = 6, *, reason: str = "unknown") -> ViewportIdentity:
    bindings = tuple(
        BoundBuy(slot_index=i, entry=None, source="unknown", confidence=0.0)
        for i in range(1, slot_count + 1)
    )
    return ViewportIdentity(known=False, offset=0, bindings=bindings, reason=reason, confidence=0.0)


def next_offset(
    offset: int,
    *,
    direction: str,
    rows: int,
    cols: int,
    catalog_len: int,
) -> int | None:
    """Advance catalog offset after a controlled one-row step. None ⇒ invalidate."""

    delta = max(1, int(rows)) * max(1, int(cols))
    if direction == "down":
        nxt = offset + delta
    elif direction == "up":
        nxt = offset - delta
    else:
        return None
    if nxt < 0:
        return 0 if offset > 0 else None
    if nxt >= catalog_len:
        return None
    return nxt


def slot_column(slot_index: int) -> str:
    """1-based slot → left/right column in the 2-col buy grid."""

    return "left" if (slot_index % 2) == 1 else "right"


def normalize_ocr_text(text: str) -> str:
    return " ".join(_WORD_RE.findall(text or "")).lower()


def score_text_vs_entry(
    observation: str,
    entry: CatalogEntry,
    *,
    column: str | None = None,
) -> float:
    """Soft 0..1 score of one nameplate OCR blob against one catalog entry."""

    hay = normalize_ocr_text(observation)
    if not hay:
        return 0.0

    best = 0.0
    hay_tokens = [t for t in hay.split() if t]
    hay_set = set(hay_tokens)

    for name in entry.names:
        needle = normalize_ocr_text(name)
        if not needle:
            continue
        if needle == hay:
            best = max(best, 1.0)
            continue
        if needle in hay or hay in needle:
            best = max(best, 0.88)
            continue
        n_tokens = [t for t in needle.split() if len(t) > 1]
        if not n_tokens:
            continue
        overlap = 0.0
        for token in n_tokens:
            if token in hay_set:
                overlap += 1.0
                continue
            # Fuzzy prefix: OCR "thom" ≈ "thorn", "lifesteai" ≈ "lifesteal".
            if len(token) >= 3:
                for ht in hay_tokens:
                    if len(ht) < 3:
                        continue
                    if token.startswith(ht[:3]) or ht.startswith(token[:3]):
                        overlap += 0.55
                        break
                    # Shared stem length
                    shared = 0
                    for a, b in zip(token, ht):
                        if a != b:
                            break
                        shared += 1
                    if shared >= 4:
                        overlap += 0.45
                        break
        ratio = overlap / len(n_tokens)
        best = max(best, 0.2 + 0.7 * min(1.0, ratio))

    for token in entry.unique:
        tok = normalize_ocr_text(token)
        if tok and tok in hay:
            best = min(1.0, best + 0.08)

    if column and entry.column and column != entry.column:
        best *= 0.45
    return min(1.0, best)


def match_ocr_to_catalog(
    observation: str,
    catalog: list[CatalogEntry],
    *,
    column: str | None = None,
    candidates: Iterable[CatalogEntry] | None = None,
) -> BoundBuy | None:
    """Best single-slot catalog match. Abstains when the top two scores tie closely."""

    pool = list(candidates) if candidates is not None else list(catalog)
    if not pool or not normalize_ocr_text(observation):
        return None
    scored = [(entry, score_text_vs_entry(observation, entry, column=column)) for entry in pool]
    scored = [(e, s) for e, s in scored if s > 0.2]
    if not scored:
        return None
    scored.sort(key=lambda pair: pair[1], reverse=True)
    if len(scored) > 1 and scored[0][1] - scored[1][1] < 0.08:
        return None
    entry, score = scored[0]
    if score < _DIRECT_MED:
        return None
    return BoundBuy(slot_index=0, entry=entry, source="ocr", confidence=score)


def nameplate_roi(
    nx: float,
    ny: float,
    *,
    card_nw: float = 0.30,
    card_nh: float = 0.08,
) -> dict[str, float]:
    """Title-band ROI well left of the buy/Max click (normalized window coords).

    Clicks park on the value/cost/Max control. Titles sit on the card's left
    edge — keep this ROI off the Max plate or OCR reads junk and tanks scores.
    """

    _ = card_nw  # width hint kept for call-site compat; title band is fixed relative to click
    # Empirically: buy click ≈ 0.32/0.72; title left edge ≈ click - 0.24.
    title_nx = float(nx) - 0.24
    title_ny = float(ny) - float(card_nh) * 0.50
    return {
        "nx": max(0.02, min(0.90, title_nx)),
        "ny": max(0.02, min(0.92, title_ny)),
        "nw": 0.20,
        "nh": max(0.045, float(card_nh) * 0.85),
    }


def best_catalog_score(observation: str, catalog: list[CatalogEntry], *, column: str | None) -> float:
    if not normalize_ocr_text(observation):
        return 0.0
    return max(
        (score_text_vs_entry(observation, entry, column=column) for entry in catalog),
        default=0.0,
    )


def rank_offset_hypotheses(
    catalog: list[CatalogEntry],
    observations: dict[int, str],
    *,
    slot_count: int = 6,
) -> list[OffsetHypothesis]:
    """Score every catalog offset by how well OCR fits that window.

    Uses a raw evidence sum (not an average over every OCR blob) so garbage
    crops on Max plates cannot dilute a single strong Crit Chance anchor.
    Neighbor structure is implicit in the shared offset.
    """

    if not catalog:
        return []
    max_offset = max(0, len(catalog) - 1)
    hypotheses: list[OffsetHypothesis] = []

    for offset in range(0, max_offset + 1):
        slot_scores: list[float] = []
        total = 0.0
        anchors = 0
        for slot in range(1, slot_count + 1):
            idx = offset + slot - 1
            obs = observations.get(slot) or ""
            col = slot_column(slot)
            if idx >= len(catalog):
                # Text where the list has ended — only penalize if it looked like a real name.
                if best_catalog_score(obs, catalog, column=col) >= _DIRECT_MED:
                    slot_scores.append(-0.2)
                    total -= 0.2
                else:
                    slot_scores.append(0.0)
                continue
            entry = catalog[idx]
            score = score_text_vs_entry(obs, entry, column=col)
            # Ignore low-scoring garbage blobs (Max / numbers / overlay crumbs).
            if normalize_ocr_text(obs) and score < 0.25 and best_catalog_score(obs, catalog, column=col) < 0.25:
                score = 0.0
            slot_scores.append(score)
            total += score
            if score >= _DIRECT_HIGH:
                total += 0.55  # unique-ish strong anchor bonus
                anchors += 1
            elif score >= _DIRECT_MED:
                total += 0.20
                anchors += 1

        # Same-row pair bonus: left+right both decent for consecutive catalog ids.
        for left_slot in range(1, slot_count, 2):
            right_slot = left_slot + 1
            if right_slot > slot_count:
                break
            left_i = left_slot - 1
            right_i = right_slot - 1
            if slot_scores[left_i] >= _DIRECT_MED and slot_scores[right_i] >= _DIRECT_MED:
                total += 0.45
            elif slot_scores[left_i] >= 0.35 and slot_scores[right_i] >= 0.35:
                total += 0.20

        # Vertical neighbor bonus.
        for top_slot in range(1, slot_count - 1, 2):
            below = top_slot + 2
            if below > slot_count:
                break
            if slot_scores[top_slot - 1] >= 0.35 and slot_scores[below - 1] >= 0.35:
                total += 0.15

        # Prefer offsets that actually used anchors (avoid empty high ties).
        if anchors:
            total += 0.05 * anchors
        hypotheses.append(OffsetHypothesis(offset=offset, score=total, slot_scores=tuple(slot_scores)))

    hypotheses.sort(key=lambda h: h.score, reverse=True)
    return hypotheses


def _unique_anchor_offset(
    catalog: list[CatalogEntry],
    observations: dict[int, str],
    *,
    slot_count: int,
) -> tuple[int, int, float] | None:
    """If one high-confidence OCR hit uniquely implies an offset, return it.

    Returns (offset, slot_index, confidence) or None.
    """

    candidates: list[tuple[int, int, float]] = []
    for slot in range(1, slot_count + 1):
        hit = match_ocr_to_catalog(
            observations.get(slot) or "",
            catalog,
            column=slot_column(slot),
        )
        if hit is None or hit.entry is None or hit.confidence < _DIRECT_HIGH:
            continue
        implied = hit.entry.index - (slot - 1)
        if implied < 0:
            continue
        candidates.append((implied, slot, hit.confidence))
    if not candidates:
        return None
    # Prefer the highest-confidence unique implied offset.
    by_offset: dict[int, list[tuple[int, float]]] = {}
    for offset, slot, conf in candidates:
        by_offset.setdefault(offset, []).append((slot, conf))
    # If multiple offsets claimed, pick the one with strongest total conf.
    best_offset = max(
        by_offset.items(),
        key=lambda item: sum(conf for _slot, conf in item[1]),
    )[0]
    slot, conf = max(by_offset[best_offset], key=lambda pair: pair[1])
    return best_offset, slot, conf


def bind_from_slot_texts(
    catalog: list[CatalogEntry],
    observations: dict[int, str],
    *,
    slot_count: int = 6,
    min_votes: int = 2,  # kept for call-site compat; soft scoring supersedes hard votes
) -> ViewportIdentity:
    """Bind the visible grid by ranking catalog-offset hypotheses with soft OCR.

    One strong unique anchor (e.g. Crit Chance under key 1) is enough to lock the
    window so neighbors fill from structure when their OCR is weak/garbage.
    """

    _ = min_votes
    if not catalog:
        return unknown_identity(slot_count, reason="empty catalog")

    hypotheses = rank_offset_hypotheses(catalog, observations, slot_count=slot_count)
    if not hypotheses:
        return unknown_identity(slot_count, reason="ocr-no-hypotheses")

    best = hypotheses[0]
    second = hypotheses[1] if len(hypotheses) > 1 else None
    margin = best.score - (second.score if second is not None else 0.0)
    top_scores = tuple((h.offset, round(h.score, 3)) for h in hypotheses[:4])

    strong_slots = sum(1 for s in best.slot_scores if s >= _DIRECT_MED)
    high_slots = sum(1 for s in best.slot_scores if s >= _DIRECT_HIGH)
    unique = _unique_anchor_offset(catalog, observations, slot_count=slot_count)

    # Promote a unique high OCR hit even when the rest of the crops are junk.
    if unique is not None:
        u_offset, u_slot, u_conf = unique
        matching = next((h for h in hypotheses if h.offset == u_offset), None)
        if matching is not None and (high_slots >= 1 or u_conf >= _DIRECT_HIGH):
            # If ranking disagreed, prefer the unique-anchor offset when margin is thin
            # or the ranked winner has no high anchors.
            if matching.offset != best.offset and (high_slots == 0 or margin < 0.35):
                best = matching
                second = hypotheses[0] if hypotheses[0].offset != best.offset else (
                    hypotheses[1] if len(hypotheses) > 1 else None
                )
                margin = best.score - (second.score if second is not None else 0.0)
                strong_slots = sum(1 for s in best.slot_scores if s >= _DIRECT_MED)
                high_slots = sum(1 for s in best.slot_scores if s >= _DIRECT_HIGH)

    window_ok = (
        (best.score >= 0.70 and (margin >= 0.25 or strong_slots >= 2))
        or (high_slots >= 1 and (unique is not None and unique[0] == best.offset))
        or (strong_slots >= 2 and margin >= 0.15)
    )
    soft_ok = strong_slots >= 1 and (margin >= 0.20 or high_slots >= 1) and best.score >= 0.45

    if not window_ok and not soft_ok:
        # Surface only direct high OCR hits; do not invent a whole window.
        bindings: list[BoundBuy] = []
        for slot in range(1, slot_count + 1):
            hit = match_ocr_to_catalog(
                observations.get(slot) or "",
                catalog,
                column=slot_column(slot),
            )
            if hit is not None and hit.entry is not None and hit.confidence >= _DIRECT_HIGH:
                bindings.append(
                    BoundBuy(slot_index=slot, entry=hit.entry, source="ocr", confidence=hit.confidence)
                )
            else:
                bindings.append(BoundBuy(slot_index=slot, entry=None, source="unknown", confidence=0.0))
        return ViewportIdentity(
            known=False,
            offset=best.offset,
            bindings=tuple(bindings),
            reason=f"ocr-weak best={best.offset}@{best.score:.2f} margin={margin:.2f}",
            confidence=min(1.0, best.score / 3.0),
            offset_scores=top_scores,
        )

    # Lock window to best offset; mix direct OCR confidence with structure fill.
    bindings = []
    for slot in range(1, slot_count + 1):
        idx = best.offset + slot - 1
        if idx >= len(catalog):
            bindings.append(BoundBuy(slot_index=slot, entry=None, source="unknown", confidence=0.0))
            continue
        entry = catalog[idx]
        direct = best.slot_scores[slot - 1] if slot - 1 < len(best.slot_scores) else 0.0
        if direct >= _DIRECT_MED:
            bindings.append(
                BoundBuy(
                    slot_index=slot,
                    entry=entry,
                    source="ocr",
                    confidence=min(1.0, direct),
                )
            )
            continue
        # Structure fill from the locked offset / neighboring anchors.
        inferred = 0.58 if high_slots >= 1 else 0.48
        partner = slot + 1 if slot % 2 == 1 else slot - 1
        if 1 <= partner <= slot_count:
            partner_score = best.slot_scores[partner - 1] if partner - 1 < len(best.slot_scores) else 0.0
            if partner_score >= _DIRECT_MED:
                inferred = min(0.78, inferred + 0.14)
        # Vertical neighbor support.
        above = slot - 2
        below = slot + 2
        for neighbor in (above, below):
            if 1 <= neighbor <= slot_count:
                n_score = best.slot_scores[neighbor - 1] if neighbor - 1 < len(best.slot_scores) else 0.0
                if n_score >= _DIRECT_MED:
                    inferred = min(0.80, inferred + 0.08)
        bindings.append(
            BoundBuy(
                slot_index=slot,
                entry=entry,
                source="structure",
                confidence=inferred,
            )
        )

    known = all(b.known for b in bindings[: min(2, slot_count)])
    return ViewportIdentity(
        known=known,
        offset=best.offset,
        bindings=tuple(bindings),
        reason=(
            f"ocr-offset={best.offset} score={best.score:.2f} "
            f"margin={margin:.2f} anchors={strong_slots}"
        ),
        confidence=min(1.0, 0.35 + 0.15 * strong_slots + 0.2 * high_slots),
        offset_scores=top_scores,
    )
