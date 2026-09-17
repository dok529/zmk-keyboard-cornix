# Cornix keymap notes

Maintenance notes for `cornix.keymap`, written for whoever (human or AI
agent) edits it next. `cornix.keymap` is the single keymap used by the
`cornix_left`, `cornix_right`, and `cornix_ph_left` boards — ZMK resolves it
via `ZMK_KEYBOARD_NAME` ("Cornix", set in
`boards/jzf/cornix/Kconfig.defconfig`) lowercased to `cornix`, which is why
one file covers all three boards without a `-DKEYMAP_FILE=` override.
`config/cornix.conf` is picked up the same way (all three boards get
`CONFIG_ZMK_STUDIO=y`, see below).

The keymap's letter layout is a fork of [miryoku.vil](../miryoku.vil) (a
Vial/QMK export) — see "Origin: porting from Vial" below before assuming any
oddity is a mistake; several are intentional carry-overs from that source.

## Physical layout & the position-ordering gotcha

The board is 50 keys (`LAYOUT_50`), defined in
[`boards/jzf/cornix/cornix-layouts.dtsi`](../boards/jzf/cornix/cornix-layouts.dtsi):
a `zmk,matrix-transform` (`default_transform`) assigns each raw matrix event
a **position** 0–49, and a `zmk,physical-layout` (`layout_50`) gives each
position's real x/y (used by the position-numbered comment header in
[`config/includes/cornix54.h`](includes/cornix54.h), which documents the
`LT0`..`RB5`/`LH0`..`RH3` naming used by `KEYS_L`/`KEYS_R`/`KEYS_T` below).

**The `bindings = < ... >` array in every layer must be written in strict
position order**: for each visual row, left-hand keys first (outer→inner,
i.e. pinky to index finger), then right-hand keys (inner→outer, i.e. index
finger to pinky). Concretely, reading positions 0–11 (top row) left to
right: outermost-left pinky key is position 0, innermost-left (next to the
gap) is position 5, innermost-right is position 6, outermost-right pinky is
position 11. The bottom row additionally has two "gap" keys (positions
30/31, an extra key next to the left pinky's row and one physically-lower-
but-electrically-home-row key on the right) sitting between the left and
right halves — see the 14-token bottom row in every layer.

**Why this matters**: `miryoku.vil`'s own per-row arrays store columns
consistently *outer→inner for both hands* (mirroring the physical matrix
column wiring, which is symmetric left/right). For the **left** hand this
happens to already match the position-order convention above — vial's array
can be copied straight in. For the **right** hand it's the *opposite*
direction and must be **reversed** before it matches position order. Missing
this reversal is exactly the bug that shipped once already: every
right-hand key looked plausible in isolation (it was some valid key from
the same row) but the whole right hand was mirrored front-to-back. If you
ever re-sync from `miryoku.vil` or a similar per-row-ordered source, reverse
each right-hand row segment before writing it into the `bindings` array.
Combos (which address raw position numbers directly, not array order) are
unaffected by this and don't need any such adjustment.

If something related surfaces again: verify by building and checking
`zephyr.dts`'s compiled `default_layer` — HID keycode `0x1C` at the position
you expect for `Y` is a Y, not a mirrored key. (macOS + a non-US layout can
also make a *correctly*-bound key print an unexpected character — see the
umlaut section below before assuming a position/mirroring bug.)

## OS-mode convention: Base = Windows, `win_layer` = macOS

`default_layer` (index 0, display-name "Base") assumes Windows. `win_layer`
(index 1, display-name "Windows" — a historical name inherited from before
this convention existed; don't take the ZMK layer name at face value) is
what you toggle to when working on a Mac, via `&tog 1` (bottom-right extra
key on Base) / `&tog 0` (same slot on `win_layer`, to go back). GUI/Alt/Ctrl
order on the thumb row is swapped between the two to match each OS's
physical modifier layout convention.

Most other layers (Media, Adjust, Num, Sym, ...) are shared and reached
identically regardless of which OS-mode layer is active — they don't
inherently "know" which OS you're in. `mix_layer` is the one exception:
it's reached *only* from `win_layer` (`&lt 4 LS(N6)`, not reachable from
Base at all) and is already Mac-flavored throughout (Cmd-based shortcuts,
the umlaut macros).

### Layer-specific OS overrides: `conditional_layers`

When a *shared* layer needs one or two keys to differ by OS-mode, don't
duplicate the whole layer. Use ZMK's `conditional_layers`
(`if-layers = <A B>; then-layer = <N>;`): whenever layers A and B are *both*
active, layer N is activated *on top* (verified against ZMK source: it's
additive, never a replacement, and higher-index layers win ties — see
`app/src/conditional_layer.c` / `app/src/keymap.c` in the ZMK checkout).
Give layer N `&trans` everywhere except the positions that actually need to
differ; those fall through to the shared layer underneath.

`mac_adjust_layer` (index 8) is the working example: `if-layers = <1 3>`
(win_layer + Adjust) `then-layer = <8>` overrides Adjust's Home/End with
`LG(LEFT)`/`LG(RIGHT)` (raw Home/End scroll the macOS viewport instead of
moving the cursor — Cmd+Left/Right is the macOS-idiomatic equivalent, and
this keymap already uses it elsewhere) and is `&trans` everywhere else. Use
the same pattern for any future "this key needs to differ when we're in
Mac-mode" request. A `then-layer` index must be higher than every index
listed in its `if-layers` (see the layer-index table below for what's free).

## Layer index reference

| # | ZMK node | Display name | Reached from | Notes |
|---|---|---|---|---|
| 0 | `default_layer` | Base | (default) | Windows-mode |
| 1 | `win_layer` | Windows | `&tog 1` (Base), `&tog 0` back | macOS-mode, despite the name |
| 2 | `media_layer` | Media | `&mo 2` (Base thumb) | |
| 3 | `adjust_layer` | Adjust | `&lt 3 BSPC` (Base & win_layer thumb) | BT select, clipboard, nav, caps word, bootloader |
| 4 | `mix_layer` | Mix | `&lt 4 LS(N6)` (win_layer thumb only) | Mac-only; umlaut macros live here |
| 5 | `num_layer` | Num | `&lt 5 LSHFT` (Base thumb) | |
| 6 | `num2_layer` | Num2 | **unreachable** — only `&tog 6` exists, which lives *on* this layer | dead weight carried over from the Vial port; free to repurpose if you need another layer index |
| 7 | `sym_layer` | Sym | `&lt 7 DELETE` (Base thumb) | |
| 8 | `mac_adjust_layer` | AdjMac | automatic, via `conditional_layers` (`if-layers = <1 3>`) | see above; never target this directly with `&mo`/`&tog`/`&lt` |

## Combos

Defined in `combos { }`, addressed by raw position number (not affected by
the ordering gotcha above): `cb_cv` (27+28 → Enter), `cb_we` (2+3 → Esc),
`cb_mcomma` (33+34 → Enter), all active on layers `<0 1>` (Base + win_layer)
only. To find a position number for a new combo, check the layer's
`bindings` array and count tokens left-to-right starting at 0 per the
position-ordering rules above, or cross-reference
`config/includes/cornix54.h`.

## Custom hold-tap behaviors (`behaviors { }`)

- `hm_l` / `hm_r` — positional home-row mods (urob's "timeless homerow
  mods" technique: `hold-trigger-key-positions` limits fast hold-resolution
  to opposite-hand + thumb keys, so same-hand rolls aren't misread as a
  hold). `hm_shift_l` / `hm_shift_r` are the same for Shift specifically.
- `hm` — same idea but non-positional (no `hold-trigger-key-positions`),
  used for thumb keys like `&hm LCTRL SPACE`.
- `lt` — thin wrapper matching ZMK's built-in `&lt` (layer-tap), kept as a
  local alias so `tapping-term-ms`/`quick-tap-ms` are explicit here rather
  than inherited from upstream defaults.
- **Timing**: `HM_PRIOR_IDLE` (`require-prior-idle-ms`, currently 150ms) is
  what makes normal fast typing resolve taps instantly — a tap shortly
  after another keypress is assumed to be a tap, not a hold. This matters
  far more than `HM_TAPPING_TERM` for perceived typing lag; if a "home-row
  mods feel slow" report comes in again, raise `HM_PRIOR_IDLE` first (urob's
  own formula: `require-prior-idle-ms >= 10500 / typing_wpm`), not the
  tapping term. A *shorter* tapping term does not reduce tap latency, it
  only increases false-hold misfires — don't reach for that lever.
- `gresc` — mod-morph: tap for Escape, tap-while-Shift/Gui-held for `` ` ``/`~`.

## Macros (`macros { }`) and the umlaut mechanism

`zm4` is a plain macro (Cmd+Option+N). `zmuml` is a **parameterized** macro
(`zmk,behavior-macro-one-param`) that sends `Option+I` (see below) then
whatever keycode parameter it's given; `zmae`/`zmoe`/`zmue` are mod-morphs
wrapping it — tap for lowercase (ä/ö/ü), tap-while-Shift for the capital
(Ä/Ö/Ü). The mod-morph *masks* the real Shift before invoking the "capital"
branch (ZMK default behavior — confirmed in `behavior_mod_morph.c`), so the
`Option+I` dead-key step always fires unshifted; Shift for the capital
letter is reapplied only to the final vowel tap via `LS(x)`, which is an
*implicit* modifier the masking doesn't touch.

**Why `Option+I` and not `Option+U`**: the user's macOS input source is
Colemak, and macOS's Colemak implementation moves the whole Option-key
table along with the remapped letters — the diaeresis dead key sits wherever
Colemak's "u" prints, which is the physical/HID `I` key, not `U`. If macOS
input source or layout ever changes, this mapping needs re-verifying, not
assumed.

`zmae`/`zmoe`/`zmue` cover ä/ö/ü (and their capitals); if another accented
letter is ever needed, add one more `zmuml`-wrapping mod-morph following the
same pattern rather than hand-rolling a new macro from scratch.

## RGB indicators (`cornix_indicator`)

Enabled via `shield: cornix_indicator` in `build.yaml` (on the left/right/
ph_left targets) plus the `zmk-rgbled-widget` module in `config/west.yml`
(was commented out by default). Battery/connection/layer colors are
configured in `boards/shields/cornix_indicator/cornix_indicator.conf`
(numeric color IDs: 1=red 2=green 3=yellow 4=blue 5=magenta 6=cyan 7=white,
see `zmk-rgbled-widget`'s `widget.h`). A blue flash means "BLE connected", a
green flash means "battery high" — both are routine, not errors; only a
yellow (advertising) or red (disconnected) flash indicates an actual BLE
reconnect event worth investigating.

## ZMK Studio

`config/cornix.conf` sets `CONFIG_ZMK_STUDIO=y` (+ locking disabled, to
match `cornix_dongle_adapter.conf`'s existing settings) for the direct-BLE
split build. No RPC-transport snippet is needed:
`CONFIG_ZMK_STUDIO_TRANSPORT_BLE` defaults to `y` whenever `CONFIG_ZMK_BLE`
is enabled, which it already is. Only `cornix_left` (the split-central role)
actually runs the RPC stack — connect Studio to whichever half is currently
paired to the host (i.e. the central), per ZMK's own gating in
`app/src/studio/Kconfig` (`select ZMK_STUDIO_RPC if !ZMK_SPLIT ||
ZMK_SPLIT_ROLE_CENTRAL`).

## Origin: porting from Vial

The letter/layer layout started as a 1:1 port of [`miryoku.vil`](../miryoku.vil)
(10 Vial layers reduced to 8; the last two were unreachable in the ported
subset and dropped, their only entry points `TG(8)`/`MO(9)` became `&none`).
QMK tap-dances were reduced to plain tap+hold (ZMK has no built-in
double-tap/double-hold equivalent) — see git history around the initial
port commit for the full tap-dance → tap/hold mapping if it's ever needed
again. `USER00`/`USER01`/`USER02`/`USER05`/`USER06` (custom QMK keycodes
with no recoverable definition in the `.vil` export) were best-effort
mapped to Bluetooth profile selection by position (they sit in the same
far-left column the existing BT_SEL pattern uses elsewhere) — **this is an
unverified guess**, not a confirmed mapping; flag it if the original QMK
`process_record_user()` source ever turns up.

## Visualizing the keymap

`make vis` (see [`../Makefile`](../Makefile)) regenerates
`keymap-viz.html` at the repo root: a standalone, interactive,
Vial-style view of the current keymap (one tab per layer, laid out
like the real board, click a key for its full binding and an
explanation). It's generated fresh from `config/cornix.keymap` and
`boards/jzf/cornix/cornix-layouts.dtsi` by
[`../scripts/gen_keymap_viz.py`](../scripts/gen_keymap_viz.py) (which
fills in [`../scripts/keymap-viz-template.html`](../scripts/keymap-viz-template.html))
— no Docker/Nix/network needed, just `python3`. Re-run it after editing
the keymap; the output file itself is gitignored (regenerate, don't
commit it).

## Local build chain

See the top-level [`../README.md`](../README.md) for user-facing build/flash
docs. Two build paths exist:

- **Docker** (`make init`, `make build`, `make build ARTIFACT=<name>`, see
  [`../Makefile`](../Makefile) and `../scripts/docker-*.sh`) — no local
  Zephyr/west/Nix install needed, matches the official CI image
  (`zmkfirmware/zmk-build-arm:stable`). `config/` is bind-mounted read-only
  straight from the repo (`-v "$REPO_ROOT/config:/ws/config:ro"`) into every
  container, so local keymap/config edits are always picked up — no sync
  step, no risk of building a stale copy. (This used to be a `cp -R` done
  once at init time, re-copied on every build as a workaround after a real
  "the fix isn't showing up" bug; the mount replaced both scripts' copy
  steps entirely once bind-mounting turned out to work fine here.)
- **Nix** (`nix develop`, `just init`, `just build <target>`, see
  `../Justfile`/`../flake.nix`) — the original toolchain; note
  `Justfile`'s `config := absolute_path('config2')` currently points at a
  nonexistent directory (should very likely be `config`), so `just build`
  is probably broken until that's fixed — verify before relying on it.

## Known gaps / TODOs

- `num2_layer` (index 6) is unreachable — either wire it up or repurpose the
  index.
- `USER00`/`USER01`/`USER02`/`USER05`/`USER06` → BT_SEL mapping is an
  unverified guess (see above).
- Mic-mute on macOS (distinct from system mute, which is unaffected) has no
  firmware-side solution yet — it's app-specific (Zoom/Teams/Meet each have
  their own shortcut) or needs a macOS-side Shortcuts/Hammerspoon automation
  bound to a spare key combo; nothing implemented here yet.
