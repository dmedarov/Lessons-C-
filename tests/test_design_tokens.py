from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "static" / "styles.css"


def _block_after(css: str, selector: str) -> str:
    start = css.index(selector)
    brace = css.index("{", start)
    depth = 0
    for index in range(brace, len(css)):
        if css[index] == "{":
            depth += 1
        elif css[index] == "}":
            depth -= 1
            if depth == 0:
                return css[brace + 1 : index]
    raise AssertionError(f"Unclosed CSS block for {selector}")


def _tokens_for(selector: str) -> dict[str, str]:
    css = CSS.read_text()
    block = _block_after(css, selector)
    return dict(re.findall(r"(--[\w-]+):\s*([^;]+);", block))


def _hex(value: str) -> str:
    value = value.strip().lower()
    if not re.fullmatch(r"#[0-9a-f]{3}(?:[0-9a-f]{3})?", value):
        raise AssertionError(f"Expected solid hex color token, got {value!r}")
    raw = value[1:]
    if len(raw) == 3:
        raw = "".join(char * 2 for char in raw)
    return raw


def _relative_luminance(value: str) -> float:
    raw = _hex(value)
    channels = [int(raw[index : index + 2], 16) / 255 for index in (0, 2, 4)]

    def linearize(channel: float) -> float:
        if channel <= 0.03928:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = [linearize(channel) for channel in channels]
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast(foreground: str, background: str) -> float:
    fg_luminance = _relative_luminance(foreground)
    bg_luminance = _relative_luminance(background)
    lighter = max(fg_luminance, bg_luminance)
    darker = min(fg_luminance, bg_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def test_design_token_contrast_pairs_meet_wcag_aa() -> None:
    light = _tokens_for(":root")
    dark = {**light, **_tokens_for(':root[data-theme="dark"]')}

    pairs = [
        ("light primary text", light["--ink"], light["--bg-bottom"], 4.5),
        ("light strong text", light["--ink-strong"], light["--bg-bottom"], 4.5),
        ("light muted text", light["--muted"], light["--bg-bottom"], 4.5),
        ("light primary button text", "#ffffff", light["--brand"], 4.5),
        ("light brand on white", light["--brand"], "#ffffff", 4.5),
        ("light success status", light["--success"], light["--bg-bottom"], 4.5),
        ("light warning status", light["--warning"], light["--bg-bottom"], 4.5),
        ("light danger status", light["--danger"], light["--bg-bottom"], 4.5),
        ("dark primary text", dark["--ink"], dark["--bg-bottom"], 4.5),
        ("dark strong text", dark["--ink-strong"], dark["--bg-bottom"], 4.5),
        ("dark muted text", dark["--muted"], dark["--bg-bottom"], 4.5),
        ("dark success status", dark["--success"], dark["--bg-bottom"], 4.5),
        ("dark warning status", dark["--warning"], dark["--bg-bottom"], 4.5),
        ("dark danger status", dark["--danger"], dark["--bg-bottom"], 4.5),
    ]

    failures = [
        f"{name}: {_contrast(foreground, background):.2f}:1 < {minimum}:1"
        for name, foreground, background, minimum in pairs
        if _contrast(foreground, background) < minimum
    ]
    assert failures == []
