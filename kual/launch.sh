#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
state=/mnt/us/extensions/sentence-assistant/install-state
case "${1:-}" in install|backup|restore|status|import|test) ;; *) exit 1 ;; esac
[ ! -L /mnt/us/extensions/sentence-assistant ] && [ ! -L "$state" ] || exit 1
mkdir -p "$state"
if [ "$1" = status ]; then
    if [ -f "$state/status.txt" ]; then
        message=$(head -n 1 "$state/status.txt")
        eips 0 2 "$message"
    else
        eips 0 2 'Sentence Assistant: no installer run yet.'
    fi
    exit 0
fi
command -v nohup >/dev/null
command -v setsid >/dev/null
if ! mkdir "$state/lock" 2>/dev/null; then
    eips 0 2 'Installer busy or interrupted. Check install-state.'
    exit 1
fi
printf '%s\n' 'Starting installer...' > "$state/status.txt"
worker=worker.sh
case "$1" in import|test) worker=settings.sh ;; esac
nohup setsid sh "$base/$worker" "$1" </dev/null >>"$state/installer.log" 2>&1 &
