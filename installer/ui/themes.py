"""The installer's palette, stylesheet and layout constants.

The palette is Postal Gambit's own: the application's dark background with its
blue accent for primary surfaces and its amber focus colour for the hover
border. Every QPushButton carries a transparent 2px border by default so the
hover border never reflows the layout, and every hover reaction is gated on
:enabled so a disabled button stays muted and shows no border change. The theme
travels with the app; only the functionality is shared with the other
installers in the portfolio. British spelling is used in comments. No em dashes
appear anywhere.
"""

from __future__ import annotations

# --- palette ----------------------------------------------------------------

BACKGROUND = "#1b1e26"
SURFACE = "#232733"
SURFACE_RAISED = "#2b3140"
BORDER = "#39404f"
TEXT = "#e6e9f0"
TEXT_MUTED = "#9aa3b5"
ACCENT = "#3d7bd9"
ACCENT_TEXT = "#ffffff"
HOVER = "#f0b944"
DANGER = "#d9534f"
DISABLED_TEXT = "#5b6470"

# --- geometry ---------------------------------------------------------------

WINDOW_WIDTH = 620
WINDOW_HEIGHT = 600
LICENCE_DIALOG_HEIGHT = 540
LICENCE_FONT_PX = 12
ICON_PX = 56
DIVIDER_PX = 1
BORDER_PX = 1
HOVER_BORDER_PX = 2
TEXT_PADDING_PX = 8
SIDES = 2
WIDTH_SAFETY_PX = 8
MARGIN_SIDE = 36
MARGIN_TOP = 28
MARGIN_BOTTOM = 24
DIALOG_MARGIN = 20
SECTION_SPACING = 14
HEADER_SPACING = 14
TITLE_BLOCK_SPACING = 0
BUTTON_GAP = 10
PROGRESS_HEIGHT_PX = 10

# --- object names, so the stylesheet and the widgets agree ------------------

HEADER_TITLE = "HeaderTitle"
HEADER_VERSION = "HeaderVersion"
SUBTITLE = "SubTitle"
TAGLINE = "Tagline"
INSTALL_PATH = "InstallPath"
STATUS_LINE = "StatusLine"
DIVIDER = "Divider"
LICENCE_BUTTON = "LicenceButton"
LICENCE_VIEW = "LicenceView"
PRIMARY_ACTION = "PrimaryAction"
SECONDARY_ACTION = "SecondaryAction"
DANGER_ACTION = "DangerAction"
PROGRESS_BAR = "InstallProgress"

STYLESHEET = f"""
QWidget {{
    background: {BACKGROUND}; color: {TEXT}; font-family: 'Segoe UI';
}}
QLabel#{HEADER_TITLE} {{ font-size: 30px; font-weight: 700; color: {ACCENT}; }}
QLabel#{HEADER_VERSION} {{ font-size: 13px; color: {TEXT_MUTED}; }}
QLabel#{SUBTITLE} {{ font-size: 18px; font-weight: 700; color: {ACCENT}; }}
QLabel#{TAGLINE} {{ font-size: 13px; color: {TEXT_MUTED}; }}
QLabel#{INSTALL_PATH} {{ font-size: 12px; color: {TEXT_MUTED}; }}
QLabel#{STATUS_LINE} {{ font-size: 13px; color: {TEXT}; }}
QFrame#{DIVIDER} {{ background: {BORDER}; border: none; }}
QCheckBox {{ spacing: 10px; font-size: 13px; color: {TEXT}; }}
QCheckBox::indicator {{ width: 16px; height: 16px; }}
QProgressBar#{PROGRESS_BAR} {{
    background: {SURFACE}; border: {BORDER_PX}px solid {BORDER};
    border-radius: 5px; height: {PROGRESS_HEIGHT_PX}px; text-align: center;
    color: transparent;
}}
QProgressBar#{PROGRESS_BAR}::chunk {{ background: {ACCENT}; border-radius: 4px; }}
QPushButton {{
    border: {HOVER_BORDER_PX}px solid transparent;
}}
QPushButton:enabled:hover {{
    border-color: {HOVER};
}}
QPushButton#{LICENCE_BUTTON} {{
    background: {SURFACE}; color: {TEXT};
    padding: 10px 18px; border-radius: 19px; font-size: 14px;
    font-weight: 600;
}}
QPushButton#{PRIMARY_ACTION} {{
    background: {ACCENT}; color: {ACCENT_TEXT};
    padding: 12px 28px; border-radius: 22px; font-size: 14px;
    font-weight: 700; min-width: 150px;
}}
QPushButton#{PRIMARY_ACTION}:enabled:hover {{
    border-color: {HOVER};
}}
QPushButton#{PRIMARY_ACTION}:disabled {{
    background: {SURFACE_RAISED}; color: {DISABLED_TEXT};
}}
QPushButton#{SECONDARY_ACTION} {{
    background: {SURFACE}; color: {TEXT};
    padding: 12px 22px; border-radius: 22px; font-size: 13px;
    font-weight: 600;
}}
QPushButton#{SECONDARY_ACTION}:disabled {{
    background: {SURFACE_RAISED}; color: {DISABLED_TEXT};
}}
QPushButton#{DANGER_ACTION} {{
    background: {SURFACE_RAISED}; color: {DANGER};
    padding: 12px 22px; border-radius: 22px; font-size: 13px;
    font-weight: 600;
}}
QPushButton#{DANGER_ACTION}:disabled {{
    background: {SURFACE_RAISED}; color: {DISABLED_TEXT};
}}
QTextEdit {{
    background: {SURFACE}; border: {BORDER_PX}px solid {BORDER};
    border-radius: 10px; color: {TEXT}; padding: {TEXT_PADDING_PX}px;
}}
QTextEdit#{LICENCE_VIEW} {{
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: {LICENCE_FONT_PX}px;
}}
QDialog {{ background: {BACKGROUND}; }}
"""
