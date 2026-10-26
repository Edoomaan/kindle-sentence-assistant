#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
state=/mnt/us/extensions/sentence-assistant/install-state
target=/var/local/sentence-assistant
stage=
published_header=no
committed=no
header=
step=preflight
message() {
    printf '%s\n' "$1" > "$state/status.txt"
    eips 0 2 "$1" || true
}
finish() {
    result=$?
    trap - EXIT HUP INT TERM
    if [ "$published_header" = yes ] && [ "$committed" != yes ]; then
        if [ -f "$stage/previous-header" ]; then
            mv "$stage/previous-header" "$header" || true
        else
            rm -f "$header"
        fi
    fi
    if [ -n "$stage" ]; then
        rm -f "$stage/input" "$stage/api.properties" "$stage/header" "$stage/provider" "$stage/previous-header" "$stage/test-result" "$stage/import-result"
        rmdir "$stage" || true
    fi
    if [ "$result" != 0 ]; then message "Settings failed: $step."; fi
    if [ -d "$target/.setup-lock" ] && [ "${private_lock:-no}" = yes ]; then rmdir "$target/.setup-lock"; fi
    rmdir "$state/lock" || true
    exit "$result"
}
trap finish EXIT
trap 'exit 1' HUP INT TERM
step=package-check
[ "$(id -u)" = 0 ]
[ -d "$state/lock" ] && [ ! -L "$state/lock" ]
(cd "$base" && sha256sum -c SHA256SUMS >/dev/null)
sha256sum -c "$base/runtime.sha256" >/dev/null
step=private-directory
framework_uid=$(id -u framework)
framework_gid=$(id -g framework)
umask 077
[ ! -L "$target" ]
if [ ! -e "$target" ]; then
    mkdir "$target"
    chown "$framework_uid:$framework_gid" "$target"
fi
[ -d "$target" ] && [ "$(stat -c %u "$target")" = "$framework_uid" ]
chmod 700 "$target"
step=private-lock
mkdir "$target/.setup-lock"
private_lock=yes
stage=$(mktemp -d "$target/.import.XXXXXX")
step=java-runtime
vm=
for executable in /usr/java/bin/cvm /usr/java/bin/java; do
    if [ -x "$executable" ]; then vm=$executable; break; fi
done
[ -n "$vm" ]
case "${1:-}" in
import)
    step=transfer-file
    incoming=$base/setup.properties
    [ -f "$incoming" ] && [ ! -L "$incoming" ] || exit 1
    [ "$(stat -c %s "$incoming")" -le 32768 ]
    step=copy-transfer
    cp "$incoming" "$stage/input"
    cmp -s "$incoming" "$stage/input"
    rm "$incoming"
    step=staging-permissions
    chown "$framework_uid:$framework_gid" "$stage" "$stage/input"
    chmod 700 "$stage"
    chmod 600 "$stage/input"
    step=java-import
    if ! "$vm" -cp "$base/registration.jar" org.kindlesentence.install.ImportSettings "$stage/input" "$stage" >"$stage/import-result" 2>&1; then
        diagnostic=$(sed -n '/^SETTINGS_FAILURE [a-z-]* [A-Za-z0-9.$]*$/p' "$stage/import-result" | head -n 1)
        if [ -n "$diagnostic" ]; then printf '%s\n' "$diagnostic"; fi
        exit 1
    fi
    step=publish-settings
    provider=$(cat "$stage/provider")
    case "$provider" in evren|openai|deepseek) ;; *) exit 1 ;; esac
    header=$target/$provider-header
    [ ! -L "$header" ] && [ ! -L "$target/api.properties" ]
    [ ! -e "$header" ] || [ -f "$header" ]
    [ ! -e "$target/api.properties" ] || [ -f "$target/api.properties" ]
    if [ -f "$stage/header" ]; then
        if [ -e "$header" ]; then
            cp "$header" "$stage/previous-header"
            chown "$framework_uid:$framework_gid" "$stage/previous-header"
            chmod 600 "$stage/previous-header"
        fi
        chown "$framework_uid:$framework_gid" "$stage/header"
        chmod 600 "$stage/header"
        mv "$stage/header" "$header"
        published_header=yes
    else
        step=saved-key-missing
        [ -s "$header" ] && [ "$(stat -c %u "$header")" = "$framework_uid" ]
        chmod 600 "$header"
    fi
    step=publish-config
    chown "$framework_uid:$framework_gid" "$stage/api.properties"
    chmod 600 "$stage/api.properties"
    mv "$stage/api.properties" "$target/api.properties"
    committed=yes
    sync
    message 'Settings imported. Transfer file removed. Run Test API.'
    ;;
test)
    message 'Testing API over Wi-Fi. Please wait...'
    if "$vm" -cp "$base/payload.jar:/opt/amazon/ebook/lib/json_simple-1.1.jar" org.kindlesentence.api.ApiTest > "$stage/test-result" 2>/dev/null; then
        message 'API test passed. Open a book and try Explain.'
    else
        message 'API test failed. Check provider, model, key and Wi-Fi.'
    fi
    ;;
*) exit 1 ;;
esac
