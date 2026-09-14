#!/usr/bin/env bash
# Build ZMK firmware for every (or one) target in build.yaml, using the
# official zmkfirmware/zmk-build-arm:stable Docker image, replicating the
# exact `west build` invocation used by zmkfirmware/zmk's
# build-user-config.yml reusable GitHub Actions workflow:
#
#   west build -s zmk/app -d <build_dir> -b <board> [-S <snippet>] -- \
#       -DZMK_CONFIG=<ws>/config -DZMK_EXTRA_MODULES=<repo> [-DSHIELD="<shield>"]
#
# Usage:
#   scripts/docker-build.sh              # build every target in build.yaml
#   scripts/docker-build.sh <artifact>   # build only the target with this
#                                         # artifact-name (see build.yaml)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WS_DIR="$REPO_ROOT/.west-workspace"
OUT_DIR="$REPO_ROOT/firmware"
DOCKER_IMAGE="${DOCKER_IMAGE:-zmkfirmware/zmk-build-arm:stable}"
FILTER="${1:-}"

if [ ! -d "$WS_DIR/.west" ]; then
    echo "==> No west workspace found, running docker-init.sh first" >&2
    "$REPO_ROOT/scripts/docker-init.sh"
fi

# docker-init.sh only copies config/ into the workspace once, at setup time.
# Re-sync it on every build so local keymap/config edits actually get built
# (otherwise the workspace's stale copy from init silently wins).
echo "==> Syncing $REPO_ROOT/config -> $WS_DIR/config"
mkdir -p "$WS_DIR/config"
cp -R "$REPO_ROOT/config/." "$WS_DIR/config/"

mkdir -p "$OUT_DIR"

fail=0
built=()

while IFS='|' read -r board shield snippet artifact; do
    [ -z "$board" ] && continue
    if [ -n "$FILTER" ] && [ "$artifact" != "$FILTER" ]; then
        continue
    fi

    echo "=================================================================="
    echo "==> Building $artifact  (board=$board shield='$shield' snippet='$snippet')"
    echo "=================================================================="

    # Only pass SHIELD/SNIPPET as env vars when non-empty: Zephyr's CMake
    # treats an *empty but defined* SHIELD/SNIPPET env var as an explicit
    # (invalid) selection, not as "unset".
    docker_env_args=(-e ARTIFACT="$artifact" -e BOARD="$board")
    [ -n "$shield" ] && docker_env_args+=(-e SHIELD="$shield")
    [ -n "$snippet" ] && docker_env_args+=(-e SNIPPET="$snippet")

    if ! docker run --rm \
        -v "$REPO_ROOT:/repo" \
        -v "$WS_DIR:/ws" \
        -w /ws \
        "${docker_env_args[@]}" \
        "$DOCKER_IMAGE" \
        bash -euxc '
            build_dir=".build/$ARTIFACT"
            rm -rf "$build_dir"

            west_args=()
            [ -n "${SNIPPET:-}" ] && west_args+=(-S "$SNIPPET")

            cmake_args=(-DZMK_CONFIG=/ws/config -DZMK_EXTRA_MODULES=/repo -DZephyr_DIR=/ws/zephyr/share/zephyr-package/cmake)
            [ -n "${SHIELD:-}" ] && cmake_args+=(-DSHIELD="$SHIELD")

            west build -s zmk/app -d "$build_dir" -b "$BOARD" "${west_args[@]}" -- "${cmake_args[@]}"

            mkdir -p /repo/firmware
            if [ -f "$build_dir/zephyr/zmk.uf2" ]; then
                cp "$build_dir/zephyr/zmk.uf2" "/repo/firmware/$ARTIFACT.uf2"
            else
                cp "$build_dir/zephyr/zmk.bin" "/repo/firmware/$ARTIFACT.bin"
            fi
        ' < /dev/null
    then
        echo "!!! Build failed for $artifact" >&2
        fail=1
        continue
    fi

    built+=("$artifact")
done < <(python3 "$REPO_ROOT/scripts/build_targets.py")

echo
echo "==> Done. Successfully built: ${built[*]:-none}"
if [ "$fail" -ne 0 ]; then
    echo "==> One or more targets FAILED, see log above." >&2
    exit 1
fi
