# Installation and recovery

The compatibility check and update path have now run successfully on the target Kindle; the user confirmed Explain still works. Initial registration has also completed on the device and its XML-only change was independently verified. Automatic failure recovery still requires supervised device testing. Do not treat this as a public stable release. See [verified evidence and limitations](feasibility.md#validation-and-recovery-evidence).

Supported target: the project's Kindle Basic 11th generation (2024), firmware `5.17.1.0.4`, build `4351960007`. The installer checks the original or previously verified registration JAR hashes and the exact Java runtime hashes used to build the helper. Similar firmware names do not imply compatibility.

The single-press install and separate optional export flow await on-device validation. The separate compatibility button has been removed, but the underlying checks remain.

## User workflow

Prerequisites: jailbreak, working KUAL, sufficient battery, at least 32 MiB free user storage and 8 MiB free root storage. Normal installation uses USB file transfer and KUAL; USBNetLite/SSH is not required. A verified computer backup is optional but recommended. SSH is an optional independent recovery path if KUAL fails; see [SSH recovery access](#ssh-recovery-access). Do not reboot, start file transfer or run another installer while installation is active. Automatic recovery cannot cover all power-loss or filesystem failures.

1. Extract `sentence-assistant-kual-usb-setup.zip` on the computer. Before connecting the Kindle, open `extensions/sentence-assistant-installer/setup.html`, fill in the provider settings and explanation instruction, and download `setup.properties`.
2. Place `setup.properties` next to `setup.html` in the extracted installer folder. Copy that whole `sentence-assistant-installer` folder into the Kindle's `extensions` folder, then safely eject and disconnect. Do not replace the running `sentence-assistant` directory.
3. **Optional, recommended:** select **Export backup (optional, recommended)** before installation. Wait for **Backup exported**, reconnect and copy `extensions/sentence-assistant/install-state/recovery-export` to a private computer folder. Run `sha256sum -c SHA256SUMS` there; all results should be OK. Safely eject again. Only this optional computer-backup step needs another USB connection.
4. Select **Install / Update** once. No export or computer-copy confirmation is required. Automatic checks and a verified on-device transaction backup precede replacement. KUAL closes and the reader framework restarts; allow up to two minutes for Library to return.
5. Reopen KUAL and select **Import settings from USB**. The transfer file is already present. Wait for **Settings imported**, then enable Wi-Fi and run **Test API (uses provider quota)**. Existing users who are keeping their saved settings can omit the form/import steps.
6. Open a book and test Explain, closing the card, another selection, and Wi-Fi operation without USB. Delete every computer copy of `setup.properties` after import, including the one inside the extracted installer folder.

The payload stays separate from the installed plugin until validation succeeds. Installation preserves API keys and provider settings; import separately applies the prepared configuration. See [provider setup](api-integration.md) for details. The pre-transfer workflow is supported by the existing scripts; this revised sequence still needs an end-to-end device check.

For another update, select **Install / Update** once. You may first export a new computer backup using the separate button. Export preserves an earlier export as `recovery-export-<timestamp>-<pid>`; installation does not consume or depend on exports. Every installation creates a fresh transaction backup from the currently installed files. Do not delete transaction backups until the new version is tested. Replacing the installer folder does not overwrite the installed plugin or its backups.

Computer exports do not restore themselves. If KUAL cannot open, manual restoration requires a working independent recovery interface such as SSH. Keeping only an on-device transaction backup provides no independent copy if that storage becomes unavailable.

## Recovery and status

**Restore previous version** restores the latest installation transaction, then restarts the framework and opens the Library. If the installation fails after replacing files, the worker attempts the same restoration automatically. It validates hashes before restoration and refuses unknown files.

After rolling back an initial installation, the plugin file is retained but its system registration is removed. Credentials are never removed or revoked. This is a one-transaction rollback, not an uninstall or firmware recovery tool.

If KUAL is unavailable and you have an independently working SSH connection, it can be used for recovery. Without KUAL or another working recovery interface, this package cannot guarantee remote recovery. The same action can be started on the Kindle:

```sh
sh /mnt/us/extensions/sentence-assistant-installer/launch.sh restore
```

Read these files for status and diagnostic details:

```text
/mnt/us/extensions/sentence-assistant/install-state/status.txt
/mnt/us/extensions/sentence-assistant/install-state/installer.log
/mnt/us/extensions/sentence-assistant/install-state/transaction-*/
```

Keep these private. They contain backups and operational details, not API credentials or book text. A stale `lock` after power loss or forced termination blocks a second launch. Do not blindly remove it: confirm no worker is running and inspect transaction/system hashes through SSH first. An interrupted system staging file also requires inspection.

Automatic recovery handles detected command failures; it does not guarantee recovery from power loss, filesystem damage, or a process forcibly killed before its cleanup handler runs. Library visibility checks do not establish that the Explain plugin loaded correctly. If the Library fails to appear, retain SSH and use the Library recovery procedure below rather than repeatedly restarting.

## Build a distributable ZIP

On the computer, first build and verify the plugin using the README's device-runtime build commands, then:

```bash
python3 tools/package-kual.py \
  --plugin build/explain-preview.jar \
  --runtime-dir /path/to/private/runtime \
  --output build/sentence-assistant-kual-usb-setup.zip
```

The output path must not already exist. The ZIP includes only this project's menu, shell scripts, plugin, registration helper and hash manifests. It includes **no Amazon JARs, API keys or device dumps**. Unlike the private SSH package, this ZIP is intended to be distributable after device validation. Runtime hashes identify the required libraries without distributing their contents.

The helper compiles against private Kindle runtime copies. On an initial installation it verifies the original system JAR hash, adds one `reader_plugins.xml` registration, and verifies that every other uncompressed entry is unchanged. ZIP compression and archive metadata may differ. It runs before stopping the framework, since framework shutdown kills `cvm` processes.

`launch.sh` uses `nohup setsid` with redirected input/output to detach the shell worker from KUAL. The worker validates the payload, exports backups, opens the Library, stops the framework, waits for Java to exit, stages replacements, and restores root read-only. A plugin-only update does not modify the system JAR. After startup it checks the active Library app and visible window; the user must still verify the actual screen and card behavior.

## SSH recovery access

This is an optional developer/recovery procedure, not part of normal setup. For supervised system-change experiments, verify a new root SSH connection while framework is stopped. Keep the USB cable connected and USBNetLite enabled during installation. USB networking and USB file transfer are different modes; Kindle may disappear from the file manager when USB networking is enabled.

On the **Kindle SSH shell**, open the Library and verify the active app is `com.lab126.KPPMainApp` before stopping framework:

```sh
lipc-set-prop com.lab126.appmgrd start 'app://com.lab126.KPPMainApp?view=KPP_LIBRARY'
lipc-get-prop com.lab126.appmgrd activeApp
stop framework
status framework
pidof cvm
```

Wait for `stop/waiting` and no `cvm` process. On the **computer**, open a second connection:

```bash
ssh -F /dev/null root@192.168.15.244 'id; status framework'
```

If it succeeds as root, restart from the **Kindle shell** with `start framework`. Wait for `status kppmainapp` to show `start/running`, then open the Library using the command above. Check the actual screen. During previous recovery, framework was running but the screen stayed blank until Library activation. This recovery observation is not a guarantee for every failure.

A full reboot/bootloop recovery test has not been performed. Do not assume that a KUAL Restore button alone provides independent recovery.

## Removing native registration

The original system JAR must match:

```text
a575b93abf58a812c4a88028ce74d86d73b6ed360cd88d55c53b5c73c6df71ce
```

Recorded metadata: `root:root`, mode `0644`. Keep a verified computer copy before any system replacement. The private SSH package described below includes a rollback script; use it only if its expected hashes match the installed files. The `tools/rollback-preview.sh` template requires candidate-hash substitution and is not directly runnable. Restoring an unknown system JAR or using an old fixed-hash installer is not supported.

For manual restoration, first open Library, stop framework, verify independent SSH, and wait for `cvm` to exit. Stage the verified original in the system JAR's directory, preserve `0:0:644`, verify the staged hash, then rename it into place. Keep root writable only for that replacement and return it to read-only before restarting framework. Verify Library visibility and reading afterward. This procedure was exercised on the target device; details and hashes are in the [evidence summary](feasibility.md#validation-and-recovery-evidence).

## Alternative private SSH package

Status: package creation and shell syntax tested on the computer; installer/rollback execution on Kindle is **not yet tested**. This developer-oriented alternative leaves framework stop/start explicit so recovery SSH can be verified independently. Do not run multiple installation or rollback sessions simultaneously.

On the **computer**, build the plugin as described in the README, then prepare a private package:

```bash
python3 tools/package-installer.py \
  --original /path/to/private/ReaderSDK-impl.jar \
  --plugin build/explain-preview.jar \
  --previous-plugin /path/to/private/current-plugin.jar \
  --output /path/to/private/new-install-package
```

`--original` must be the verified unmodified system JAR. For an update, first copy the installed plugin to the computer using SSH output redirection (the Kindle does not need `scp`):

```bash
ssh -F /dev/null root@192.168.15.244 \
  'cat /mnt/us/extensions/sentence-assistant/explain-preview.jar' \
  > /path/to/private/current-plugin.jar
```

Check that SSH succeeded and compare `sha256sum` on both copies before packaging. For an initial installation with no existing plugin, omit `--previous-plugin`. The installer rejects existing plugins unless they match the packaged computer backup.

The resulting directory and adjacent `.tar.gz` contain Amazon firmware copies. **Keep both private; do not upload them to GitHub or releases.** The generator refuses output inside this repository. API keys are not included.

Transfer from the **computer** to a new directory on Kindle:

```bash
ssh -F /dev/null root@192.168.15.244 \
  'mkdir /mnt/us/sentence-install-session && tar -xzf - -C /mnt/us/sentence-install-session' \
  < /path/to/private/new-install-package.tar.gz
```

In a **Kindle root SSH session**, run `sh install.sh --check` from the extracted package directory. Follow the SSH recovery verification above, then run `sh install.sh --apply --recovery-access-verified` with framework stopped. Start framework and verify Library afterward.

The package leaves framework stopped on completion. Its `rollback.sh --check` and `rollback.sh --apply --recovery-access-verified` commands restore the pre-install system/plugin files under the same stopped-framework requirements. It stores a device backup in `/mnt/us/extensions/sentence-assistant/package-recovery`; archive and move an earlier backup before another installation. Do not discard staging files or bypass hash checks after an error. Credentials are untouched.
