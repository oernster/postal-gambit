"""Stylesheet scanning for the focus-ring invariant.

Reads the REAL stylesheet rather than its source, by parsing what `build_qss`
returns. That sidesteps the f-string braces entirely; more importantly, it
checks the thing the application actually applies.

Sits beside `scan.py` as a helper the suites share, rather than as a suite of
its own.
"""

from __future__ import annotations

import re

from postalgambit.ui.theme import IMPORT_TEXT

# A Qt class selector matches every SUBCLASS, so each of these can land a
# border on a pane that merely holds other widgets: `QFrame:focus` reaches
# every scroll area, list, table and label in the application.
CONTAINER_SELECTORS = frozenset(
    {
        "*",
        "QWidget",
        "QFrame",
        "QAbstractScrollArea",
        "QScrollArea",
        "QGroupBox",
        "QStackedWidget",
        "QSplitter",
        "QTabWidget",
        "QScrollBar",
    }
)

# An item view rings in NO state: focusing one paints its current row with no
# stylesheet rule at all, so a rectangle round the whole view is redundant and
# fires on a click into the empty space below the last item.
ITEM_VIEW_SELECTORS = frozenset(
    {
        "QAbstractItemView",
        "QListView",
        "QListWidget",
        "QTableView",
        "QTableWidget",
        "QTreeView",
        "QTreeWidget",
    }
)

# Widgets the pointer rests INSIDE rather than points AT. A hover ring here
# reports where the mouse happens to be rather than marking what is about to
# be pressed, while the pointer sits inside one for as long as the window is
# open. The focus half is legitimate for a region carrying no items.
REGION_SELECTORS = ITEM_VIEW_SELECTORS | frozenset(
    {
        "QAbstractScrollArea",
        "QScrollArea",
        "QTextBrowser",
        "QTextEdit",
        "QPlainTextEdit",
        "QGraphicsView",
    }
)

# A TEXT view (About, a licence, the email preview) rings in NO state, focus,
# hover and disabled included: it is a pane holding words, so a border tied to
# any pseudo-state outlines the page rather than a control.
TEXT_VIEW_SELECTORS = frozenset({"QTextBrowser", "QTextEdit", "QPlainTextEdit"})

# The one exemption is deliberately narrow. An EDITABLE text field is a control
# (it is typed into), so it may ring on focus; it is named by object name only,
# so the rule cannot reach a read-only text view of the same class. Each
# entry must be the whole selector; the runtime suite proves the widget so
# named is editable. Adding an entry means adding an editable field.
EDITABLE_FIELD_RING_EXEMPTIONS = frozenset(
    {f"QPlainTextEdit#{IMPORT_TEXT}:enabled:focus"}
)

_RING_PROPERTIES = ("border", "outline")
# Border properties that shape a box without drawing an edge round it.
_NOT_A_RING = ("border-radius", "border-spacing", "border-collapse", "border-image")
# Compared against whitespace-separated TOKENS, never as substrings. "0" is a
# substring of "#f0b944", which once made every ring rule read as invisible
# and left all three stylesheet checks passing over a sheet full of them.
_INVISIBLE_KEYWORDS = frozenset({"none", "transparent", "initial", "unset"})
_ZERO_WIDTHS = frozenset({"0", "0px"})


def rules(sheet: str) -> list[tuple[str, str]]:
    """Every (selector group, body) pair in a flat stylesheet.

    Comments go first. A comment sits between the previous rule's closing
    brace and the next selector, so leaving it in makes its prose part of that
    selector.
    """
    sheet = re.sub(r"/\*.*?\*/", " ", sheet, flags=re.DOTALL)
    found = []
    for chunk in sheet.split("}"):
        if "{" not in chunk:
            continue
        selector, _, body = chunk.partition("{")
        found.append((selector.strip(), body.strip()))
    return found


def paints_a_ring(body: str) -> bool:
    """True when this rule body draws a visible edge."""
    for declaration in body.split(";"):
        name, _, value = declaration.partition(":")
        name = name.strip()
        if name in _NOT_A_RING:
            continue
        if name not in _RING_PROPERTIES and not name.startswith("border-"):
            continue
        tokens = value.split()
        if not tokens:
            continue
        if any(token in _INVISIBLE_KEYWORDS for token in tokens):
            continue
        if tokens[0] in _ZERO_WIDTHS:
            continue
        return True
    return False


def ring_selectors(sheet: str) -> list[tuple[str, str, str]]:
    """(class, pseudo-state, whole selector) for every rule painting a ring.

    Subcontrol rules (`::item`) are skipped: the item level is a different
    question and is deliberately untouched by this invariant.
    """
    found = []
    for group, body in rules(sheet):
        if not paints_a_ring(body):
            continue
        for selector in (part.strip() for part in group.split(",")):
            if not selector or "::" in selector:
                continue
            state = ""
            if ":hover" in selector:
                state = "hover"
            elif ":focus" in selector:
                state = "focus"
            if not state:
                continue
            head = selector.split(":")[0].split("#")[0].strip()
            found.append((head, state, selector))
    return found


def text_view_rings(sheet: str) -> list[str]:
    """Every selector tying a visible border on a text view to any state.

    Wider than `ring_selectors`: any pseudo-state counts (focus, hover,
    disabled, anything), because a text view keeps its resting border in all
    of them. The documented editable-field exemptions are left out.
    """
    found = []
    for group, body in rules(sheet):
        if not paints_a_ring(body):
            continue
        for selector in (" ".join(part.split()) for part in group.split(",")):
            subject = re.split(r"[\s>]+", selector)[-1] if selector else ""
            if ":" not in subject or "::" in subject:
                continue
            if re.split(r"[:#\[.]", subject)[0] not in TEXT_VIEW_SELECTORS:
                continue
            if selector not in EDITABLE_FIELD_RING_EXEMPTIONS:
                found.append(selector)
    return found
