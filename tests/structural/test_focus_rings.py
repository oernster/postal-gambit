"""A pane never paints a focus ring; the stylesheet half of that invariant.

Focus belongs to controls. A ring drawn round a container tells the user
nothing they can act on, so no rule may put one there. Three shapes are
forbidden: a ring selector naming a container class or the universal
selector, since a Qt class selector matches every SUBCLASS; any ring on an
item view, whose current row is already the indicator; and a hover ring on
any region, a widget the pointer rests inside rather than points at.

The companion check, that no pane is reachable by Tab at all, is in
`test_focus_chain.py`. Neither can settle whether a NATIVE focus rect is
drawn: a focused QPushButton diffs to zero changed pixels under every bundled
style, so a pixel diff would prove nothing. That half is confirmed on the
running application, by eye.
"""

from __future__ import annotations

import pytest

from installer.ui.themes import STYLESHEET as INSTALLER_SHEET
from postalgambit.ui.theme import DARK, LIGHT, build_qss
from tests.structural.focus_scan import (
    CONTAINER_SELECTORS,
    EDITABLE_FIELD_RING_EXEMPTIONS,
    ITEM_VIEW_SELECTORS,
    REGION_SELECTORS,
    TEXT_VIEW_SELECTORS,
    ring_selectors,
    text_view_rings,
)

_THEMES = [DARK, LIGHT]
_THEME_IDS = ["dark", "light"]
_SHEETS = [build_qss(DARK), build_qss(LIGHT), INSTALLER_SHEET]
_SHEET_IDS = ["dark", "light", "installer"]


class TestNoTextViewRingsInAnyState:
    """About, a licence and the email preview keep their resting border.

    Tab reaching one of them rang the whole page; so would a click, a hover or
    a disabled state, so every pseudo-state counts. The editable paste box is
    the documented exemption: it is typed into, so it is a control.
    """

    @pytest.mark.parametrize("sheet", _SHEETS, ids=_SHEET_IDS)
    def test_no_text_view_border_is_tied_to_a_state(self, sheet) -> None:
        offences = text_view_rings(sheet)
        assert offences == [], (
            "A text view is a pane holding words; it rings in no state, Tab "
            "included. Only an editable field named by object name may ring, "
            "listed in EDITABLE_FIELD_RING_EXEMPTIONS.\n"
            f"{offences}"
        )

    @pytest.mark.parametrize("sheet", _SHEETS, ids=_SHEET_IDS)
    def test_no_pane_or_item_view_rings_in_the_sheet(self, sheet) -> None:
        offences = [
            selector
            for head, _state, selector in ring_selectors(sheet)
            if head in CONTAINER_SELECTORS | ITEM_VIEW_SELECTORS
        ]
        assert offences == []

    def test_the_exemption_is_narrow_and_in_use(self) -> None:
        """Each exemption names one editable field, on focus, by object name."""
        sheet = build_qss(DARK)
        for selector in EDITABLE_FIELD_RING_EXEMPTIONS:
            head, _, rest = selector.partition("#")
            assert head in TEXT_VIEW_SELECTORS and rest, selector
            assert selector.endswith(":enabled:focus"), selector
            assert ":hover" not in selector, selector
            assert ("focus", selector) in {
                (state, found) for _h, state, found in ring_selectors(sheet)
            }, f"{selector} is exempted but no longer in the sheet"

    def test_the_scan_catches_each_text_view_ring(self) -> None:
        """The guard bites: each planted shape is named; the exemption is not."""
        sheet = (
            "QPlainTextEdit:enabled:focus, QTextBrowser:enabled:focus "
            "{ border: 2px solid #f0b944; }\n"
            "QTextEdit#LicenceView:focus { border-color: #f0b944; }\n"
            "QTextBrowser:disabled { border: 2px solid #d9534f; }\n"
            "QTextBrowser, QPlainTextEdit { border: 1px solid #39404f; }\n"
            f"{min(EDITABLE_FIELD_RING_EXEMPTIONS)} "
            "{ border: 2px solid #f0b944; }\n"
            "QTextBrowser:focus { border-radius: 6px; }\n"
        )
        assert text_view_rings(sheet) == [
            "QPlainTextEdit:enabled:focus",
            "QTextBrowser:enabled:focus",
            "QTextEdit#LicenceView:focus",
            "QTextBrowser:disabled",
        ]


class TestTheStylesheetNeverRingsAPane:
    """The rule is either in the sheet or it is not, so this is exact."""

    @pytest.mark.parametrize("tokens", _THEMES, ids=_THEME_IDS)
    def test_no_ring_selector_names_a_container(self, tokens) -> None:
        offences = [
            selector
            for head, _state, selector in ring_selectors(build_qss(tokens))
            if head in CONTAINER_SELECTORS
        ]
        assert offences == [], (
            "A Qt class selector matches every subclass, so a ring named "
            "against a container reaches every scroll area, list and label in "
            "the application. Name the control classes instead.\n"
            f"{offences}"
        )

    @pytest.mark.parametrize("tokens", _THEMES, ids=_THEME_IDS)
    def test_no_item_view_rings_in_any_state(self, tokens) -> None:
        offences = [
            selector
            for head, _state, selector in ring_selectors(build_qss(tokens))
            if head in ITEM_VIEW_SELECTORS
        ]
        assert offences == [], (
            "An item view needs no ring in any state: its current row is the "
            "indicator. A ring round the whole view also fires on a click "
            "into the empty space below the last item, outlining everything "
            "while selecting nothing.\n"
            f"{offences}"
        )

    @pytest.mark.parametrize("tokens", _THEMES, ids=_THEME_IDS)
    def test_no_region_rings_on_hover(self, tokens) -> None:
        offences = [
            selector
            for head, state, selector in ring_selectors(build_qss(tokens))
            if state == "hover" and head in REGION_SELECTORS
        ]
        assert offences == [], (
            "A control is pointed AT; a region is pointed INTO. The pointer "
            "rests inside a region for as long as the window is open, so a "
            "hover ring there reports where the mouse is rather than what is "
            "about to be pressed.\n"
            f"{offences}"
        )

    @pytest.mark.parametrize("tokens", _THEMES, ids=_THEME_IDS)
    def test_the_scan_can_see_a_ring_at_all(self, tokens) -> None:
        """The three checks above pass trivially if nothing is detected.

        A parsing slip once made every ring read as invisible, so all three
        passed over a sheet full of them. This is the positive control that
        would have caught it.
        """
        states = {state for _head, state, _sel in ring_selectors(build_qss(tokens))}
        assert states == {"focus", "hover"}, (
            "The scanner found no focus rings or no hover rings, which means "
            "it is not reading the stylesheet correctly rather than that the "
            "stylesheet is clean."
        )
