#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
dir=/mnt/us/extensions/sentence-assistant
state=$dir/install-state
target=/opt/amazon/ebook/lib/ReaderSDK-impl.jar
plugin=$dir/explain-preview.jar
original=a575b93abf58a812c4a88028ce74d86d73b6ed360cd88d55c53b5c73c6df71ce
legacy=5787dad5a8d18b6ddfd71fb5ec2bddb29c6c411cbb6a7bf88a7db71b6d5459ea
system_stage=$target.sentence-kual
stopped=0
mutating=0
tx=
hash() { sha256sum "$1" | awk '{print $1}'; }
fail() { echo "$*" >&2; return 1; }
regular() { [ -f "$1" ] && [ ! -L "$1" ]; }
root_ro() { awk '$2 == "/" && $4 ~ /(^|,)ro(,|$)/ {ok=1} END {exit !ok}' /proc/mounts; }
message() {
    printf '%s\n' "$1" > "$state/status.txt"
    echo "$1"
    eips 0 2 "$1" || true
}
valid_hash() { [ "${#1}" = 64 ] && ! printf '%s' "$1" | grep -q '[^0-9a-f]'; }
known_system() {
    case "$1" in "$original"|"$legacy") return 0 ;; esac
    regular "$state/registered.sha256" || return 1
    expected=$(cat "$state/registered.sha256")
    valid_hash "$expected" && [ "$1" = "$expected" ]
}
stop_reader() {
    stopped=1
    if ! status framework | grep -q 'stop/waiting'; then stop framework || return 1; fi
    count=0
    while pidof cvm >/dev/null 2>&1; do
        count=$((count + 1)); [ "$count" -le 30 ] || return 1
        sleep 1
    done
    status framework | grep -q 'stop/waiting'
}
start_reader() {
    start framework || return 1
    count=0
    until status kppmainapp | grep -q 'start/running'; do
        count=$((count + 1)); [ "$count" -le 60 ] || return 1
        sleep 1
    done
    count=0
    while [ "$count" -lt 15 ]; do
        lipc-set-prop com.lab126.appmgrd start 'app://com.lab126.KPPMainApp?view=KPP_LIBRARY' || true
        if lipc-get-prop com.lab126.appmgrd activeApp | grep -q '^com.lab126.KPPMainApp$' &&
           DISPLAY=:0 xwininfo -root -tree | grep 'ID:com.lab126.KPPMainApp' | grep -q IsViewable; then
            sync
            root_ro || mount -o remount,ro / || return 1
            stopped=0
            return 0
        fi
        count=$((count + 1)); sleep 2
    done
    return 1
}
replace_system() {
    source_file=$1
    expected_hash=$2
    [ "$(hash "$target")" != "$expected_hash" ] || return 0
    [ ! -e "$system_stage" ] && [ ! -L "$system_stage" ] || return 1
    mount -o remount,rw / || return 1
    cp "$source_file" "$system_stage" || return 1
    chown 0:0 "$system_stage" && chmod 0644 "$system_stage" || return 1
    [ "$(hash "$system_stage")" = "$expected_hash" ] || return 1
    sync
    mv "$system_stage" "$target" || return 1
    sync
    mount -o remount,ro / || return 1
}
validate_transaction() {
    regular "$tx/system.before.jar" && regular "$tx/before.sha256" && regular "$tx/after.sha256" || return 1
    before=$(cat "$tx/before.sha256")
    after=$(cat "$tx/after.sha256")
    valid_hash "$before" && valid_hash "$after" || return 1
    known_system "$before" || return 1
    [ "$(hash "$tx/system.before.jar")" = "$before" ] || return 1
    current=$(hash "$target")
    [ "$current" = "$before" ] || [ "$current" = "$after" ] || return 1
    if [ -f "$tx/plugin.before.sha256" ]; then
        regular "$tx/plugin.before.jar" || return 1
        [ "$(hash "$tx/plugin.before.jar")" = "$(cat "$tx/plugin.before.sha256")" ] || return 1
    fi
    if [ -e "$plugin" ]; then
        regular "$plugin" || return 1
        installed=$(hash "$plugin")
        [ "$installed" = "$(cat "$tx/plugin.after.sha256")" ] ||
          { regular "$tx/plugin.before.sha256" && [ "$installed" = "$(cat "$tx/plugin.before.sha256")" ]; } || return 1
    fi
}
restore_files() {
    validate_transaction || return 1
    replace_system "$tx/system.before.jar" "$before" || return 1
    if regular "$tx/plugin.before.jar"; then
        cp "$tx/plugin.before.jar" "$tx/plugin.restore" || return 1
        [ "$(hash "$tx/plugin.restore")" = "$(cat "$tx/plugin.before.sha256")" ] || return 1
        chmod 0644 "$tx/plugin.restore" && chown 0:0 "$tx/plugin.restore" || return 1
        mv "$tx/plugin.restore" "$plugin" || return 1
    fi
    # Initial rollback leaves an unregistered plugin file in user storage.
    printf '%s\n' "$before" > "$state/registered.sha256"
    sync
}
finish() {
    result=$?
    trap - EXIT HUP INT TERM
    if [ "$result" != 0 ]; then
        message 'Installer failed. Attempting recovery; keep USB connected.'
        if [ "$mutating" = 1 ]; then
            if stop_reader && restore_files; then
                mutating=0
                message 'Previous files restored.'
            else
                message 'Recovery needs SSH. Preserve install-state and logs.'
                sync
                root_ro || mount -o remount,ro / || true
                rmdir "$state/lock" || true
                exit 1
            fi
        fi
        sync
        if [ "$stopped" = 1 ]; then root_ro || mount -o remount,ro / || true; fi
        if [ "$stopped" = 1 ]; then
            if start_reader; then message 'Install failed; previous reader restarted.'
            else message 'Reader recovery needs SSH. Preserve backups.'; fi
        fi
    fi
    rmdir "$state/lock" || true
    exit "$result"
}
trap finish EXIT
trap 'exit 1' HUP INT TERM
[ "$(id -u)" = 0 ] || fail 'Root required.'
[ -d "$state/lock" ] && [ ! -L "$state/lock" ] || fail 'Start through launch.sh.'
[ ! -L "$dir" ] && [ ! -L "$state" ] || fail 'Symlink installation directory.'
regular "$target" || fail 'System JAR missing or symlink.'
[ "$(stat -c '%u:%g:%a' "$target")" = '0:0:644' ] || fail 'Unexpected system metadata.'
root_ro || fail 'Root must initially be read-only.'
[ ! -e "$system_stage" ] && [ ! -L "$system_stage" ] || fail 'Staging file exists; inspect over SSH.'
for tool in sha256sum stat lipc-set-prop lipc-get-prop eips xwininfo pidof status start stop; do
    command -v "$tool" >/dev/null || fail "Missing tool: $tool"
done
(cd "$base" && sha256sum -c SHA256SUMS) || fail 'Package integrity check failed.'
sha256sum -c "$base/runtime.sha256" || fail 'Device Java runtime differs from build runtime.'
current=$(hash "$target")
if [ "$1" != restore ]; then known_system "$current" || fail 'Unsupported system JAR. No system changes made.'; fi
if [ -e "$plugin" ] || [ -L "$plugin" ]; then regular "$plugin" || fail 'Invalid plugin file.'; fi
[ "$(df -Pk "$dir" | awk 'END {print $4}')" -ge 32768 ] || fail 'At least 32 MiB user storage required.'
[ "$(df -Pk / | awk 'END {print $4}')" -ge 8192 ] || fail 'At least 8 MiB root filesystem space required.'
action=$1
case "$action" in
backup)
    export_dir=$state/recovery-export
    [ ! -L "$export_dir" ] || fail 'Backup export is a symlink.'
    if [ -e "$export_dir" ]; then
        [ -d "$export_dir" ] || fail 'Invalid backup export.'
        archive=$state/recovery-export-$(date +%s)-$$
        [ ! -e "$archive" ] && [ ! -L "$archive" ] || fail 'Backup archive already exists.'
        mv "$export_dir" "$archive"
    fi
    mkdir "$export_dir"
    cp "$target" "$export_dir/system.before.jar"
    [ "$(hash "$export_dir/system.before.jar")" = "$current" ] || fail 'Backup copy failed.'
    if [ -f "$plugin" ]; then
        cp "$plugin" "$export_dir/plugin.before.jar"
        [ "$(hash "$plugin")" = "$(hash "$export_dir/plugin.before.jar")" ] || fail 'Plugin backup failed.'
    fi
    stat -c '%u:%g:%a' "$target" > "$export_dir/system.metadata"
    (cd "$export_dir" && sha256sum *.jar > SHA256SUMS)
    sync
    message 'Backup exported. Copy recovery-export to your PC.' 
    ;;
install)
    tx=$state/transaction-$(date +%s)-$$
    mkdir "$tx"
    cp "$target" "$tx/system.before.jar"
    [ "$(hash "$tx/system.before.jar")" = "$current" ] || fail 'System backup failed.'
    stat -c '%u:%g:%a' "$target" > "$tx/system.metadata"
    printf '%s\n' "$current" > "$tx/before.sha256"
    if [ -f "$plugin" ]; then
        cp "$plugin" "$tx/plugin.before.jar"
        [ "$(hash "$tx/plugin.before.jar")" = "$(hash "$plugin")" ] || fail 'Plugin backup failed.'
        hash "$plugin" > "$tx/plugin.before.sha256"
    fi
    if [ "$current" = "$original" ]; then
        vm=
        for executable in /usr/java/bin/cvm /usr/java/bin/java; do
            if [ -x "$executable" ] && "$executable" -cp "$base/registration.jar" org.kindlesentence.install.Registration --probe | grep -q '^sentence-installer-ready$'; then
                vm=$executable; break
            fi
        done
        [ -n "$vm" ] || fail 'Standalone device Java invocation not supported.'
        "$vm" -cp "$base/registration.jar" org.kindlesentence.install.Registration "$tx/system.before.jar" "$tx/system.after.jar"
    else
        cp "$target" "$tx/system.after.jar"
    fi
    hash "$tx/system.after.jar" > "$tx/after.sha256"
    cp "$base/payload.jar" "$tx/plugin.after.jar"
    hash "$base/payload.jar" > "$tx/plugin.after.sha256"
    [ "$(hash "$tx/plugin.after.jar")" = "$(cat "$tx/plugin.after.sha256")" ] || fail 'Payload copy failed.'
    printf '%s\n' "${tx##*/}" > "$state/current.next"
    mv "$state/current.next" "$state/current"
    sync
    lipc-set-prop com.lab126.appmgrd start 'app://com.lab126.KPPMainApp?view=KPP_LIBRARY'
    sleep 3
    [ "$(lipc-get-prop com.lab126.appmgrd activeApp)" = com.lab126.KPPMainApp ] || fail 'Library did not activate.'
    stop_reader
    validate_transaction
    mutating=1
    chmod 0644 "$tx/plugin.after.jar"
    chown 0:0 "$tx/plugin.after.jar"
    mv "$tx/plugin.after.jar" "$plugin"
    replace_system "$tx/system.after.jar" "$(cat "$tx/after.sha256")"
    printf '%s\n' "$(cat "$tx/after.sha256")" > "$state/registered.sha256"
    sync
    start_reader
    mutating=0
    message 'Installed. Open a book and test Explain.'
    ;;
restore)
    name=$(cat "$state/current")
    case "$name" in transaction-*[!0-9-]*|'') fail 'Invalid transaction reference.' ;; transaction-*) ;; *) fail 'Invalid transaction reference.' ;; esac
    tx=$state/$name
    [ -d "$tx" ] && [ ! -L "$tx" ] || fail 'Transaction missing.'
    validate_transaction
    lipc-set-prop com.lab126.appmgrd start 'app://com.lab126.KPPMainApp?view=KPP_LIBRARY' || true
    sleep 3
    stop_reader
    mutating=1
    restore_files
    start_reader
    mutating=0
    message 'Previous version restored. Open a book to verify.'
    ;;
*) fail 'Unknown action.' ;;
esac
