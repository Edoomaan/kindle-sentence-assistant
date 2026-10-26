# Kindle Sentence Assistant

Explain selected text inside Kindle's stock reader. The offline setup form starts with an editable instruction for simple English explanations, idioms and missing context. Change it to request another language, translation or a different style.

## Tested setup

| Component | Tested version |
| --- | --- |
| Device | Kindle Basic 11th generation (2024), jailbroken with KUAL |
| Firmware | `5.17.1.0.4` |
| Build | `4351960007` |
| Provider / model | Evren / `qwen3.8-flash-next` |

Explain works over Kindle Wi-Fi without a computer on this setup. Other devices and firmware versions have not been verified; automatic file/runtime checks remain in the installer.

I'm a Turkish developer, and I chose **Evren API** for development and testing. Evren is a preference, not a requirement: the app also has separate OpenAI and DeepSeek configurations, but direct requests to those providers have not been tested with live credentials.

The multi-provider plugin and earlier KUAL installer were deployed and tested on this device. The user confirmed USB settings import after the staging-ownership fix. The new single-press installation, separate backup export and fully editable instruction await device validation.

## Use

1. Press and hold one word, then lift your finger.
2. Extend the selection using its handles.
3. Choose **Explain** and wait for the explanation.
4. Choose **Close** to return to the book.

On the tested firmware, dragging directly across a sentence can create a permanent Kindle highlight. Selecting one word first and then extending the handles avoids that behavior. The assistant does not delete saved highlights.

## Privacy and API keys

Only the selected text and your saved instruction are sent to the selected provider. No surrounding paragraphs, book metadata or conversation history are included. Requests run in a background thread. Closing the card cancels the local request; stale results cannot replace a newer selection.

Keys live on the Kindle, outside USB user storage:

```text
/var/local/sentence-assistant/
  evren-header
  openai-header
  deepseek-header
  api.properties
```

The directory is mode `700`; files are mode `600`, owned by `framework`. Keys are plaintext and remain accessible to root. They are never passed as command-line arguments or written to the repository. Provider retention policies still apply to transmitted text.

## Install and configure without SSH

Normal installation and configuration use USB file transfer and KUAL. **USBNetLite and SSH are not required for this workflow.** A verified computer backup is optional but recommended; SSH remains an optional developer/recovery tool if KUAL cannot open.

1. Extract `sentence-assistant-kual-usb-setup.zip` and copy `extensions/sentence-assistant-installer` into the Kindle's `extensions` folder.
2. **Optional, recommended:** safely eject USB file transfer and select **Export backup (optional, recommended)** in KUAL. When status says **Backup exported**, reconnect and copy `extensions/sentence-assistant/install-state/recovery-export` to a private folder on your computer. Run `sha256sum -c SHA256SUMS` inside that copied folder to verify it. Do not put backups in Kindle's `documents` folder or publish them.
3. Safely eject USB file transfer, then select **Install / Update** once. Installation starts immediately after automatic checks and an internal transaction backup. Wait for Library to return. No second press or computer-backup confirmation is required.
4. On your computer, open the extracted `setup.html` next to `setup.js`. Choose the provider, enter its model ID and API key, and adjust explanation preferences. This page works offline and has no external scripts or network requests.
5. Click **Create setup.properties**. Copy that file into Kindle's `extensions/sentence-assistant-installer` folder, safely eject, then choose **Import settings from USB** in KUAL.
6. Import removes the Kindle transfer file and saves settings privately. Delete the downloaded computer copy as well: it contains the key in plain text.
7. Enable Kindle Wi-Fi and choose **Test API (uses provider quota)**. After success, open a book and use Explain. Setup is complete; do not press **Install / Update** again.

**Install / Update installs the plugin; Import settings from USB only saves API settings.** Import does not add the Explain menu. If you imported settings before installing, run Install / Update once; you do not need to import again. Changing API settings after installation requires no reinstall.

**Upgrading from earlier versions:** install the new plugin, then open the new setup form and import your complete instruction. An old instruction such as “Use at most three short sentences” now stands alone; no hidden explanation rules are appended. Missing instructions require re-import. Leave the API key blank to reuse its saved value.

The optional export is a snapshot of the current system JAR and existing plugin, not a log archive or a full-device backup. Copy it to the computer before installation if you want an independent recovery copy. Installation always retains its own on-device transaction backup for **Restore previous version**, even if you skip export. A computer copy is restored manually through a working recovery interface; it is not restored automatically.

**Observed on the tested Kindle:** the user reported three “Application failed” messages after starting installation, followed by a working Explain menu. The cause of these messages has not been verified. Allow up to two minutes for Library to return, then check **Show installer status** and test Explain in a book. The messages alone do not establish success or failure. If Library does not return or Explain does not work, keep `extensions/sentence-assistant/install-state/installer.log` for diagnosis rather than repeatedly pressing Install / Update.

Leave the key blank to keep an existing key for the selected provider. Repeat steps 4–7 to change providers, models or explanation preferences; no restart is needed for subsequent requests. Preferences are the complete system instruction: choose the language, style and detail. The plugin adds no hidden English-only or no-translation rules. Blank instructions are rejected.

USB import succeeded on the device after the staging-ownership fix; a separate on-device API-test confirmation remains pending. The installer and earlier Explain version were tested on the target device. Direct OpenAI/DeepSeek service access remains untested. API tests may incur charges; no free tier is assumed. See [API configuration](docs/api-integration.md) and [installation/recovery](docs/installation.md) for details.

## Build and verify

The device uses a reduced Java 8 runtime. A desktop Java 8 compilation alone is insufficient. Obtain private copies of the following files from your own compatible device; do not commit or redistribute them:

- `ReaderSDK.jar`, `ReaderSDK-impl.jar`, `Reader-plugin.jar`
- `ReaderContentSDK.jar`, `Reader-utils.jar`, `reader-commons.jar`, `kafui.jar`, `json_simple-1.1.jar`
- `/usr/java/lib/rt.jar` and `/usr/java/lib/agui.jar`, in a separate runtime directory

Development checks require Python 3.8+, Node.js 18+ (offline form tests), and a JDK supporting Java 8 cross-compilation. End users need none of these tools for the packaged USB/KUAL setup. Run on the computer:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/build.py --check-ui
python3 tools/build.py --check-native \
  --sdk-dir /path/to/private/device-jars \
  --runtime-dir /path/to/private/runtime
python3 tools/build.py \
  --sdk-dir /path/to/private/device-jars \
  --runtime-dir /path/to/private/runtime \
  --output build/explain-preview.jar
```

`--sdk-dir` can be repeated. Build output contains only this project's classes; firmware libraries are not bundled.

## Installation and recovery

This experimental plugin supports only the verified device/firmware. Initial installation adds one registration in the system JAR; subsequent matching-registration updates replace only our plugin. KUAL offers **Restore previous version**, and the worker attempts restoration after detected installation failures. Power-loss and automatic-failure recovery are not fully device-validated; the ability to recover every failure without SSH is not guaranteed.

See [installation and recovery](docs/installation.md) for backups, package building and optional developer SSH tools. Do not publish private firmware libraries or recovery archives.

## Project layout

- `src/`: reader card, request lifecycle, provider configuration and curl transport.
- `tests/`: UI, cancellation, JSON, provider isolation and credential rotation checks.
- `kual/`: offline settings form, KUAL menus, installation and settings workers.
- `installer/`: native registration and settings import helpers.
- `tools/`: build, packaging and optional developer SSH setup commands.
- `docs/`: installation/recovery, API configuration and a concise technical evidence summary.

## Research

- [Technical findings, sources and validation limits](docs/feasibility.md)
