# Project instructions

## Communication and mentoring

- Communicate with the user in Turkish unless requested otherwise. Explain important technical decisions, trade-offs and unfamiliar terms in the conversation.
- Keep source comments and CLI messages in English. Add comments only for maintenance or non-obvious behavior, not as teaching material.
- Use small, verifiable steps. Explain command purpose and whether it runs on the computer or Kindle before execution.
- Distinguish source findings, user reports, inferences and untested assumptions. Never claim a test passed unless it ran successfully.
- Prefer simple code, existing conventions and focused tests. Do not add unrelated changes or dependencies without explaining their purpose.

## Product contract

- Explain selected text inside the stock Kindle reader using the user-configured instruction. Do not replace the reader with KOReader.
- The editable default instruction in setup.html requests simple English, idiom explanations and no invented context. Users may change response language or request translation; do not append hidden explanation rules in runtime code.
- Send only the selected passage and the saved user instruction. Do not send surrounding paragraphs, book metadata or reading history. No conversation history is needed.
- The Kindle must work independently over Wi-Fi with the computer disconnected.
- Provider keys must remain separate. Keep fixed provider endpoints and reject unknown provider configuration rather than falling back to another account or service.

## Verified device and current status

- Kindle Basic 11th generation (2024), firmware `5.17.1.0.4`, build `4351960007`; jailbreak, KUAL and USBNetLite are installed.
- Root SSH access was verified while the framework was stopped. A full reboot/recovery test has not been performed.
- A separate plugin is registered through `reader_plugins.xml` inside `ReaderSDK-impl.jar`. Device entry path: `/mnt/us/extensions/sentence-assistant/explain-preview.jar`.
- The user confirmed that the corrected Evren/Qwen card works quickly, including over Wi-Fi without USB. Last confirmed plugin hash: `73928fe8fa1f21a777af5653316c1c7047af90aa9faf492ebe79be371598d272`.
- Selecting one word, lifting the finger and then extending the handles avoids permanent highlights on this device. Direct dragging can invoke Kindle's QUICK_HIGHLIGHT mode. Do not add automatic annotation deletion without proving that existing highlights and notes are preserved.
- The multi-provider revision was deployed through KUAL with working Evren requests. The user confirmed USB import after the staging-ownership fix and subsequent Explain availability. The latest single-press install with optional export is host-tested but not device-tested. Direct OpenAI/DeepSeek access has not been tested with live credentials.

## Build and validation

- Native compilation must use private copies of the device's `rt.jar` and `agui.jar` through `--runtime-dir`, in addition to the SDK JARs.
- Desktop Java 8 is not a sufficient compatibility check: the first API build failed because Kindle lacks `java.awt.event.HierarchyEvent`.
- Run the Python credential setup tests, core UI/lifecycle tests and native card/JSON/provider checks for relevant changes.
- Host tests cannot establish device touch behavior, E Ink rendering or loader success. Report these limits explicitly.

## Device changes and recovery

- The user authorized native plugin installation, API development and controlled framework restarts. Firmware updates, downgrades, factory resets and reboot experiments remain outside the agreed scope.
- Before system changes, preserve verified original backups, SHA-256 hashes, permissions and ownership on the computer, with recovery access independent of KUAL.
- Keep root read-only except during a specifically reviewed system replacement. Own-plugin updates in user storage do not require a writable root filesystem.
- Open KPP_LIBRARY before a framework restart. After startup, verify both process status and Library visibility. Explicit Library activation recovered a previous blank-screen incident.
- Preserve known-good plugin backups. Do not reuse historical fixed-hash installers for new artifacts.
- Do not assume compatibility with the Oasis reference project or similar firmware version numbers.

## Publication and credentials

- Never commit API keys, full serial numbers, books, annotation databases, firmware JARs, device dumps or personal logs.
- Keep device SDK/runtime copies and recovery artifacts outside the repository. Generated build output and Python caches are ignored.
- Keys live in `/var/local/sentence-assistant/{provider}-header`, with `700` directory and `600` file permissions, owned by the actual framework UID/GID. They are plaintext and accessible to root.
- Normal setup uses the offline form and a temporary USB settings file, imported and removed by KUAL. Keys must never be printed, passed in process arguments or accepted in chat. The optional developer CLI uses a hidden prompt and SSH stdin.
- The user requested SSH-free normal setup. Keep independent recovery access for supervised system experiments; do not claim guaranteed recovery without KUAL/SSH after power loss.
- The user will publish the repository. Preparing files does not authorize pushing or publishing on their behalf.

## Documentation

Keep the main README, provider setup and installation instructions current. Preserve source-backed research and recovery evidence, clearly labeled as historical when superseded. Consult `docs/installation.md` and `docs/api-integration.md` before changing device deployment or credentials.

## KUAL installer test release

- `tools/package-kual.py` builds a distributable ZIP containing only project code and hash manifests. It must not include private Amazon runtime/system JARs or credentials.
- The KUAL compatibility check and update path passed on the device, including standalone Java invocation and detached worker survival. Initial registration subsequently passed on-device and its XML-only change was verified independently. Automatic failure recovery remains unverified; do not call it ready for general use.
- Keep the installer directory separate from the installed plugin. Preserve automatic transaction backups. Offer computer backup export as a separate optional, recommended action; installation must not require export or computer-copy confirmation.
- Automatic recovery is an attempt, not a guarantee against power loss or filesystem failure. Keep independent SSH recovery during supervised testing.
