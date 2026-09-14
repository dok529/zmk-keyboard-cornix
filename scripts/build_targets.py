#!/usr/bin/env python3
"""Parse build.yaml's `include:` list without needing PyYAML/yq.

Only supports the simple subset of YAML actually used in build.yaml: a
top-level `include:` list of flat mappings with `board`, `shield`,
`snippet`, `artifact-name` string keys (one per line), and `#` comments.

Prints one line per target as '|'-separated fields:
    board|shield|snippet|artifact-name
(shield/snippet/artifact-name may be empty strings)

'|' is used instead of a tab because bash's IFS field splitting treats
tab as whitespace and silently collapses/drops empty fields between
consecutive tabs, which would misalign columns whenever shield/snippet
are empty.
"""
import re
import sys
from pathlib import Path

BUILD_YAML = Path(__file__).resolve().parent.parent / "build.yaml"

KEY_RE = re.compile(r'^(board|shield|snippet|artifact-name)\s*:\s*(.*)$')


def strip_comment(line: str) -> str:
    # build.yaml has no strings containing '#', so a plain split is safe.
    return line.split('#', 1)[0]


def parse(text: str):
    lines = text.splitlines()
    in_include = False
    targets = []
    current = None
    for raw in lines:
        line = strip_comment(raw).rstrip()
        if not line.strip():
            continue
        if line.startswith('include:'):
            in_include = True
            continue
        if not in_include:
            continue
        stripped = line.strip()
        if stripped.startswith('- '):
            if current:
                targets.append(current)
            current = {}
            stripped = stripped[2:].strip()
        if current is None:
            continue
        m = KEY_RE.match(stripped)
        if m:
            key, val = m.groups()
            current[key] = val.strip().strip('"').strip("'")
    if current:
        targets.append(current)
    return targets


def main():
    text = BUILD_YAML.read_text()
    targets = parse(text)
    if not targets:
        print("no targets found in build.yaml", file=sys.stderr)
        sys.exit(1)
    for t in targets:
        board = t.get('board', '')
        if not board:
            continue
        shield = t.get('shield', '')
        snippet = t.get('snippet', '')
        artifact = t.get('artifact-name', '')
        if not artifact:
            artifact = (f"{shield.replace(' ', '+')}-" if shield else '') + board.replace('/', '_')
        print('|'.join([board, shield, snippet, artifact]))


if __name__ == '__main__':
    main()
