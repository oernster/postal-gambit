"""A read-only scrolling region is a focus stop only while it overflows.

A pane holds controls; it is not one, so it does not take focus. The single
exception is a region the user has to be able to READ from the keyboard: a
licence text, the About body, the email preview. Those carry no controls of
their own, so if they were not stops their content could not be scrolled
without a mouse.

The exception is bounded by the thing that justifies it. A region that fits
its viewport scrolls nowhere, so it is not actionable and drops off the ring;
one that overflows earns its place back. That makes the policy a function of
the window size at this moment rather than a setting chosen once at
construction, which is why it is recomputed rather than assigned.

The viewport is set NoFocus alongside, because it is a separate focusable
child: setting only the outer widget leaves it reachable.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Slot
from PySide6.QtWidgets import QAbstractScrollArea


class OverflowFocus(QObject):
    """Keeps a region's focus policy equal to whether it can scroll."""

    def __init__(self, region: QAbstractScrollArea) -> None:
        # Parented to the region so it lives exactly as long as its subject.
        super().__init__(region)
        self._region = region
        region.viewport().setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # rangeChanged is the signal that answers the question directly: it
        # fires whenever the scrollable extent moves, which covers a resize
        # and a change of content without needing an event filter for each.
        # Both bars are watched because either can be the one that overflows.
        region.verticalScrollBar().rangeChanged.connect(self.sync)
        region.horizontalScrollBar().rangeChanged.connect(self.sync)
        self.sync()

    @Slot()
    def sync(self, *_range: int) -> None:
        """Match the focus policy to whether there is anywhere to scroll."""
        policy = Qt.FocusPolicy.TabFocus if self.overflows() else Qt.FocusPolicy.NoFocus
        if self._region.focusPolicy() != policy:
            self._region.setFocusPolicy(policy)

    def overflows(self) -> bool:
        """True when the region actually has somewhere to scroll."""
        return (
            self._region.verticalScrollBar().maximum() > 0
            or self._region.horizontalScrollBar().maximum() > 0
        )
