"""Semantic colour tokens and the application stylesheet.

Dark theme only for v1; the tokens are already semantic so a light dict and
a runtime toggle can land later without touching widget code.
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
}

TOKENS = DARK


def build_qss(tokens: dict[str, str] = TOKENS) -> str:
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
QMenuBar::item:selected {{
    background: {tokens["accent"]};
    color: {tokens["accent_text"]};
}}
QMenu {{
    background: {tokens["panel_bg"]};
    border: 1px solid {tokens["border"]};
}}
QMenu::item:selected {{
    background: {tokens["accent"]};
    color: {tokens["accent_text"]};
}}
QListWidget, QPlainTextEdit, QTextBrowser, QLineEdit, QComboBox {{
    background: {tokens["panel_bg"]};
    border: 1px solid {tokens["border"]};
    border-radius: 4px;
    selection-background-color: {tokens["accent"]};
}}
QLineEdit:enabled:focus, QPlainTextEdit:enabled:focus,
QListWidget:enabled:focus, QComboBox:enabled:focus {{
    border: 2px solid {tokens["focus"]};
}}
QPushButton {{
    background: {tokens["panel_bg"]};
    border: 2px solid {tokens["border"]};
    border-radius: 4px;
    padding: 6px 14px;
}}
QPushButton:enabled:hover {{
    border: 2px solid {tokens["focus"]};
}}
QPushButton:enabled:focus {{
    border: 2px solid {tokens["focus"]};
}}
QPushButton:disabled {{
    color: {tokens["muted_text"]};
    background: {tokens["window_bg"]};
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
QStatusBar {{
    background: {tokens["panel_bg"]};
    color: {tokens["muted_text"]};
}}
QCheckBox:enabled:focus {{
    border: 1px solid {tokens["focus"]};
}}
QLabel#Heading {{
    font-size: 12pt;
    font-weight: bold;
}}
"""
