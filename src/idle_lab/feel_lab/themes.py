"""Feel Lab looks — families own distinct color rooms; variants nudge accent + chrome."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Look:
    id: str
    key: str
    title: str
    blurb: str
    bg: str
    panel: str
    board: str
    line: str
    muted: str
    live_bg: str
    live_hover: str
    live_text: str
    live_key: str
    live_border: str
    return_bg: str
    return_text: str
    return_border: str
    return_label: str
    dorm_bg: str
    dorm_text: str
    new: str
    caption: str
    esc_pop: str  # Esc word / return header — should read loud
    desc_border: str  # description box rim (no fill slab)
    style: str
    border_width: int
    rail_width: int
    btn_height: int
    btn_width: int
    pad_x: int
    font_size: int
    bold_live: bool
    bold_key_only: bool
    key_format: str
    uppercase: bool
    group_pad: int
    tight_gap: bool
    show_group_border: bool
    header_size: int


def _look(
    *,
    id: str,
    key: str,
    title: str,
    blurb: str,
    style: str,
    # Room (page / chrome) — must differ by family or themes feel dead
    bg: str,
    panel: str,
    board: str,
    line: str,
    muted: str,
    live_bg: str,
    live_hover: str,
    live_text: str,
    live_key: str,
    live_border: str,
    return_bg: str,
    return_text: str,
    return_border: str,
    dorm_bg: str,
    dorm_text: str,
    caption: str,
    esc_pop: str,
    desc_border: str,
    new: str = "#6A5A40",
    border_width: int = 0,
    rail_width: int = 2,
    btn_height: int = 34,
    btn_width: int = 180,
    pad_x: int = 10,
    font_size: int = 12,
    bold_live: bool = True,
    bold_key_only: bool = False,
    key_format: str = "bracket",
    uppercase: bool = False,
    group_pad: int = 10,
    tight_gap: bool = True,
    show_group_border: bool = False,
    header_size: int = 11,
) -> Look:
    return Look(
        id=id,
        key=key,
        title=title,
        blurb=blurb,
        bg=bg,
        panel=panel,
        board=board,
        line=line,
        muted=muted,
        live_bg=live_bg,
        live_hover=live_hover,
        live_text=live_text,
        live_key=live_key,
        live_border=live_border,
        return_bg=return_bg,
        return_text=return_text,
        return_border=return_border,
        return_label="Esc",
        dorm_bg=dorm_bg,
        dorm_text=dorm_text,
        new=new,
        caption=caption,
        esc_pop=esc_pop,
        desc_border=desc_border,
        style=style,
        border_width=border_width,
        rail_width=rail_width,
        btn_height=btn_height,
        btn_width=btn_width,
        pad_x=pad_x,
        font_size=font_size,
        bold_live=bold_live,
        bold_key_only=bold_key_only,
        key_format=key_format,
        uppercase=uppercase,
        group_pad=group_pad,
        tight_gap=tight_gap,
        show_group_border=show_group_border,
        header_size=header_size,
    )


# --- Family rooms (readably different) ---------------------------------------

# Thread — sage / green rail (main)
_THREAD = dict(
    bg="#B9C4BB",
    panel="#C9D2CB",
    board="#A8B4AC",
    line="#1E2A22",
    muted="#5A6A60",
    live_bg="#E4EBE4",
    live_hover="#EEF3EE",
    live_text="#1A2420",
    live_key="#2F5A42",
    live_border="#4A7A5C",
    return_bg="#B4BEB6",
    return_text="#6A5A48",
    return_border="#8A7A60",
    dorm_bg="#AEB8B0",
    dorm_text="#7A8A80",
    caption="#3A4A40",
    esc_pop="#1A3328",
    desc_border="#6A7E70",
    new="#6A5A40",
)

# Rim — cool slate / blue-gray
_RIM = dict(
    bg="#B4BCC8",
    panel="#C4CCD6",
    board="#A0AAB8",
    line="#1A222E",
    muted="#5A6678",
    live_bg="#E2E7EE",
    live_hover="#EEF2F7",
    live_text="#161E28",
    live_key="#3A4A5A",
    live_border="#5A6A7A",
    return_bg="#A8B0BC",
    return_text="#5A4A40",
    return_border="#7A6A58",
    dorm_bg="#A6AEBA",
    dorm_text="#6A7688",
    caption="#2E3A48",
    esc_pop="#1A2838",
    desc_border="#5A6A7C",
    new="#5A4A38",
)

# Lift — warm stone / parchment
_LIFT = dict(
    bg="#C8BEB0",
    panel="#D6CCC0",
    board="#B8AE9E",
    line="#2A2218",
    muted="#6A5E50",
    live_bg="#EDE6DC",
    live_hover="#F5F0E8",
    live_text="#221A12",
    live_key="#4A3A28",
    live_border="#C8B8A0",
    return_bg="#B8AE9E",
    return_text="#5A5048",
    return_border="#9A8A78",
    dorm_bg="#B0A698",
    dorm_text="#7A6E60",
    caption="#3A3228",
    esc_pop="#2A2010",
    desc_border="#8A7A68",
    new="#6A4A28",
)

# Type — near-ink (typography-forward). Live plates must pop off page bg.
_TYPE = dict(
    bg="#1A1C20",
    panel="#24262C",
    board="#121418",
    line="#E8ECF0",
    muted="#8A929C",
    live_bg="#32383F",
    live_hover="#3E4650",
    live_text="#F0F4F8",
    live_key="#D0D8E0",
    live_border="#8A9AAA",
    return_bg="#1E2228",
    return_text="#8A8070",
    return_border="#4A4840",
    dorm_bg="#16181C",
    dorm_text="#5A6068",
    caption="#A8B0B8",
    esc_pop="#E8D0A0",
    desc_border="#4A5058",
    new="#C8A860",
)


@dataclass(frozen=True)
class Family:
    id: str
    key: str
    title: str
    blurb: str
    style: str
    looks: tuple[Look, ...]


FAMILIES: tuple[Family, ...] = (
    Family(
        id="thread",
        key="1",
        title="Thread",
        blurb="Main line — sage room, slim green rail. Nested looks nudge size and key chrome.",
        style="rail",
        looks=(
            _look(
                id="thread_fine",
                key="1",
                title="Fine",
                blurb="2px green thread, compact rows on sage.",
                style="rail",
                **_THREAD,
                rail_width=2,
                btn_height=30,
                btn_width=160,
                pad_x=8,
                font_size=11,
                tight_gap=True,
                group_pad=8,
            ),
            _look(
                id="thread_dot",
                key="2",
                title="Dot keys",
                blurb="Same sage thread; keys read as D · Label.",
                style="rail",
                **_THREAD,
                rail_width=2,
                key_format="dot",
                btn_height=30,
                btn_width=160,
                font_size=11,
            ),
            _look(
                id="thread_wide",
                key="3",
                title="Wide leaf",
                blurb="Same 2px rail; longer buttons for Deck-dense rows.",
                style="rail",
                **_THREAD,
                rail_width=2,
                btn_height=32,
                btn_width=210,
                pad_x=12,
                font_size=12,
                tight_gap=True,
            ),
            _look(
                id="thread_tall",
                key="4",
                title="Quiet tall",
                blurb="Taller light plates, semibold live type, thin green rail.",
                style="rail",
                **{
                    **_THREAD,
                    "live_bg": "#E8EFE8",
                    "live_hover": "#F2F7F2",
                    "return_bg": "#B0BAB2",
                    "esc_pop": "#143028",
                    "desc_border": "#5A7264",
                },
                rail_width=2,
                btn_height=38,
                btn_width=188,
                font_size=13,
                header_size=12,
                tight_gap=False,
                group_pad=12,
            ),
            _look(
                id="thread_moss",
                key="5",
                title="Moss thread",
                blurb="Deeper moss room + 3px rail — greener than Fine.",
                style="rail",
                **{
                    **_THREAD,
                    "bg": "#A8BAA8",
                    "panel": "#B8C8B8",
                    "board": "#98AA98",
                    "live_key": "#24543A",
                    "live_border": "#3A6A50",
                    "live_bg": "#D8E8D8",
                    "live_hover": "#E4F0E4",
                    "esc_pop": "#0E2818",
                    "desc_border": "#4A6A50",
                },
                rail_width=3,
                btn_height=32,
                btn_width=170,
                font_size=12,
            ),
            _look(
                id="thread_bare",
                key="6",
                title="Bare key",
                blurb="Thread + bare D Label (no brackets).",
                style="rail",
                **_THREAD,
                rail_width=2,
                key_format="bare",
                btn_height=32,
                btn_width=170,
                font_size=12,
            ),
        ),
    ),
    Family(
        id="rim",
        key="2",
        title="Rim",
        blurb="Cool slate room — hairline edges. Should read blue-gray vs Thread sage.",
        style="rim",
        looks=(
            _look(
                id="rim_hairline",
                key="1",
                title="Hairline",
                blurb="1px cool edge on slate — quiet cousin of Thread.",
                style="rim",
                **_RIM,
                border_width=1,
                show_group_border=True,
                rail_width=0,
                btn_height=26,
                btn_width=150,
            ),
            _look(
                id="rim_open",
                key="2",
                title="Open",
                blurb="Button rims only; group band has no frame. Slightly cooler slate.",
                style="rim",
                **{
                    **_RIM,
                    "bg": "#A8B4C4",
                    "panel": "#B8C4D2",
                    "board": "#98A4B4",
                },
                border_width=1,
                show_group_border=False,
                btn_height=26,
                btn_width=150,
            ),
            _look(
                id="rim_dot",
                key="3",
                title="Dot rim",
                blurb="Hairline + D · keys. Steel-er accents.",
                style="rim",
                **{
                    **_RIM,
                    "live_key": "#2A3A4A",
                    "live_border": "#4A5A6A",
                    "live_bg": "#D8DEE8",
                },
                border_width=1,
                show_group_border=True,
                key_format="dot",
                btn_height=26,
            ),
        ),
    ),
    Family(
        id="lift",
        key="3",
        title="Lift",
        blurb="Warm stone / parchment room — raised plates, no outline. Not sage.",
        style="lift",
        looks=(
            _look(
                id="lift_whisper",
                key="1",
                title="Whisper",
                blurb="Soft raise on warm stone — barely there.",
                style="lift",
                **{
                    **_LIFT,
                    "live_bg": "#E4DCD0",
                    "live_hover": "#EDE6DC",
                    "return_bg": "#B0A698",
                },
            ),
            _look(
                id="lift_step",
                key="2",
                title="Step",
                blurb="Clearer light plate on parchment — still no outline.",
                style="lift",
                **{
                    **_LIFT,
                    "bg": "#D0C4B4",
                    "panel": "#DED4C6",
                    "board": "#C0B4A4",
                    "live_bg": "#F0E8DC",
                    "live_hover": "#F7F2EA",
                    "live_key": "#3A2A18",
                },
            ),
            _look(
                id="lift_tight",
                key="3",
                title="Tight",
                blurb="Packed warm plates — denser instrument feel.",
                style="lift",
                **{
                    **_LIFT,
                    "bg": "#C0B4A4",
                    "panel": "#D0C4B4",
                    "live_bg": "#E8E0D4",
                },
                btn_height=28,
                btn_width=150,
                tight_gap=True,
                group_pad=6,
                font_size=11,
            ),
        ),
    ),
    Family(
        id="type",
        key="4",
        title="Type",
        blurb="Ink room — near-black page, type-only chrome. Should slam dark vs sage.",
        style="type",
        looks=(
            _look(
                id="type_bracket",
                key="1",
                title="Bracket",
                blurb="[D] Label on ink — no rails.",
                style="type",
                **_TYPE,
                btn_height=26,
                btn_width=150,
            ),
            _look(
                id="type_dot",
                key="2",
                title="Dot",
                blurb="D · Label — notebook quiet on charcoal.",
                style="type",
                **{
                    **_TYPE,
                    "bg": "#12141A",
                    "panel": "#1C1E24",
                    "live_bg": "#343A44",
                    "live_hover": "#404850",
                    "live_key": "#D0D8E0",
                    "live_border": "#8A9AAA",
                },
                key_format="dot",
                btn_height=26,
            ),
            _look(
                id="type_bare",
                key="3",
                title="Bare",
                blurb="D Label — least chrome; slightly warmer ink.",
                style="type",
                **{
                    **_TYPE,
                    "bg": "#1C1814",
                    "panel": "#28241E",
                    "board": "#141210",
                    "live_bg": "#3A342C",
                    "live_hover": "#484034",
                    "live_key": "#E0D4C0",
                    "live_border": "#A89070",
                    "esc_pop": "#E8C878",
                    "desc_border": "#4A4030",
                },
                key_format="bare",
                btn_height=26,
            ),
        ),
    ),
)


def family_by_id(family_id: str) -> Family | None:
    for family in FAMILIES:
        if family.id == family_id:
            return family
    return None


def look_by_id(look_id: str) -> Look | None:
    for family in FAMILIES:
        for look in family.looks:
            if look.id == look_id:
                return look
    return None


def family_for_look(look_id: str) -> Family | None:
    for family in FAMILIES:
        for look in family.looks:
            if look.id == look_id:
                return family
    return None


def ordered_looks(family: Family, main_look_id: str | None) -> list[Look]:
    """Main look becomes #1; others follow in catalog order."""
    looks = list(family.looks)
    if not main_look_id:
        return looks
    main = next((L for L in looks if L.id == main_look_id), None)
    if main is None:
        return looks
    rest = [L for L in looks if L.id != main_look_id]
    return [main, *rest]


def default_look() -> Look:
    # Colour lean: Type → Bracket
    return look_by_id("type_bracket") or FAMILIES[0].looks[0]


LEGACY_THEME_MAP = {
    "thread": "thread_fine",
    "rail": "thread_fine",
    "rail_thread": "thread_fine",
    "rail_standard": "thread_wide",
    "rail_plank": "thread_moss",
    "rail_paren": "thread_dot",
    "rail_boxed": "thread_tall",
    "rim": "rim_hairline",
    "rim_heavy": "rim_hairline",
    "rim_frame": "rim_open",
    "lift": "lift_whisper",
    "lift_slab": "lift_step",
    "lift_softheader": "lift_tight",
    "type": "type_bracket",
    "type_shout": "type_bracket",
    "type_lined": "type_dot",
    "harbor": "thread_fine",
    "ember": "lift_step",
    "moss": "thread_moss",
    "plum": "type_bracket",
}


def resolve_look_id(raw: str | None) -> str:
    if not raw:
        return default_look().id
    if look_by_id(raw) is not None:
        return raw
    mapped = LEGACY_THEME_MAP.get(raw)
    if mapped and look_by_id(mapped) is not None:
        return mapped
    return default_look().id


THEMES = FAMILIES


def theme_by_id(theme_id: str) -> Look:
    return look_by_id(resolve_look_id(theme_id)) or default_look()


def resolve_theme_id(raw: str | None) -> str:
    return resolve_look_id(raw)
