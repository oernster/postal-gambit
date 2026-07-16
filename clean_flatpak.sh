#!/usr/bin/env bash
# Remove every Flatpak artefact build_flatpak.sh created, and nothing else.
# The Windows (dist-installer/) and macOS (dist-macos/) outputs are separate
# build paths and are never touched here.
#
# Usage: ./clean_flatpak.sh

set -euo pipefail

APP_ID="uk.codecrafter.PostalGambit"
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BUNDLE="${PROJECT_ROOT}/postal-gambit.flatpak"
MANIFEST="${PROJECT_ROOT}/${APP_ID}.yml"

echo "Uninstalling ${APP_ID} (user scope)..."
if flatpak list --user 2>/dev/null | grep -q "${APP_ID}"; then
    flatpak uninstall --user -y "${APP_ID}"
else
    echo "  Not installed, skipping."
fi

echo "Removing Flatpak build artefacts..."
rm -f "${BUNDLE}" "${MANIFEST}"
rm -rf \
    "${PROJECT_ROOT}/.flatpak-build" \
    "${PROJECT_ROOT}/.flatpak-repo" \
    "${PROJECT_ROOT}/.flatpak-builder" \
    "${PROJECT_ROOT}/.flatpak-wheels" \
    "${PROJECT_ROOT}/packaging"

echo "Done."
