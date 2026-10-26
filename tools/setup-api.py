#!/usr/bin/env python3
import argparse
import getpass
import html
from pathlib import Path
import json
import re
import shlex
import subprocess
import sys


DIRECTORY = "/var/local/sentence-assistant"
PROVIDERS = {
    "evren": ("https://evren-llmapi.ssyz.org.tr/v1/chat/completions", "X-API-Key: "),
    "openai": ("https://api.openai.com/v1/chat/completions", "Authorization: Bearer "),
    "deepseek": ("https://api.deepseek.com/chat/completions", "Authorization: Bearer "),
}
def default_instruction():
    form = (Path(__file__).resolve().parents[1] / "kual/setup.html").read_text()
    return html.unescape(re.search(r'<textarea\b[^>]*id="instruction"[^>]*>(.*?)</textarea>', form, re.S).group(1)).strip()


WRITE_FILE = r"""
set -eu
target=/var/local/sentence-assistant
framework_uid=$(id -u framework)
framework_gid=$(id -g framework)
umask 077
test ! -L "$target"
if [ ! -e "$target" ]; then
    mkdir "$target"
    chown "$framework_uid:$framework_gid" "$target"
    chmod 700 "$target"
fi
test -d "$target"
test "$(stat -c %u "$target")" = "$framework_uid"
test "$(stat -c %a "$target")" = 700
mkdir "$target/.setup-lock" || { echo 'Another setup is active.' >&2; exit 1; }
staging=
trap 'test -z "$staging" || rm -f "$staging"; rmdir "$target/.setup-lock"' EXIT
trap 'exit 1' HUP INT TERM
destination="$target/$filename"
test ! -L "$destination"
if [ -e "$destination" ]; then
    test -f "$destination"
    test "$replace" = yes || { echo 'Key exists; use --replace to rotate it.' >&2; exit 1; }
fi
if [ -n "$required_header" ]; then
    test ! -L "$target/$required_header"
    test -f "$target/$required_header"
    test "$(stat -c %u "$target/$required_header")" = "$framework_uid"
    test "$(stat -c %a "$target/$required_header")" = 600
fi
staging=$(mktemp "$target/.setup.XXXXXX")
cat > "$staging"
test -s "$staging"
chown "$framework_uid:$framework_gid" "$staging"
chmod 600 "$staging"
mv -f "$staging" "$destination"
echo 'Saved on Kindle (directory 700, file 600).'
"""


def validate_model(model):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", model):
        raise ValueError("Invalid model ID.")
    return model


def header_bytes(provider, key):
    if not key or any(ord(char) <= 32 or ord(char) >= 127 for char in key):
        raise ValueError("The key must contain printable ASCII without whitespace.")
    return (PROVIDERS[provider][1] + key + "\n").encode("ascii")


def write_command(provider, activate=False, replace=False):
    if provider not in PROVIDERS:
        raise ValueError("Unknown provider.")
    filename = "api.properties" if activate else provider + "-header"
    required = provider + "-header" if activate else ""
    return ("filename=" + shlex.quote(filename) + "\nreplace="
            + ("yes" if replace or activate else "no")
            + "\nrequired_header=" + shlex.quote(required) + "\n" + WRITE_FILE)


def request_body(provider, model):
    request = {
        "model": validate_model(model),
        "messages": [
            {"role": "system", "content": default_instruction()},
            {"role": "user", "content": "It is raining cats and dogs."},
        ],
        "stream": False,
    }
    if provider == "openai":
        request.update(max_completion_tokens=1024, store=False)
    else:
        request["max_tokens"] = 1024
        if provider == "evren":
            request["reasoning_effort"] = "low"
        else:
            request["thinking"] = {"type": "disabled"}
    return request


def test_command(provider):
    return shlex.join([
        "/usr/bin/curl", "--silent", "--show-error", "--fail-with-body",
        "--connect-timeout", "10", "--max-time", "45", "--max-filesize", "65536",
        "--proto", "=https", "-H", "@" + DIRECTORY + "/" + provider + "-header",
        "-H", "Content-Type: application/json", "--data-binary", "@-",
        "--write-out", "%{stderr}HTTP=%{http_code} DNS=%{time_namelookup}s "
        "TLS=%{time_appconnect}s First-byte=%{time_starttransfer}s Total=%{time_total}s\n",
        PROVIDERS[provider][0],
    ])


def main():
    parser = argparse.ArgumentParser(description="Manage separate provider keys and settings on Kindle.")
    parser.add_argument("--host", default="192.168.15.244")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("key", "test", "use"):
        command = commands.add_parser(name)
        command.add_argument("--provider", choices=PROVIDERS, required=True)
        if name == "key":
            command.add_argument("--replace", action="store_true")
        else:
            command.add_argument("--model", required=True, type=validate_model)
    args = parser.parse_args()
    ssh = ["ssh", "-F", "/dev/null", "-T", "-o", "ConnectTimeout=8",
           "-o", "NumberOfPasswordPrompts=1", "-l", "root", "--", args.host]
    if args.command == "key":
        if not sys.stdin.isatty():
            raise ValueError("Run key setup in an interactive terminal; keys are never read from arguments.")
        key = getpass.getpass(args.provider + " API key (hidden): ")
        payload = header_bytes(args.provider, key)
        del key
        subprocess.run(ssh + [write_command(args.provider, replace=args.replace)], input=payload, check=True)
    elif args.command == "use":
        instruction = json.dumps(default_instruction(), ensure_ascii=True)[1:-1]
        settings = "provider=" + args.provider + "\nmodel=" + args.model + "\ninstruction=" + instruction + "\n"
        subprocess.run(ssh + [write_command(args.provider, activate=True)], input=settings.encode("ascii"), check=True)
        print("Selected " + args.provider + "/" + args.model + ". Applies to the next request in the multi-provider plugin.")
    else:
        result = subprocess.run(ssh + [test_command(args.provider)],
                                input=json.dumps(request_body(args.provider, args.model)).encode(),
                                stdout=subprocess.PIPE)
        if result.returncode:
            raise RuntimeError("API test failed. Check the HTTP/timing output; saved settings were not changed.")
        choice = json.loads(result.stdout)["choices"][0]
        content = choice["message"].get("content")
        if choice.get("finish_reason") != "stop" or not isinstance(content, str) or not content.strip():
            raise RuntimeError("No complete explanation returned.")
        print("Model:", args.model)
        print("Explanation:", content.strip())


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print("SSH operation failed (exit %s)." % error.returncode, file=sys.stderr)
        sys.exit(1)
    except (ValueError, KeyError, IndexError, TypeError, RuntimeError, OSError):
        print("Setup failed. Check arguments, file permissions and connection status. No credentials are printed.", file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        sys.exit(130)
