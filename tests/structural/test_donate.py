"""The donate button's claims, asserted rather than trusted.

Three things have to stay true and none of them is visible from reading a
diff. The address must be the one Oliver generated for this application, so
it is asserted literally: a copied address from another project sends a
supporter's money against the wrong thing; a typo sends it nowhere. It
must have exactly one home, so a second copy cannot drift out of step with
the first. And the button must reach the browser by handing the address to
the desktop, not by opening anything itself, because this application's
headline claim is that it never touches the network.

That last point is the reason this suite sits beside test_no_network.py
rather than in a UI test. The invariant here is structural: it is about which
module knows the address and how the address leaves the process, neither of
which needs a running window to check.
"""

from __future__ import annotations

from postalgambit.version import DONATE_URL
from tests.structural.scan import (
    REPO_ROOT,
    imports_of,
    iter_shipped_modules,
    relative_name,
)

# The address Oliver generated for Postal Gambit. Written out here in full so
# that changing it in the application has to be a deliberate act that changes
# this line too, rather than something a stray keystroke can do quietly.
EXPECTED_DONATE_URL = "https://www.paypal.com/ncp/payment/D7D4B3P2WPCUY"

# The one module allowed to know the address, plus the seam the donate
# path leaves through.
DONATE_URL_HOME = "postalgambit/version.py"
EXTERNAL_OPEN_MODULE = "postalgambit/ui/links.py"

# Two places called the desktop opener directly before the seam existed: the
# export dialog hands over a mailto: URI and the update check opens a release
# page. Both are named rather than swept up, because routing the mail
# transport through a new seam is a change to the product's core path and has
# nothing to do with donations. Naming them keeps the list from growing
# quietly: a NEW direct caller fails here and has to be argued for.
KNOWN_DIRECT_CALLERS = {
    "postalgambit/ui/dialogs/export_dialog.py",
    "postalgambit/ui/update_check.py",
}

# Everything the seam is allowed to import. Kept tight on purpose: the whole
# value of a one-function module is that its dependencies can be read at a
# glance, so anything arriving beyond this list has to be argued for here.
DESKTOP_OPEN_IMPORTS = {"__future__", "PySide6.QtCore", "PySide6.QtGui"}


def _modules_naming_the_url() -> list[str]:
    found = []
    for path in iter_shipped_modules():
        if EXPECTED_DONATE_URL in path.read_text(encoding="utf-8"):
            found.append(relative_name(path))
    return sorted(found)


class TestTheAddress:
    def test_the_address_is_the_one_generated_for_this_app(self) -> None:
        assert DONATE_URL == EXPECTED_DONATE_URL

    def test_the_address_is_https(self) -> None:
        assert DONATE_URL.startswith("https://")

    def test_the_address_has_exactly_one_home(self) -> None:
        naming = _modules_naming_the_url()
        assert naming == [DONATE_URL_HOME], (
            "The donation address must appear in exactly one shipped module "
            f"({DONATE_URL_HOME}). A second copy drifts out of step with the "
            "first and one of them then sends money nowhere.\n"
            f"Found in: {naming}"
        )


class TestTheAddressLeavesByTheDesktop:
    """The button opens a browser without this application opening anything.

    test_no_network.py proves no shipped module imports networking. This adds
    the other half: the donate path reaches the outside world through one
    named seam, so it cannot quietly become a fetch later.
    """

    def test_the_seam_ships(self) -> None:
        scanned = {relative_name(path) for path in iter_shipped_modules()}
        assert EXTERNAL_OPEN_MODULE in scanned

    def test_the_seam_asks_the_desktop(self) -> None:
        path = REPO_ROOT / EXTERNAL_OPEN_MODULE
        source = path.read_text(encoding="utf-8")
        assert "QDesktopServices" in source
        assert imports_of(path) <= DESKTOP_OPEN_IMPORTS

    def test_no_new_module_calls_the_desktop_opener_directly(self) -> None:
        callers = set()
        for path in iter_shipped_modules():
            if relative_name(path) == EXTERNAL_OPEN_MODULE:
                continue
            if "QDesktopServices" in path.read_text(encoding="utf-8"):
                callers.add(relative_name(path))
        assert callers == KNOWN_DIRECT_CALLERS, (
            "A module opens an address without going through "
            f"{EXTERNAL_OPEN_MODULE}. Two predate the seam and are named in "
            "KNOWN_DIRECT_CALLERS; anything else belongs behind the seam, so "
            "that what leaves this application can be read in one place.\n"
            f"Unexpected: {sorted(callers - KNOWN_DIRECT_CALLERS)}\n"
            f"Gone from the list: {sorted(KNOWN_DIRECT_CALLERS - callers)}"
        )

    def test_the_donate_path_uses_the_seam(self) -> None:
        window = (REPO_ROOT / "postalgambit/ui/main_window.py").read_text(
            encoding="utf-8"
        )
        assert "from postalgambit.ui.links import open_externally" in window
        assert "QDesktopServices" not in window


class TestTheButtonIsWiredToTheSlot:
    """A button connected to nothing looks identical to one that works."""

    def test_the_window_connects_the_donate_button(self) -> None:
        source = (REPO_ROOT / "postalgambit/ui/main_window.py").read_text(
            encoding="utf-8"
        )
        assert "bottom_tray.donate_button.clicked.connect" in source

    def test_the_tray_is_in_the_focus_ring(self) -> None:
        source = (REPO_ROOT / "postalgambit/ui/main_window.py").read_text(
            encoding="utf-8"
        )
        assert "*self.bottom_tray.ring_stops()" in source

    def test_the_tray_is_not_itself_a_focus_stop(self) -> None:
        """A container never takes focus; only the control inside it does."""
        source = (REPO_ROOT / "postalgambit/ui/bottom_tray.py").read_text(
            encoding="utf-8"
        )
        assert "self.setFocusPolicy(Qt.FocusPolicy.NoFocus)" in source

    def test_the_tray_paints_its_own_border(self) -> None:
        """A QWidget subclass ignores its stylesheet border without this.

        Measured: with the rule in place and the attribute absent, the top
        edge came out in the parent's fill rather than the border colour, so
        the foot lost the line that makes it read as a foot while the
        stylesheet still looked correct.
        """
        source = (REPO_ROOT / "postalgambit/ui/bottom_tray.py").read_text(
            encoding="utf-8"
        )
        assert "WA_StyledBackground" in source

    def test_the_tooltip_says_the_browser_opens(self) -> None:
        """The picture carries no meaning on its own, so the words must."""
        from postalgambit.ui.bottom_tray import DONATE_TOOLTIP

        assert "browser" in DONATE_TOOLTIP.lower()

    def test_the_slot_reports_a_desktop_that_declined(self) -> None:
        """Silence leaves a user pressing a button that does nothing."""
        source = (REPO_ROOT / "postalgambit/ui/main_window.py").read_text(
            encoding="utf-8"
        )
        assert "def open_donation" in source
        slot = source.split("def open_donation")[1].split("\n    def ")[0]
        assert "if not open_externally(DONATE_URL)" in slot
        assert "QMessageBox.warning" in slot
