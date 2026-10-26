#!/bin/sh
set -eu
original_hash=@ORIGINAL@
candidate_hash=@CANDIDATE@
plugin_hash=@PLUGIN@
previous_hash=@PREVIOUS@
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
target=/opt/amazon/ebook/lib/ReaderSDK-impl.jar
dir=/mnt/us/extensions/sentence-assistant
stage=$target.sentence-rollback
hash() { sha256sum "$1" | awk '{print $1}'; }
fail() { echo "$*" >&2; exit 1; }
regular() { [ -f "$1" ] && [ ! -L "$1" ] || fail "Not a regular file: $1"; }
[ "$(id -u)" = 0 ] || fail 'Root required.'
[ ! -L "$dir" ] && [ ! -L "$dir/package-recovery" ] || fail 'Symlink recovery directory.'
regular "$dir/package-recovery/ReaderSDK-impl.before.jar"
before=$(hash "$dir/package-recovery/ReaderSDK-impl.before.jar")
case "$before" in "$original_hash"|"$candidate_hash") ;; *) fail 'Unknown backup.' ;; esac
regular "$target"
case "$(hash "$target")" in "$original_hash"|"$candidate_hash") ;; *) fail 'Unknown system JAR.' ;; esac
regular "$dir/explain-preview.jar"
case "$(hash "$dir/explain-preview.jar")" in "$plugin_hash"|"$previous_hash") ;; *) fail 'Unknown installed plugin.' ;; esac
if [ "$previous_hash" != absent ]; then
    regular "$base/previous-plugin.jar"
    [ "$(hash "$base/previous-plugin.jar")" = "$previous_hash" ] || fail 'Previous plugin hash mismatch.'
fi
[ ! -e "$stage" ] && [ ! -L "$stage" ] || fail 'Rollback staging path exists.'
[ ! -e "$dir/explain-preview.restore" ] && [ ! -L "$dir/explain-preview.restore" ] || fail 'Plugin staging path exists.'
awk '$2 == "/" && $4 ~ /(^|,)ro(,|$)/ {ok=1} END {exit !ok}' /proc/mounts || fail 'Root must be read-only.'
case "${1:---check}" in
    --check) [ "$#" -le 1 ] || fail 'Unexpected arguments.'; echo 'Rollback checks passed; nothing changed.'; exit 0 ;;
    --apply) [ "$#" = 2 ] && [ "$2" = --recovery-access-verified ] || fail 'Recovery verification required.' ;;
    *) fail 'Unknown argument.' ;;
esac
status framework | grep -q 'stop/waiting' || fail 'Framework must be stopped.'
! pidof cvm >/dev/null 2>&1 || fail 'Java framework still running.'
changed_root=0
cleanup() {
    sync
    if [ "$changed_root" = 1 ]; then mount -o remount,ro / || exit 1; fi
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
if [ "$(hash "$target")" != "$before" ]; then
    changed_root=1
    mount -o remount,rw /
    cp "$dir/package-recovery/ReaderSDK-impl.before.jar" "$stage"
    chown 0:0 "$stage"
    chmod 0644 "$stage"
    [ "$(hash "$stage")" = "$before" ] || fail 'Staged rollback hash mismatch.'
    sync
    mv "$stage" "$target"
fi
if [ "$previous_hash" != absent ]; then
    cp "$base/previous-plugin.jar" "$dir/explain-preview.restore"
    chmod 0644 "$dir/explain-preview.restore"
    chown 0:0 "$dir/explain-preview.restore"
    [ "$(hash "$dir/explain-preview.restore")" = "$previous_hash" ] || fail 'Plugin restore hash mismatch.'
    mv "$dir/explain-preview.restore" "$dir/explain-preview.jar"
fi
echo 'Previous registration and plugin restored; framework remains stopped.'
echo 'For an initial install, the now-unregistered plugin file is retained.'
