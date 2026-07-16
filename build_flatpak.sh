#!/usr/bin/env bash
# Build the Postal Gambit Flatpak bundle (Linux).
#
# Self-generating: the manifest, launcher, .desktop and .metainfo.xml are
# written by this script (only the script is committed). Fully offline app
# build: Python wheels are pre-downloaded on the host, so the sandbox build
# needs no network and the app runs with no network permission at all (the
# user's own mail client is the transport).
#
# Usage:            ./build_flatpak.sh
# Install locally:  flatpak install --user postal-gambit.flatpak
# Run:              flatpak run uk.codecrafter.PostalGambit

set -euo pipefail

APP_ID="uk.codecrafter.PostalGambit"
APP_NAME="Postal Gambit"
APP_CMD="postal-gambit"
APP_SUMMARY="Correspondence chess over your own email"
RUNTIME="org.freedesktop.Platform"
SDK="org.freedesktop.Sdk"
RUNTIME_VERSION="25.08"
PYTHON_DIR="python3.13"
PYTHON_TAG="313"

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BUNDLE="${PROJECT_ROOT}/postal-gambit.flatpak"
BUILD_DIR="${PROJECT_ROOT}/.flatpak-build"
REPO_DIR="${PROJECT_ROOT}/.flatpak-repo"
WHEELS_DIR="${PROJECT_ROOT}/.flatpak-wheels"
PACKAGING_DIR="${PROJECT_ROOT}/packaging"
MANIFEST="${PROJECT_ROOT}/${APP_ID}.yml"
VERSION="$(tr -d '[:space:]' < "${PROJECT_ROOT}/VERSION")"
ICON_SIZES=(16 24 32 48 64 96 128 256 512)

section() {
    if command -v tput >/dev/null 2>&1; then
        printf '\n%s== %s ==%s\n' "$(tput bold)" "$1" "$(tput sgr0)"
    else
        printf '\n== %s ==\n' "$1"
    fi
}

install_if_missing() {
    local tool="$1" package="$2"
    if command -v "${tool}" >/dev/null 2>&1; then
        return
    fi
    section "Installing ${package}"
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update && sudo apt-get install -y "${package}"
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y "${package}"
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -S --noconfirm "${package}"
    elif command -v zypper >/dev/null 2>&1; then
        sudo zypper install -y "${package}"
    else
        echo "ERROR: no known package manager found; install ${package} manually." >&2
        exit 1
    fi
}

section "Checking tools"
install_if_missing flatpak flatpak
install_if_missing flatpak-builder flatpak-builder

section "Ensuring Flathub remote, runtime and SDK"
flatpak remote-add --if-not-exists --user flathub \
    https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user --noninteractive flathub \
    "${RUNTIME}//${RUNTIME_VERSION}" "${SDK}//${RUNTIME_VERSION}"

section "Pre-downloading Python wheels (offline sandbox build)"
rm -rf "${WHEELS_DIR}"
mkdir -p "${WHEELS_DIR}"
python3 -m pip download --only-binary :all: \
    --python-version "${PYTHON_TAG}" --implementation cp \
    --platform manylinux_2_34_x86_64 \
    -d "${WHEELS_DIR}" -r "${PROJECT_ROOT}/requirements.txt"

section "Writing packaging files"
rm -rf "${PACKAGING_DIR}"
mkdir -p "${PACKAGING_DIR}"

cat > "${PACKAGING_DIR}/${APP_CMD}" <<'LAUNCHER'
#!/bin/sh
export PYTHONPATH="/app/lib/python3.13/site-packages:/app/share/postal-gambit${PYTHONPATH:+:$PYTHONPATH}"
export QT_PLUGIN_PATH="/app/lib/python3.13/site-packages/PySide6/Qt/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="/app/lib/python3.13/site-packages/PySide6/Qt/plugins/platforms"
if [ -n "$WAYLAND_DISPLAY" ] && [ -z "$FORCE_X11" ]; then
    export QT_QPA_PLATFORM=wayland
else
    export QT_QPA_PLATFORM=xcb
fi
exec python3 /app/share/postal-gambit/main.py "$@"
LAUNCHER

cat > "${PACKAGING_DIR}/${APP_ID}.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=${APP_SUMMARY}
Exec=${APP_CMD} %u
Icon=${APP_ID}
Terminal=false
Categories=Game;BoardGame;Qt;
Keywords=chess;correspondence;email;pgn;
MimeType=x-scheme-handler/postalgambit;
DESKTOP

cat > "${PACKAGING_DIR}/${APP_ID}.metainfo.xml" <<METAINFO
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>${APP_ID}</id>
  <name>${APP_NAME}</name>
  <summary>${APP_SUMMARY}</summary>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0-only</project_license>
  <developer id="uk.codecrafter">
    <name>Oliver Ernster</name>
  </developer>
  <description>
    <p>
      Postal Gambit is a local-first desktop app for correspondence chess
      over ordinary email. It keeps your games, enforces the rules and turns
      each move into a ready-to-send email in whatever mail client you
      already use. It never touches the network itself.
    </p>
  </description>
  <launchable type="desktop-id">${APP_ID}.desktop</launchable>
  <categories>
    <category>Game</category>
  </categories>
  <releases>
    <release version="${VERSION}" date="$(date +%Y-%m-%d)"/>
  </releases>
  <content_rating type="oars-1.1"/>
</component>
METAINFO

section "Writing manifest"
ICON_INSTALLS=""
for size in "${ICON_SIZES[@]}"; do
    ICON_INSTALLS="${ICON_INSTALLS}
      - install -Dm644 assets/postal-gambit_icon_${size}.png /app/share/icons/hicolor/${size}x${size}/apps/${APP_ID}.png"
done

cat > "${MANIFEST}" <<MANIFEST
app-id: ${APP_ID}
runtime: ${RUNTIME}
runtime-version: "${RUNTIME_VERSION}"
sdk: ${SDK}
command: ${APP_CMD}
build-options:
  strip: true
  no-debuginfo: true
finish-args:
  - --share=ipc
  - --socket=fallback-x11
  - --socket=wayland
  - --device=dri
  - --filesystem=home
modules:
  - name: python-deps
    buildsystem: simple
    build-commands:
      - python3 -m ensurepip --upgrade
      - pip3 install --no-cache-dir --no-index --find-links wheels
        --prefix=/app -r requirements.txt
    sources:
      - type: dir
        path: .flatpak-wheels
        dest: wheels
      - type: file
        path: requirements.txt
  - name: postal-gambit
    buildsystem: simple
    build-commands:
      - install -d /app/share/postal-gambit
      - cp -r main.py postalgambit assets VERSION LICENSE /app/share/postal-gambit/
      - install -Dm755 packaging/${APP_CMD} /app/bin/${APP_CMD}
      - install -Dm644 packaging/${APP_ID}.desktop /app/share/applications/${APP_ID}.desktop
      - install -Dm644 packaging/${APP_ID}.metainfo.xml /app/share/metainfo/${APP_ID}.metainfo.xml${ICON_INSTALLS}
    sources:
      - type: dir
        path: .
MANIFEST

section "Building with flatpak-builder"
flatpak-builder --user --install-deps-from=flathub --force-clean \
    --repo="${REPO_DIR}" "${BUILD_DIR}" "${MANIFEST}"

section "Creating bundle"
flatpak build-bundle \
    --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo \
    "${REPO_DIR}" "${BUNDLE}" "${APP_ID}"

section "Done"
echo "Bundle: ${BUNDLE}"
echo "Install: flatpak install --user ${BUNDLE##*/}"
echo "Run:     flatpak run ${APP_ID}"
