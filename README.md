# NuPhy Codex Sidelight

Let your keyboard lights follow Codex. A local React control panel that turns the NuPhy Air75 V3 sidelights into a status indicator for your coding agent.

[中文说明](README.zh-CN.md) · [MIT license](LICENSE)

![NuPhy Codex Sidelight — connection checks, live lights, and customizable state colors and effects](docs/images/preview.jpg)

## What it does

- **See the current state:** working, waiting for approval, turn ended, error, or idle.
- **Check the connection:** macOS, local Codex installation, keyboard detection, and a real USB lighting readback.
- **Try every state:** enter test mode, preview the physical lights, then return to automatic tracking.
- **Make it yours:** choose a color and native effect for each state; restore one state or all defaults.
- **Keep your preferences:** English and Chinese UI, language selection, colors, and effects persist across restarts.
- **Stay local:** no account, API key, hosted service, or firmware flashing required.

**Verified hardware:** NuPhy Air75 V3 **ANSI**, stock firmware, connected to a **Mac by USB in wired mode**. Both sidebars share one lighting zone. Other models, ISO layouts, wireless connections, Windows, and Linux are not supported by this release.

## Quick start

You need Node.js **24+**, Python **3.11+**, and a USB data cable. Local Codex with [Hooks support](https://learn.chatgpt.com/docs/hooks) is required for automatic tracking; you can test the keyboard before enabling the hooks.

```sh
git clone https://github.com/joe960913/nuphy-codex-sidelight.git
cd nuphy-codex-sidelight

python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci
npm run build
npm start
```

1. Connect the keyboard and switch it to wired mode. Close NuPhy IO configuration windows to avoid competing device connections.
2. Open **[127.0.0.1:8765](http://127.0.0.1:8765)** and click **Test connection**. A detected receiver alone does not count as a verified keyboard connection.
3. Enter test mode and try the states. The UI confirms a lighting change only after reading the configuration back from the keyboard.

### Enable automatic Codex tracking

In another terminal, from the same project directory:

```sh
.venv/bin/python bridge.py install
```

This merges seven event handlers into `~/.codex/hooks.json`, preserves unrelated hooks, and backs up an existing configuration under `runtime/`. Start `codex`, enter `/hooks`, then review and trust this project's commands. They should run this checkout's `.venv/bin/python` with `bridge.py hook`. Start a new local Codex turn to verify that events arrive.

Hook configuration and received events are shown separately in the panel. Trust is always controlled by the user; the app does not change Codex trust records. Keep the checkout at the installed path. If you move it, uninstall from the old location first, then install and review the hooks again from the new one.

The first hook event starts the light controller automatically. Once installed, automatic tracking does not require the browser or web server to stay open. With the default idle profile, the controller restores the captured lighting and exits after about 30 idle seconds. A custom idle effect keeps it running.

## States and effects

| State | Default lights | Meaning |
| --- | --- | --- |
| Working | Blue · Breathe | Codex is thinking or executing tools |
| Waiting | Orange · Breathe | Approval or a synchronous user reply is needed |
| Turn ended | Green · Steady, 15 seconds | A turn ended; this is not a guarantee of success |
| Error | Red · Breathe, 15 seconds | A local task ended with an error |
| Idle | Original keyboard effect | No active turn, or the user interrupted it |

Each state supports **Breathe, Steady, Flow, Neon, Rhythm**, or **Original keyboard effect**. Neon cycles its own colors, so it does not use a fixed color. “Wave” is a main-key backlight effect; the sidebar's moving effect is **Flow**. Effects run on the keyboard; the app does not stream animation frames.

Use the color picker or a six-digit HEX value, choose an effect, and click **Save** for that state. Settings can be saved while the keyboard is disconnected. A saved preference and a hardware-confirmed lighting change are separate indicators. Changes to the active state apply when the device is available; other profiles apply when their state becomes active.

**Reset** restores the app's default state profile. **Original keyboard effect** restores the sidelights captured before the controller took over, without factory-resetting the keyboard or changing its main-key backlight. Resetting all state profiles keeps your language preference.

Multiple local chats are combined with this priority: **Error → Waiting → Working → Turn ended → Idle**. Test mode temporarily overrides this result. Closing the testing page releases its lease within 20 seconds and resumes automatic tracking. Asynchronous user questions are not treated as persistent waiting, because there is no matching reply hook to clear that state reliably.

## Local data and recovery

The server listens only on `127.0.0.1`. The app has no cloud backend and does not upload keyboard or chat data. It retains only lifecycle metadata: session/turn identifiers, timestamps, event/tool names, and local transcript paths/read positions. It reads lifecycle records from connected local Codex transcripts to recover task endings that arrive without a `Stop` hook; it does not retain chat text, tool arguments, or tool responses.

Generated files live in **`runtime/`**, which is excluded from Git:

- `preferences.json` — saved language, colors, and effects. Keep it when migrating this checkout.
- `original-lighting.json` — recovery snapshot while the controller owns the lights. Keep it until restoration succeeds.
- Session state, hardware receipts, locks, and controller logs — local operational data.

An abrupt shutdown or unplugged keyboard may leave the last effect active. Reconnect by USB, remove the hooks, stop the web server, and wait for the controller to exit before manual recovery. If you configured a custom idle profile, reset Idle to **Original keyboard effect** first so the controller can exit.

```sh
# Remove only this checkout's hooks
.venv/bin/python bridge.py uninstall

# Restore the captured original sidelights once the controller has exited
.venv/bin/python nuphy.py restore
```

Do not delete the recovery snapshot before restoring. If settings are damaged, the UI reports the problem and lets you reset them instead of silently overwriting the file.

## Development

Keep `npm start` running for the local backend. In a second terminal, run `npm run dev` and open the Vite URL. Rebuild with `npm run build` to update the regular console.

```sh
npm test                             # Mocked protocol, lifecycle, settings, HTTP, and i18n tests
npm run build                        # Production React build
.venv/bin/python nuphy.py probe       # Read device details without changing lights
.venv/bin/python bridge.py status     # Inspect local lifecycle state
```

CI runs the tests and build on macOS without a connected keyboard. Tests cover protocol rejection, lighting recovery, concurrent test sessions, settings persistence, stale edits, local-only HTTP access, and hook installation. Hardware verification is separate: USB configuration readback and preserved main-key backlight were checked on an Air75 V3 ANSI, including all five native sidebar effects and restoration.

`src/` contains the React UI, `webapp.py` the loopback API, `bridge.py` the lifecycle controller, `preferences.py` shared settings validation, and `nuphy.py` the HID protocol.

## Known limits

- The verified USB identity is `19f5:1028`. The tested `19f5:2620` wireless receiver rejects lighting queries; Bluetooth and receiver control are not implemented.
- Stock firmware exposes both sidebars as one zone. Independent left/right states and per-LED progress are not available.
- Lighting writes are rate-limited to at least two seconds apart. Long-term storage endurance under frequent configuration writes has not been measured.
- Only local Codex sessions emitting the supported lifecycle events are tracked. Cloud-orchestrated Work chats are outside this integration. This version uses the default `~/.codex` location.
- A session with no terminal event expires after 24 hours. A green light reports a turn ending, not task correctness or passing tests.
- The on-screen keyboard is an illustration; hardware readback confirms configuration, not a visual inspection of the physical LEDs.

## Acknowledgments

- [OpenAI Hooks documentation](https://learn.chatgpt.com/docs/hooks) — lifecycle events and user-controlled trust.
- [kbvu protocol research](https://github.com/pda/kbvu/blob/main/docs/keyboard-protocol.md) and [N Agent Bridge protocol notes](https://github.com/bohu8264/N-Agent-Bridge/blob/main/docs/HID-PROTOCOL.md) — Air75 V3 protocol references.
- [cython-hidapi](https://github.com/trezor/cython-hidapi) — local HID communication.
- Native sidebar effect names and identifiers were cross-checked against NuPhy IO and verified by device readback.

Released under the [MIT license](LICENSE). An independent community project, not affiliated with NuPhy or OpenAI.
