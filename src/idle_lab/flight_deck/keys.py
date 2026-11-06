"""Virtual-key helpers for the flight deck expand binding."""

from __future__ import annotations

# US keyboard backtick / tilde key. Remappable per anchor.
DEFAULT_EXPAND_VK = 0xC0  # VK_OEM_3
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_0 = 0x30
VK_9 = 0x39
VK_A = 0x41
VK_Z = 0x5A

# Common OEM labels for the remap UI.
_OEM_LABELS = {
    0xBA: ";",  # VK_OEM_1
    0xBB: "=",  # VK_OEM_PLUS
    0xBC: ",",  # VK_OEM_COMMA
    0xBD: "-",  # VK_OEM_MINUS
    0xBE: ".",  # VK_OEM_PERIOD
    0xBF: "/",  # VK_OEM_2
    0xC0: "`",  # VK_OEM_3
    0xDB: "[",  # VK_OEM_4
    0xDC: "\\",  # VK_OEM_5
    0xDD: "]",  # VK_OEM_6
    0xDE: "'",  # VK_OEM_7
}

# Reserved menu tokens (not taken from keymap JSON as free keys).
BACK_TOKEN = "X"
DESCRIBE_TOKEN = "D"
SPACE_TOKEN = "Space"


def normalize_menu_key(token: str) -> str:
    """Canonical compare form: SPACE, X, A–Z, 0–9, OEM glyphs."""

    raw = token if token is not None else ""
    if raw == " " or raw == "\u00a0":
        return "SPACE"
    text = raw.strip()
    if not text:
        return ""
    upper = text.upper()
    if upper in {"SPACE", "SPC"}:
        return "SPACE"
    if upper == "X":
        return "X"
    if upper == "D":
        return "D"
    if len(text) == 1:
        return upper
    return upper


def display_menu_key(token: str) -> str:
    norm = normalize_menu_key(token)
    if norm == "SPACE":
        return "Space"
    return token.strip() if token else norm


def vk_label(vk: int) -> str:
    code = int(vk)
    if code == VK_SPACE:
        return "Space"
    if VK_A <= code <= VK_Z:
        return chr(code)
    if VK_0 <= code <= VK_9:
        return chr(code)
    if code in _OEM_LABELS:
        return _OEM_LABELS[code]
    if 0x70 <= code <= 0x7B:  # F1–F12
        return f"F{code - 0x6F}"
    if code == VK_ESCAPE:
        return "Esc"
    return f"VK_{code:02X}"


def vk_from_menu_token(token: str) -> int | None:
    """Map a keymap JSON key token (``Space``, ``S``, ``1``, ``` ``) to a VK code."""

    norm = normalize_menu_key(token)
    if not norm:
        return None
    if norm == "SPACE":
        return VK_SPACE
    if len(norm) == 1:
        ch = norm
        if "A" <= ch <= "Z":
            return ord(ch)
        if "0" <= ch <= "9":
            return ord(ch)
        for vk, label in _OEM_LABELS.items():
            if token.strip() == label:
                return vk
        return None
    if norm.startswith("F") and norm[1:].isdigit():
        n = int(norm[1:])
        if 1 <= n <= 12:
            return 0x6F + n
    if norm in {"ESC", "ESCAPE"}:
        return VK_ESCAPE
    return None


def menu_token_from_vk(vk: int) -> str | None:
    code = int(vk)
    if code == VK_SPACE:
        return SPACE_TOKEN
    if VK_A <= code <= VK_Z:
        return chr(code)
    if VK_0 <= code <= VK_9:
        return chr(code)
    if code in _OEM_LABELS:
        return _OEM_LABELS[code]
    return None
