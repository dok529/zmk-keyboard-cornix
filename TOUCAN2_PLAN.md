# Plan: Cornix-Keymap auf den beekeeb Toucan2 übertragen

Stand: 2026-10-17. Nur Konzept, noch nichts umgesetzt. Basis ist die
Cornix-Keymap inklusive Game-Layer (Layer 0–8, siehe
[`config/README.md`](config/README.md)).

## Quellen

- Produktseite: <https://beekeeb.com/introducing-toucan2/>
- Offizielles ZMK-Repo: <https://github.com/beekeeb/zmk-keyboard-toucan2>
  (Shield `toucan_left`/`toucan_right` auf `seeeduino_xiao_ble`, ZMK **v0.3**,
  Module `zmk-rgbled-widget`, `zmk_driver_azoteq` (Trackpad TPS43),
  `zmk-input-zoom`, Display-Shield `nice_view_gem`)
- Community-Ports als Referenz, z. B.
  <https://github.com/ShigglesAndGits/toucan2-zmk>

## Hardware-Vergleich

| | Cornix | Toucan2 |
|---|---|---|
| Tasten | 50 | **42** (3×6 pro Hälfte + 3 Daumentasten) |
| Drehregler | 2 (drehen + drücken) | keine |
| Extras | RGB-LEDs | **Trackpad** rechts, **Display** links, RGB-LED |
| Controller / ZMK | Cornix-Board, ZMK `main` (Zephyr 4.1) | Seeed XIAO BLE, ZMK **v0.3** |
| ZMK Studio | ja | ja (`studio-rpc-usb-uart`, nur USB) |

## Repo-Aufbau

- **Eigenes Repo**: Fork von `beekeeb/zmk-keyboard-toucan2`, nicht in dieses
  Cornix-Repo integrieren (ZMK v0.3 vs. `main` in einem Manifest mischen ist
  fehleranfällig).
- Keymap nach `config/toucan.keymap` portieren; beekeebs Shield-Dateien
  möglichst **unverändert** lassen (einfachere Upstream-Updates) und alles
  Nötige aus der Keymap heraus per Devicetree-Referenz überschreiben (siehe
  „Trackpad“).
- Aus diesem Repo mitnehmen und anpassen: `Makefile`,
  `scripts/docker-*.sh`, `scripts/build_targets.py`, Visualisierung
  (`gen_keymap_viz.py` liest dann die Toucan-`toucan.dtsi`-Koordinaten),
  Pages-Workflow, `config/README.md` als Doku-Vorlage.
- Keymap wird danach in zwei Repos gepflegt.

## Positions-Mapping Cornix → Toucan2

| Cornix | Toucan2 | Inhalt |
|---|---|---|
| 0–11 | 0–11 | obere Reihe, identisch |
| 12–23 | 12–23 | Home Row, identisch |
| 24–29 | 24–29 | untere Reihe links |
| 30, 31 | — | Drehregler-Klicks, **entfallen** |
| 32–37 | 30–35 | untere Reihe rechts |
| 38–40 | — | äußere Tasten unten links, **entfallen** |
| 41–43 | 36–38 | Daumen links |
| 44–46 | 39–41 | Daumen rechts |
| 47–49 | — | äußere Tasten unten rechts, **entfallen** |

Folgen:

- Combos: `cb_we` 2+3 und `cb_pg` 4+5 bleiben, `cb_mcomma` 33+34 → **31+32**.
- `KEYS_L`/`KEYS_R`/`KEYS_T` (hold-trigger-key-positions) neu aufstellen;
  `LH3`/`RH3`/38/39/`LP0`/47/48/`RP0` fallen raus. Eigenen Positions-Header
  statt `includes/cornix54.h` anlegen.
- Game-Layer: Shift 41 → **36**, Space 42 → **37**, Enter 23 bleibt.

## Was wegfällt und wohin es kommt

| Cornix | Belegung | Vorschlag Toucan2 |
|---|---|---|
| 31 (Regler rechts drücken) | Win/Mac umschalten (`&tog 1` / `&tog 0`) | **Adjust**, freie Taste oben links (z. B. Position 4 = Colemak P) mit `&tog 1` |
| 30 (Regler links drücken) | Win: `zm4` (Win+Alt+N, Mic Mute); Mac: Teams-Mute Cmd+Shift+M | **Adjust** Position 3 (Colemak F) `&zm4`, in **Adjust Mac** dieselbe Position `LG(LS(M))` |
| Regler drehen | Lautstärke, Pfeile, Bild auf/ab | Lautstärke liegt schon in Media/Umlaut, Pfeile und Bild auf/ab in Adjust; Scrollen übernimmt das Trackpad |
| 38–40 | Ctrl/Cmd/Alt (Mac: Cmd/Opt/Ctrl) | über Home-Row-Mods und Adjust-Home-Row vorhanden, kein Ersatz nötig |
| 47, 49 | Home/End (Mac: Cmd+←/→) | in Adjust bzw. Adjust Mac schon vorhanden |
| 48 | `LG(U)` (Mac: Ctrl+Cmd+Q, Bildschirm sperren) | `LG(U)` auf freie Taste in Media; Sperren liegt schon im Umlaut-Layer (Position 5) |

Game-Toggle (Adjust Mac, Position 5 = Colemak G) bleibt unverändert.

## Layer-Plan

ZMK erlaubt bis zu 32 Layer (`zmk_keymap_layers_state_t` = `uint32_t`).

| # | Layer | Hinweis |
|---|---|---|
| 0 | Win | |
| 1 | Mac | |
| 2 | Game | |
| 3 | Media | |
| 4 | Adjust | |
| 5 | Umlaut | |
| 6 | Num | |
| 7 | Sym | |
| 8 | Adjust Mac | `conditional_layers`: `if-layers = <1 4>` |
| 9 | **Mouse** (neu) | nur Daumentasten = Klicks, sonst `&trans`; muss **ganz oben** liegen, damit sie in jedem Modus gilt |
| 10, 11 | reserviert | freie Layer für ZMK Studio (`status = "reserved"`, wie bei beekeeb) |

Layer-Nummern einmal als Namen definieren (`#define L_WIN 0`, `L_MAC 1`, …,
`L_MOUSE 9`) und überall verwenden — in `&mo`/`&lt`/`&tog`,
`conditional_layers` und den Trackpad-Overrides.

## Trackpad

beekeeb verdrahtet in `boards/shields/toucan/toucan.dtsi` Layer-Nummern
fest; das passt nicht zu dieser Reihenfolge. Statt die Shield-Datei zu
ändern, in `config/toucan.keymap` überschreiben:

```dts
&is_touching_processor { bindings = <&mo L_MOUSE>; };   // Original: &mo 4
&trackpad_listener {
    scroller { layers = <L_NUM L_ADJUST>; };             // Original: <1 2>, Auswahl offen
};
```

- **Wischgesten** (`swipe_button_mapper`) und **Zoom** (`zip_zoom_mapper`)
  sind beim Bauen fest auf Mac oder Windows eingestellt (`TOUCAN_WIN_MODE`),
  nicht über den Win/Mac-Layer zur Laufzeit. Vorschlag: Mac-Standard lassen.
  Bei Bedarf per Override in der Keymap anpassen.
- Scroll-Richtung und -Empfindlichkeit: `tps43_trackpad` in
  `toucan_right.overlay` (`invert-scroll-y`, `scroll-sensitivity`).

## ZMK-v0.3-Kompatibilität (vor dem Port prüfen)

Die Cornix-Keymap nutzt: `require-prior-idle-ms`, `hold-trigger-on-release`,
`hold-trigger-key-positions`, `zmk,behavior-mod-morph`,
`zmk,behavior-macro-one-param` mit `&macro_param_1to1`,
`conditional_layers`, Combos mit `timeout-ms`/`layers`, `display-name`.
Alles sollte in v0.3 vorhanden sein, im Build verifizieren. Außerdem:

- `#include "zmk-helpers/helper.h"` in der Cornix-Keymap prüfen, ob es
  überhaupt gebraucht wird; sonst weglassen (nicht im Toucan-Manifest).
- Studio: beekeeb nutzt `&studio_unlock` mit Studio-Locking; Cornix hat
  `CONFIG_ZMK_STUDIO_LOCKING=n`. Entscheiden, welche Variante.
- Sensor-Bindings (`&inc_dec_kp`) komplett entfernen (keine Encoder).

## Offene Fragen

1. Auf welchen Layern soll das Trackpad **scrollen** statt die Maus zu
   bewegen?
2. Welche Daumentasten im Mouse-Layer welche Klicks (beekeeb: links
   Mitte/Links/Rechts, rechts Links/Rechts/Mitte)?
3. Wischgesten fest auf Mac lassen?
4. Plätze für Win/Mac-Toggle, Mic Mute und `LG(U)` wie oben vorgeschlagen?
5. Studio-Locking an oder aus?
