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

from postalgambit.ui.theme import DARK, LIGHT, build_qss
from tests.structural.focus_scan import (
    CONTAINER_SELECTORS,
    ITEM_VIEW_SELECTORS,
    REGION_SELECTORS,
    ring_selectors,
)

_THEMES = [DARK, LIGHT]
_THEME_IDS = ["dark", "light"]


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
