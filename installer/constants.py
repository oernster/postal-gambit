"""Identity, layout and registry constants for the Postal Gambit setup program.

Every name the installer writes to disk or to the registry is declared here, so
a rename is a single edit and no module carries an inline literal. British
spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

# --- product identity -------------------------------------------------------

# The spaceless identifier used for the payload directory and the install path.
APP_NAME = "PostalGambit"
# The display name shown in all installer text and in the Apps list.
APP_DISPLAY_NAME = "Postal Gambit"
APP_TAGLINE = "Correspondence chess over your own email"
APP_PUBLISHER = "Oliver Ernster"
APP_URL = "https://github.com/oernster/postal-gambit"

# The executable is hyphenated while the payload and install directory are not,
# so the two names are deliberately kept distinct.
EXE_NAME = "postal-gambit.exe"
EXE_SUFFIX = ".exe"

# --- payload layout ---------------------------------------------------------

# Produced by buildinstaller.py: payload/PostalGambit/ holds the bundle's
# non-binary files, payload/PostalGambit.zip holds the full bundle for
# deployment and payload/LICENSE holds the application licence text.
PAYLOAD_DIR_NAME = "payload"
PAYLOAD_ARCHIVE_NAME = "PostalGambit.zip"
LICENSE_FILE_NAME = "LICENSE"
# The installer wrapper carries an as-is notice distinct from the application
# licence, so both are bundled and both have a viewer of their own.
INSTALLER_LICENSE_FILE_NAME = "INSTALLER_LICENSE"
VERSION_FILE_NAME = "VERSION"

ICON_SUBPATH = ("assets", "postal-gambit_icon_256.png")
# The multi-size .ico, used for shortcuts and the Apps-list DisplayIcon so the
# small sizes that Windows search and the taskbar render are present.
SHORTCUT_ICON_SUBPATH = ("assets", "postal-gambit.ico")

# --- per-user locations (no administrator rights required) ------------------

ENV_LOCALAPPDATA = "LOCALAPPDATA"
ENV_APPDATA = "APPDATA"
PROGRAMS_DIR_NAME = "Programs"
START_MENU_SUBPATH = ("Microsoft", "Windows", "Start Menu", "Programs")
DESKTOP_DIR_NAME = "Desktop"
SHORTCUT_EXT = ".lnk"
# The per-user state directory the application writes (games and settings). The
# application keeps it under the home directory rather than under LOCALAPPDATA.
STATE_DIR_NAME = ".postal-gambit"

# --- the registered uninstaller ---------------------------------------------

# A copy of the setup program is placed under the install root, so
# "Apps & features" can re-run it with --uninstall.
UNINSTALLER_SUBDIR = "_uninstall"
UNINSTALLER_NAME = "PostalGambitSetup.exe"
UNINSTALL_FLAG = "--uninstall"
# Under a Nuitka onefile build sys.executable is the unpacked temporary
# bootstrap, so the original launcher is discovered through this instead.
NUITKA_ONEFILE_ENV = "NUITKA_ONEFILE_BINARY"

# --- registry keys (all under HKCU) -----------------------------------------

# This is what makes the app appear in "Apps & features" with a working
# Uninstall button.
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PostalGambit"
# Launching the app at Windows sign-in, per user so no admin rights are needed.
RUN_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "PostalGambit"
# The app registers its notification name under this Application User Model ID
# at startup; uninstall removes that registration.
APP_AUMID = "uk.codecrafter.PostalGambit"
INSTALLER_AUMID = "uk.codecrafter.PostalGambit.installer"
AUMID_CLASSES_SUBKEY = r"Software\Classes\AppUserModelId"

# The postalgambit: URI scheme. Clicking an import link in an email launches
# the installed app with the link as its only argument.
URL_SCHEME = "postalgambit"
URL_CLASS_KEY = rf"Software\Classes\{URL_SCHEME}"
URL_CLASS_DESCRIPTION = "URL:Postal Gambit Link"
URL_PROTOCOL_VALUE = "URL Protocol"
URL_DEFAULT_ICON_SUBKEY = "DefaultIcon"
URL_OPEN_COMMAND_SUBKEY = r"shell\open\command"

# --- diagnostics ------------------------------------------------------------

# A console-disabled onefile shows no traceback when it dies, so unhandled
# exceptions are appended to this file under the temporary directory.
INSTALLER_LOG_NAME = "postal-gambit-installer.log"

# Used when the bundled VERSION file is missing or unreadable.
FALLBACK_VERSION = "0.0.0"
