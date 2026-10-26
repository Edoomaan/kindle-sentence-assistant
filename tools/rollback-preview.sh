#!/bin/sh
set -eu

original_hash=a575b93abf58a812c4a88028ce74d86d73b6ed360cd88d55c53b5c73c6df71ce
candidate_hash=@CANDIDATE_HASH@
target=/opt/amazon/ebook/lib/ReaderSDK-impl.jar
backup=/mnt/us/extensions/sentence-assistant/recovery/ReaderSDK-impl.original.jar
staged=/opt/amazon/ebook/lib/ReaderSDK-impl.jar.sentence-restore

hash() { sha256sum "$1" | awk '{print $1}'; }
fail() { printf '%s\n' "$*" >&2; exit 1; }

[ "$(id -u)" = 0 ] || fail 'Root required on Kindle.'
[ "$(hash "$backup")" = "$original_hash" ] || fail 'Original backup hash mismatch.'
current=$(hash "$target")
case "$current" in
    "$original_hash") printf '%s\n' 'Original JAR already present; no change.'; exit 0 ;;
    "$candidate_hash") ;;
    *) fail 'Unknown system JAR; refusing replacement.' ;;
esac

if [ "${1:-}" != '--apply' ]; then
    printf '%s\n' 'Hashes match. Read-only check complete; nothing changed.'
    exit 0
fi
[ "$#" = 2 ] && [ "$2" = '--recovery-access-verified' ] || fail 'Recovery access must be verified before applying.'
status framework | grep -q 'stop/waiting' || fail 'Framework must already be stopped through verified SSH access.'
! pidof cvm >/dev/null 2>&1 || fail 'Java framework process still running.'
[ ! -e "$staged" ] || fail 'Staging file exists; inspect manually.'
awk '$2 == "/" && $4 ~ /(^|,)ro(,|$)/ {ok=1} END {exit !ok}' /proc/mounts || fail 'Root must initially be read-only.'

restore_readonly() {
    sync
    mount -o remount,ro / || { printf '%s\n' 'ERROR: root remount read-only failed.' >&2; exit 1; }
}
trap restore_readonly EXIT
trap 'exit 1' HUP INT TERM
mount -o remount,rw /
cp "$backup" "$staged"
chown 0:0 "$staged"
chmod 0644 "$staged"
[ "$(hash "$staged")" = "$original_hash" ] || fail 'Staged copy verification failed.'
sync
mv "$staged" "$target"
sync
[ "$(hash "$target")" = "$original_hash" ] || fail 'Restored target verification failed.'
printf '%s\n' 'Original restored. Framework remains stopped; no automatic restart or reboot.'
