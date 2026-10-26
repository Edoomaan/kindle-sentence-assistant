#!/bin/sh
set -eu
original_hash=@ORIGINAL@
candidate_hash=@CANDIDATE@
plugin_hash=@PLUGIN@
previous_hash=@PREVIOUS@
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
target=/opt/amazon/ebook/lib/ReaderSDK-impl.jar
dir=/mnt/us/extensions/sentence-assistant
plugin=$dir/explain-preview.jar
stage=$target.sentence-install
hash() { sha256sum "$1" | awk '{print $1}'; }
fail() { printf '%s\n' "$*" >&2; exit 1; }
regular() { [ -f "$1" ] && [ ! -L "$1" ] || fail "Not a regular file: $1"; }
readonly_root() { awk '$2 == "/" && $4 ~ /(^|,)ro(,|$)/ {ok=1} END {exit !ok}' /proc/mounts; }
[ "$(id -u)" = 0 ] || fail 'Root SSH required.'
for name in ReaderSDK-impl.original.jar ReaderSDK-impl.candidate.jar explain-preview.jar; do regular "$base/$name"; done
[ "$(hash "$base/ReaderSDK-impl.original.jar")" = "$original_hash" ] || fail 'Original hash mismatch.'
[ "$(hash "$base/ReaderSDK-impl.candidate.jar")" = "$candidate_hash" ] || fail 'Candidate hash mismatch.'
[ "$(hash "$base/explain-preview.jar")" = "$plugin_hash" ] || fail 'Plugin hash mismatch.'
regular "$target"
[ "$(stat -c '%u:%g:%a' "$target")" = '0:0:644' ] || fail 'Unexpected system JAR metadata.'
current=$(hash "$target")
case "$current" in "$original_hash"|"$candidate_hash") ;; *) fail 'Unsupported system JAR; nothing changed.' ;; esac
[ ! -L "$dir" ] || fail 'Plugin directory is a symlink.'
if [ "$previous_hash" = absent ]; then
    [ ! -e "$plugin" ] && [ ! -L "$plugin" ] || fail 'Existing plugin requires --previous-plugin when packaging.'
else
    regular "$base/previous-plugin.jar"
    regular "$plugin"
    [ "$(hash "$base/previous-plugin.jar")" = "$previous_hash" ] || fail 'Packaged previous plugin hash mismatch.'
    [ "$(hash "$plugin")" = "$previous_hash" ] || fail 'Installed plugin differs from computer backup.'
fi
readonly_root || fail 'Root must initially be read-only.'
[ ! -e "$stage" ] && [ ! -L "$stage" ] || fail 'System staging path already exists.'
[ ! -e "$dir/package-recovery" ] && [ ! -L "$dir/package-recovery" ] || fail 'Preserve and move the previous package-recovery directory first.'
[ ! -e "$plugin.next" ] && [ ! -L "$plugin.next" ] || fail 'Plugin staging path already exists.'
case "${1:---check}" in
    --check) [ "$#" -le 1 ] || fail 'Unexpected arguments.'; echo 'Read-only checks passed. No files changed.'; exit 0 ;;
    --apply) [ "$#" = 2 ] && [ "$2" = --recovery-access-verified ] || fail 'Verify independent SSH with framework stopped first.' ;;
    *) fail 'Usage: sh install.sh [--check | --apply --recovery-access-verified]' ;;
esac
status framework | grep -q 'stop/waiting' || fail 'Stop framework through SSH first.'
! pidof cvm >/dev/null 2>&1 || fail 'Java framework is still running.'
umask 077
mkdir -p "$dir"
mkdir "$dir/package-recovery"
cp "$target" "$dir/package-recovery/ReaderSDK-impl.before.jar"
[ "$(hash "$dir/package-recovery/ReaderSDK-impl.before.jar")" = "$current" ] || fail 'System backup verification failed.'
if [ "$previous_hash" != absent ]; then
    cp "$plugin" "$dir/package-recovery/explain-preview.before.jar"
    [ "$(hash "$dir/package-recovery/explain-preview.before.jar")" = "$previous_hash" ] || fail 'Plugin backup verification failed.'
fi
changed_root=0
cleanup() {
    sync
    if [ "$changed_root" = 1 ]; then
        mount -o remount,ro / || { echo 'ERROR: cannot restore read-only root.' >&2; exit 1; }
    fi
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
cp "$base/explain-preview.jar" "$plugin.next"
chmod 0644 "$plugin.next"
chown 0:0 "$plugin.next"
[ "$(hash "$plugin.next")" = "$plugin_hash" ] || fail 'Plugin staging verification failed.'
mv "$plugin.next" "$plugin"
if [ "$current" = "$original_hash" ]; then
    changed_root=1
    mount -o remount,rw /
    cp "$base/ReaderSDK-impl.candidate.jar" "$stage"
    chmod 0644 "$stage"
    chown 0:0 "$stage"
    [ "$(hash "$stage")" = "$candidate_hash" ] || fail 'System staging verification failed.'
    sync
    mv "$stage" "$target"
fi
[ "$(hash "$target")" = "$candidate_hash" ] || fail 'Installed registration verification failed.'
echo 'Installed. Framework remains stopped. Verify Library after starting framework.'
echo "Recovery files: $dir/package-recovery; computer originals remain in the private package."
