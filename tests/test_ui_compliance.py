from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text()


def test_notification_lists_are_polite_live_regions() -> None:
    for template in ("templates/index.html", "templates/admin.html"):
        html = _read(template)
        assert 'id="notificationsList" aria-live="polite" aria-relevant="additions text"' in html


def test_admin_calendar_glyph_buttons_have_accessible_names() -> None:
    html = _read("templates/admin.html")
    assert 'id="monthPrev" type="button" aria-label="Предишен месец"' in html
    assert 'id="monthNext" type="button" aria-label="Следващ месец"' in html


def test_dialog_helpers_restore_focus_to_trigger() -> None:
    app_js = _read("static/app.js")
    assert app_js.count("const returnFocusTo = document.activeElement instanceof HTMLElement") == 2
    assert app_js.count("returnFocusTo?.focus();") == 2


def test_dialog_helpers_expose_modal_names_and_descriptions() -> None:
    app_js = _read("static/app.js")
    assert app_js.count('dialog.setAttribute("aria-labelledby", titleId);') == 2
    assert app_js.count('dialog.setAttribute("aria-describedby", descriptionId);') == 2
    assert app_js.count('dialog.setAttribute("aria-modal", "true");') == 2
    assert app_js.count("copy.id = descriptionId;") == 2
    assert 'role="alert" aria-live="polite"' in app_js


def test_field_errors_are_programmatically_associated() -> None:
    app_js = _read("static/app.js")
    assert 'inputNode.setAttribute("aria-invalid", "true");' in app_js
    assert 'inputNode.setAttribute("aria-describedby", `${id}Error`);' in app_js
    assert 'inputNode.removeAttribute("aria-describedby");' in app_js


def test_mobile_rail_respects_safe_area() -> None:
    styles = _read("static/styles.css")
    assert "padding-bottom: calc(88px + env(safe-area-inset-bottom));" in styles
    assert "bottom: max(8px, env(safe-area-inset-bottom));" in styles
