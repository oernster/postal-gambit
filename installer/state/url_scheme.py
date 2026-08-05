"""The postalgambit: URI scheme registration.

An import link in an email opens a static page that rebuilds a ``postalgambit:``
URI, so the scheme has to resolve to the installed executable for a one-click
import to work at all. The registration is per user (under HKCU Classes) so no
administrator rights are needed, and it is removed on uninstall.

Which key is written is part of the injected RegistryKeys value, exactly as for
the Uninstall and Run registrations, so a test exercises the real behaviour
against a scratch key and never touches the user's own scheme. British spelling
is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from pathlib import Path

from installer.constants import (
    URL_CLASS_DESCRIPTION,
    URL_DEFAULT_ICON_SUBKEY,
    URL_OPEN_COMMAND_SUBKEY,
    URL_PROTOCOL_VALUE,
)
from installer.ops.paths import installed_exe
from installer.ops.payload import shortcut_icon_file
from installer.state.registry import (
    DEFAULT_KEYS,
    RegistryKeys,
    delete_tree,
    write_string,
)

# The default value of a key is written under the empty name.
_DEFAULT_VALUE = ""
# Icon references carry the index of the icon within the file.
_FIRST_ICON_INDEX = "0"


def scheme_entries(
    install_dir: Path,
    keys: RegistryKeys = DEFAULT_KEYS,
) -> tuple[tuple[str, str, str], ...]:
    """Return the (key, value name, value) triples the scheme is made of.

    The icon falls back to the executable itself, which carries the same icon
    in its resources, so a bundle without the loose .ico still shows one.
    """
    root = keys.url_class_key
    exe = installed_exe(install_dir)
    icon = shortcut_icon_file(install_dir) or exe
    return (
        (root, _DEFAULT_VALUE, URL_CLASS_DESCRIPTION),
        (root, URL_PROTOCOL_VALUE, _DEFAULT_VALUE),
        (
            rf"{root}\{URL_DEFAULT_ICON_SUBKEY}",
            _DEFAULT_VALUE,
            f'"{icon}",{_FIRST_ICON_INDEX}',
        ),
        (
            rf"{root}\{URL_OPEN_COMMAND_SUBKEY}",
            _DEFAULT_VALUE,
            f'"{exe}" "%1"',
        ),
    )


def register_url_scheme(
    install_dir: Path,
    keys: RegistryKeys = DEFAULT_KEYS,
) -> None:
    """Point the postalgambit: scheme at the installed executable."""
    for key, name, value in scheme_entries(install_dir, keys):
        write_string(key, name, value)


def delete_url_scheme(keys: RegistryKeys = DEFAULT_KEYS) -> None:
    """Remove the postalgambit: scheme and every key beneath it."""
    delete_tree(keys.url_class_key)
