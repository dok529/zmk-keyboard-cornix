#!/usr/bin/env python3
"""Generate a standalone, interactive HTML visualization of the current
config/cornix.keymap -- one tab per layer, physically laid out like the
real board, click a key for its full ZMK binding.

Usage:
    python3 scripts/gen_keymap_viz.py [output.html]

Reads config/cornix.keymap and boards/jzf/cornix/cornix-layouts.dtsi (no
other tools/dependencies needed), fills scripts/keymap-viz-template.html
with the extracted data, and writes a single self-contained HTML file
(default: keymap-viz.html at the repo root) you can open directly in a
browser -- no server, no build step.

Re-run this after editing the keymap to refresh the view.
"""
import re
import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KEYMAP = REPO_ROOT / "config" / "cornix.keymap"
LAYOUTS_DTSI = REPO_ROOT / "boards" / "jzf" / "cornix" / "cornix-layouts.dtsi"
TEMPLATE = Path(__file__).resolve().parent / "keymap-viz-template.html"

# --- keycode -> short display label -----------------------------------
KEY = {
    'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D', 'E': 'E', 'F': 'F', 'G': 'G', 'H': 'H',
    'I': 'I', 'J': 'J', 'K': 'K', 'L': 'L', 'M': 'M', 'N': 'N', 'O': 'O', 'P': 'P',
    'Q': 'Q', 'R': 'R', 'S': 'S', 'T': 'T', 'U': 'U', 'V': 'V', 'W': 'W', 'X': 'X',
    'Y': 'Y', 'Z': 'Z',
    'N0': '0', 'N1': '1', 'N2': '2', 'N3': '3', 'N4': '4', 'N5': '5', 'N6': '6',
    'N7': '7', 'N8': '8', 'N9': '9',
    'F1': 'F1', 'F2': 'F2', 'F3': 'F3', 'F4': 'F4', 'F5': 'F5', 'F6': 'F6', 'F7': 'F7',
    'F8': 'F8', 'F9': 'F9', 'F10': 'F10', 'F11': 'F11', 'F12': 'F12',
    'TAB': '⇥', 'ENTER': '⏎', 'BSPC': '⌫', 'DELETE': '⌦',
    'ESC': 'Esc', 'SPACE': '␣',
    'LSHFT': '⇧', 'RSHFT': '⇧', 'LCTRL': '⌃', 'RCTRL': '⌃',
    'LALT': '⌥', 'RALT': '⌥', 'LGUI': '⌘', 'RGUI': '⌘',
    'SEMI': ';', 'SQT': "'", 'GRAVE': '`', 'MINUS': '-', 'EQUAL': '=',
    'LBKT': '[', 'RBKT': ']', 'BSLH': '\\', 'FSLH': '/', 'COMMA': ',', 'DOT': '.',
    'CAPS': '⇪', 'INS': 'Ins', 'HOME': 'Home', 'END': 'End',
    'PG_UP': 'PgUp', 'PG_DN': 'PgDn',
    'UP': '↑', 'DOWN': '↓', 'LEFT': '←', 'RIGHT': '→',
    'C_VOL_UP': 'Vol+', 'C_VOL_DN': 'Vol−', 'C_MUTE': 'Mute',
    'C_AC_BACK': '◀Web', 'C_AC_FORWARD': 'Web▶', 'C_AC_REFRESH': 'Web⟳',
}
MODSYM = {'LG': '⌘', 'RG': '⌘', 'LC': '⌃', 'RC': '⌃',
          'LA': '⌥', 'RA': '⌥', 'LS': '⇧', 'RS': '⇧'}
LAYER_SHORT = {0: 'Base', 1: 'Win', 2: 'Media', 3: 'Adj', 4: 'Mix', 5: 'Num',
               6: 'Num2', 7: 'Sym', 8: 'AdjMac'}
MACRO_EXPLAIN = {
    '&zmae': 'Types "ä"; hold Shift while tapping for "Ä". Sends macOS '
             'Option+"u" diaeresis dead-key (at the Colemak position for "u", '
             'i.e. physical I) then the vowel.',
    '&zmoe': 'Types "ö"; hold Shift while tapping for "Ö". Same '
             'Option+dead-key mechanism as ä/ü.',
    '&zmue': 'Types "ü"; hold Shift while tapping for "Ü". Same '
             'Option+dead-key mechanism as ä/ö.',
    '&zm4': 'Macro: press Cmd+Option, tap N, release Cmd+Option.',
    '&gresc': 'Tap for Escape. Tap while holding Shift or Cmd/Win for a backtick/tilde.',
}


def key_label(code):
    return KEY.get(code, code)


def parse_mod_wrap(code):
    m = re.match(r'^(LG|RG|LC|RC|LA|RA|LS|RS)\((.+)\)$', code)
    if not m:
        return None
    modname, inner = m.groups()
    prefix, base = parse_mod_wrap(inner) or ('', key_label(inner))
    return (MODSYM[modname] + prefix, base)


def full_key(code):
    r = parse_mod_wrap(code)
    if r:
        prefix, base = r
        return prefix + base
    return key_label(code)


def label_for(token):
    t = token.strip()
    if t == '&trans':
        return dict(main='', sub='', full='transparent', kind='trans')
    if t == '&none':
        return dict(main='', sub='', full='none', kind='none')
    m = re.match(r'^&kp (.+)$', t)
    if m:
        return dict(main=full_key(m.group(1)), sub='', full=t, kind='kp')
    m = re.match(r'^&(hm_l|hm_r|hm_shift_l|hm_shift_r|hm) (\S+) (\S+)$', t)
    if m:
        _, mod, key = m.groups()
        return dict(main=key_label(key), sub=key_label(mod), full=t, kind='ht')
    m = re.match(r'^&lt (\d+) (\S+)$', t)
    if m:
        layer, key = m.groups()
        return dict(main=key_label(key), sub='▽' + LAYER_SHORT.get(int(layer), layer), full=t, kind='lt')
    m = re.match(r'^&mo (\d+)$', t)
    if m:
        return dict(main=LAYER_SHORT.get(int(m.group(1)), m.group(1)), sub='hold', full=t, kind='mo')
    m = re.match(r'^&tog (\d+)$', t)
    if m:
        return dict(main=LAYER_SHORT.get(int(m.group(1)), m.group(1)), sub='toggle', full=t, kind='tog')
    m = re.match(r'^&to (\d+)$', t)
    if m:
        return dict(main=LAYER_SHORT.get(int(m.group(1)), m.group(1)), sub='to', full=t, kind='to')
    m = re.match(r'^&bt BT_SEL (\d+)$', t)
    if m:
        return dict(main='BT' + m.group(1), sub='select', full=t, kind='bt')
    if t == '&bt BT_CLR':
        return dict(main='BT', sub='clear', full=t, kind='bt')
    if t == '&bootloader':
        return dict(main='Boot', sub='loader', full=t, kind='sys')
    if t == '&caps_word':
        return dict(main='Caps', sub='word', full=t, kind='sys')
    if t == '&gresc':
        return dict(main='Esc', sub='` ~', full=t, kind='morph')
    if t in ('&zmae', '&zmoe', '&zmue'):
        letter = {'&zmae': ('ä', 'Ä'), '&zmoe': ('ö', 'Ö'),
                  '&zmue': ('ü', 'Ü')}[t]
        return dict(main=letter[0], sub=letter[1] + ' (⇧)', full=t, kind='macro')
    if t == '&zm4':
        return dict(main='⌘⌥N', sub='macro', full=t, kind='macro')
    m = re.match(r'^&mkp (\S+)$', t)
    if m:
        return dict(main=m.group(1), sub='click', full=t, kind='mouse')
    return dict(main=t.lstrip('&'), sub='', full=t, kind='?')


def extract_layers(text):
    km = text[text.index('keymap {'):]
    layers = re.findall(
        r'(\w+_layer)\s*\{(.*?)\n        \};', km, re.S)
    out = []
    for name, body in layers:
        dm = re.search(r'display-name = "([^"]+)"', body)
        display = dm.group(1) if dm else name
        bm = re.search(r'bindings\s*=\s*<(.*?)>;', body, re.S)
        toks = re.findall(r'&\S+(?: [A-Za-z0-9_().+-]+){0,3}?(?=\s+&|\s*$)', bm.group(1))
        sm = re.search(r'sensor-bindings = <(.*?)>;', body)
        sensor = None
        if sm:
            pairs = re.findall(r'&inc_dec_kp (\S+) (\S+)', sm.group(1))
            sensor = [dict(cw=full_key(a), ccw=full_key(b)) for a, b in pairs]
        out.append(dict(name=name, display=display,
                         cells=[label_for(tok) for tok in toks], sensor=sensor))
    return out


def extract_combos(text):
    block = re.search(r'combos \{(.*?)\n    \};', text, re.S).group(1)
    combos = re.findall(
        r'(\w+) \{\s*bindings = <([^>]+)>;\s*key-positions = <([^>]+)>;\s*layers = <([^>]+)>;',
        block)
    out = []
    for name, binding, positions, layers in combos:
        m = re.match(r'^&kp (.+)$', binding.strip())
        label = full_key(m.group(1)) if m else binding
        out.append(dict(name=name, label=label,
                         positions=[int(p) for p in positions.split()],
                         layers=[int(l) for l in layers.split()]))
    return out


def extract_coords(text):
    m = re.search(r'keys\s*//.*?\n\s*=\s*(.*?);', text, re.S)
    entries = re.findall(r'<&key_physical_attrs\s+([^>]+)>', m.group(1))
    coords = []
    for e in entries:
        parts = [p.strip('()') for p in e.split()]
        w, h, x, y = map(int, parts[:4])
        rot = int(parts[4]) if len(parts) > 4 else 0
        coords.append((x, y, rot))
    return coords


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "keymap-viz.html"

    keymap_text = KEYMAP.read_text()
    layouts_text = LAYOUTS_DTSI.read_text()

    data = dict(
        coords=extract_coords(layouts_text),
        layers=extract_layers(keymap_text),
        combos=extract_combos(keymap_text),
    )
    payload = json.dumps(data)
    if '</script' in payload:
        raise SystemExit("generated data contains '</script' -- refusing to embed unescaped")

    template = TEMPLATE.read_text()
    marker = '<script id="viz-data" type="application/json">__DATA__</script>'
    if marker.replace('__DATA__', '__DATA__') not in template and '__DATA__' not in template:
        raise SystemExit(f"template {TEMPLATE} has no __DATA__ placeholder")
    html = template.replace('__DATA__', payload)

    out_path.write_text(html)
    print(f"wrote {out_path} ({len(html)} bytes, {len(data['layers'])} layers, "
          f"{len(data['combos'])} combos)")


if __name__ == '__main__':
    main()
