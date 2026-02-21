#!/usr/bin/env bash
# =============================================================================
# Script: launch-tor-browser.sh
# Purpose: Locate and launch Tor Browser (Linux/macOS) with optional URL
# Usage:
#   ./launch-tor-browser.sh [http://example.onion/]
# =============================================================================

set -u          # Treat unset variables as error
set -e          # Exit on error (but we catch some manually)

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

# Add more paths if needed (order matters — first match wins)
TOR_PATHS=(
    "$HOME/tor-browser"
    "$HOME/tor-browser_en-US"
    "$HOME/Downloads/tor-browser"
    "$HOME/Downloads/tor-browser_en-US"
    "$HOME/Applications/tor-browser"
    "/opt/tor-browser"
    "/usr/local/share/tor-browser"
    "$HOME/.local/share/tor-browser"
    "/Applications/Tor Browser.app"
    # Flatpak common locations
    "$HOME/.var/app/org.torproject.torbrowser-launcher"
    "/var/lib/flatpak/app/org.torproject.torbrowser-launcher"
)

# ──────────────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────────────

die() {
    echo "Error: $*" >&2
    exit 1
}

log() {
    echo "[tor-launcher] $*" >&2
}

find_tor_executable() {
    local folder="$1"
    
    # Modern layout (most common since ~2022)
    if [[ -x "$folder/Browser/start-tor-browser" ]]; then
        echo "$folder/Browser/start-tor-browser"
        return 0
    fi
    
    # Older layout or custom installs
    if [[ -x "$folder/start-tor-browser" ]]; then
        echo "$folder/start-tor-browser"
        return 0
    fi
    
    # .desktop launcher (some distro packages)
    if [[ -f "$folder/start-tor-browser.desktop" ]]; then
        echo "gtk-launch"
        return 0
    fi
    
    return 1
}

# ──────────────────────────────────────────────────────────────────────────────
# Find Tor Browser installation
# ──────────────────────────────────────────────────────────────────────────────

tor_exec=""
tor_folder=""

for candidate in "${TOR_PATHS[@]}"; do
    if [[ -d "$candidate" ]]; then
        if tor_exec=$(find_tor_executable "$candidate"); then
            tor_folder="$candidate"
            break
        fi
    fi
done

# macOS .app special case
if [[ -z "$tor_exec" && -d "/Applications/Tor Browser.app" ]]; then
    open -a "/Applications/Tor Browser.app" --args "${1:-}" &
    log "Launched Tor Browser via macOS open command"
    exit 0
fi

if [[ -z "$tor_exec" ]]; then
    die "Tor Browser not found in any known location.

Please install it from https://www.torproject.org/download/
or add your installation path to the TOR_PATHS array in this script."
fi

# ──────────────────────────────────────────────────────────────────────────────
# Launch Tor Browser
# ──────────────────────────────────────────────────────────────────────────────

log "Found Tor Browser in: $tor_folder"
log "Executable: $tor_exec"

if [[ "$tor_exec" = "gtk-launch" ]]; then
    # .desktop file case
    gtk-launch start-tor-browser.desktop --working-directory="$tor_folder" "${1:-}" &
    log "Launched via gtk-launch (.desktop file)"
elif [[ -n "${1:-}" ]]; then
    # Launch with specific URL
    nohup "$tor_exec" --detach "$1" >/dev/null 2>&1 &
    log "Tor Browser launched with URL: $1"
else
    # No URL provided → just open Tor Browser
    nohup "$tor_exec" --detach >/dev/null 2>&1 &
    log "Tor Browser launched (no specific URL)"
fi

exit 0