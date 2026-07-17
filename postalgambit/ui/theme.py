"""Semantic colour tokens and the application stylesheet.

Two themes share one semantic token set, so widget code never names a
colour: the main window resolves the persisted theme name to a token dict
and hands it to build_qss and the board.
"""

from __future__ import annotations

DARK = {
    "window_bg": "#1b1e26",
    "panel_bg": "#232733",
    "text": "#e6e9f0",
    "muted_text": "#9aa3b5",
    "accent": "#3d7bd9",
    "accent_text": "#ffffff",
    "focus": "#f0b944",
    "border": "#39404f",
    "danger": "#d9534f",
    "square_light": "#aab4c4",
    "square_dark": "#5c6b82",
    "square_selected": "#f0b944",
    "square_target": "#6fbf73",
    "square_cursor": "#f0b944",
    "square_check": "#d9534f",
    "piece_light": "#f5f5f5",
    "piece_dark": "#1a1a1a",
}

LIGHT = {
    "window_bg": "#eef1f6",
    "panel_bg": "#ffffff",
    "text": "#1e2433",
    "muted_text": "#5b6579",
    "accent": "#3d7bd9",
    "accent_text": "#ffffff",
    "focus": "#d08700",
    "border": "#c3ccdb",
    "danger": "#c94441",
    "square_light": "#f0d9b5",
    "square_dark": "#b58863",
    "square_selected": "#f0b944",
    "square_target": "#4f9d55",
    "square_cursor": "#d08700",
    "square_check": "#c94441",
    "piece_light": "#f8f8f8",
    "piece_dark": "#1a1a1a",
}

THEMES = {"dark": DARK, "light": LIGHT}
DEFAULT_THEME = "dark"

_CONTROL_RADIUS_PX = 10
_BUTTON_RADIUS_PX = 12
_ITEM_RADIUS_PX = 6
_SCROLLBAR_WIDTH_PX = 12
_SCROLLBAR_HANDLE_RADIUS_PX = 4
_INDICATOR_PX = 16
_INDICATOR_RADIUS_PX = 5


def build_qss(tokens: dict[str, str] = DARK) -> str:
    return f"""
QMainWindow, QDialog {{
    background: {tokens["window_bg"]};
    color: {tokens["text"]};
}}
QWidget {{
    color: {tokens["text"]};
    font-size: 10pt;
}}
QMenuBar {{
    background: {tokens["panel_bg"]};
}}
QMenuBar::item {{
    background: transparent;
    padding: 4px 10px;
    border-radius: {_ITEM_RADIUS_PX}px;
}}
QMenuBar::item:selected {{
    background: {tokens["accent"]};
    color: {tokens["accent_text"]};
}}
QMenu {{
    background: {tokens["panel_bg"]};
    border: 1px solid {tokens["border"]};
    padding: 4px;
}}
QMenu::item {{
    background: transparent;
    padding: 5px 28px 5px 14px;
    border-radius: {_ITEM_RADIUS_PX}px;
}}
QMenu::item:selected {{
    background: {tokens["accent"]};
    color: {tokens["accent_text"]};
}}
QMenu::separator {{
    height: 1px;
    background: {tokens["border"]};
    margin: 4px 8px;
}}
QListWidget, QPlainTextEdit, QTextBrowser, QLineEdit, QComboBox {{
    background: {tokens["panel_bg"]};
    border: 1px solid {tokens["border"]};
    border-radius: {_CONTROL_RADIUS_PX}px;
    padding: 3px 6px;
    selection-background-color: {tokens["accent"]};
}}
QLineEdit:enabled:focus, QPlainTextEdit:enabled:focus,
QListWidget:enabled:focus, QComboBox:enabled:focus {{
    border: 2px solid {tokens["focus"]};
}}
QListWidget::item {{
    padding: 2px 4px;
    border-radius: {_ITEM_RADIUS_PX}px;
}}
QListWidget::item:selected {{
    background: {tokens["accent"]};
    color: {tokens["accent_text"]};
}}
QPushButton {{
    background: {tokens["panel_bg"]};
    border: 2px solid {tokens["border"]};
    border-radius: {_BUTTON_RADIUS_PX}px;
    padding: 6px 16px;
}}
QPushButton:enabled:hover {{
    border: 2px solid {tokens["focus"]};
}}
QPushButton:enabled:focus {{
    border: 2px solid {tokens["focus"]};
}}
QPushButton:disabled {{
    color: {tokens["muted_text"]};
    background: {tokens["panel_bg"]};
    border: 2px solid {tokens["danger"]};
}}
QPushButton#Primary {{
    background: {tokens["accent"]};
    color: {tokens["accent_text"]};
    border: 2px solid transparent;
}}
QPushButton#Primary:enabled:hover, QPushButton#Primary:enabled:focus {{
    border: 2px solid {tokens["focus"]};
}}
QPushButton#Danger {{
    background: {tokens["danger"]};
    color: {tokens["accent_text"]};
    border: 2px solid transparent;
}}
QPushButton#Danger:enabled:hover, QPushButton#Danger:enabled:focus {{
    border: 2px solid {tokens["focus"]};
}}
QPushButton#Primary:disabled, QPushButton#Danger:disabled {{
    background: {tokens["panel_bg"]};
    color: {tokens["muted_text"]};
    border: 2px solid {tokens["danger"]};
}}
QCheckBox {{
    border: 2px solid transparent;
    border-radius: {_BUTTON_RADIUS_PX}px;
    padding: 0px 12px;
}}
QCheckBox:enabled:focus {{
    border: 2px solid {tokens["focus"]};
}}
QCheckBox:disabled {{
    border: 2px solid {tokens["danger"]};
    color: {tokens["muted_text"]};
    background: {tokens["panel_bg"]};
}}
QRadioButton:enabled:focus {{
    border: 1px solid {tokens["focus"]};
    border-radius: {_ITEM_RADIUS_PX}px;
}}
QRadioButton:disabled {{
    border: 1px solid {tokens["danger"]};
    border-radius: {_ITEM_RADIUS_PX}px;
}}
QComboBox:disabled {{
    border: 2px solid {tokens["danger"]};
}}
QCheckBox::indicator {{
    width: {_INDICATOR_PX}px;
    height: {_INDICATOR_PX}px;
    border: 1px solid {tokens["border"]};
    border-radius: {_INDICATOR_RADIUS_PX}px;
    background: {tokens["panel_bg"]};
}}
QCheckBox::indicator:checked {{
    background: {tokens["accent"]};
    border: 1px solid {tokens["accent"]};
}}
QCheckBox::indicator:disabled {{
    background: {tokens["window_bg"]};
}}
QScrollBar:vertical {{
    background: transparent;
    width: {_SCROLLBAR_WIDTH_PX}px;
    margin: 2px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: {_SCROLLBAR_WIDTH_PX}px;
    margin: 2px;
}}
QScrollBar::handle {{
    background: {tokens["border"]};
    border-radius: {_SCROLLBAR_HANDLE_RADIUS_PX}px;
}}
QScrollBar::handle:vertical {{
    min-height: 24px;
}}
QScrollBar::handle:horizontal {{
    min-width: 24px;
}}
QScrollBar::handle:hover {{
    background: {tokens["muted_text"]};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0;
    height: 0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}
QGraphicsView {{
    background: transparent;
    border: none;
}}
QStatusBar {{
    background: {tokens["panel_bg"]};
    color: {tokens["muted_text"]};
}}
QLabel#Heading {{
    font-size: 12pt;
    font-weight: bold;
}}
"""
