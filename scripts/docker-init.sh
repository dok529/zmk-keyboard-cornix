#!/usr/bin/env bash
# Set up an isolated west workspace for building this repo's ZMK firmware
# inside the official zmkfirmware/zmk-build-arm:stable Docker image.
#
# Mirrors what zmkfirmware/zmk's build-user-config.yml reusable workflow
# does when the repo carries a zephyr/module.yml (as this one does): the
# west workspace (ZMK core + west.yml modules) lives in an *isolated*
# directory, separate from the repo checkout, and the repo itself is
# passed in later as an extra module (-DZMK_EXTRA_MODULES) so its
# boards/shields are found without the repo itself being the west topdir.
#
# config/ is bind-mounted straight from the repo (read-only) rather than
# copied: west only ever reads its manifest directory, never writes to it,
# so the workspace's .west/config (which records "config" as a *relative*
# path under this same persistent workspace dir) stays valid across every
# separate `docker run` as long as config/ is mounted at the same spot
# every time -- which it is, here and in docker-build.sh. That means local
# keymap/config edits are always picked up automatically, with no sync
# step and no risk of ever building a stale copy again.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WS_DIR="$REPO_ROOT/.west-workspace"
DOCKER_IMAGE="${DOCKER_IMAGE:-zmkfirmware/zmk-build-arm:stable}"

mkdir -p "$WS_DIR"

echo "==> Using workspace: $WS_DIR"
echo "==> Docker image:    $DOCKER_IMAGE"

docker run --rm \
    -v "$REPO_ROOT:/repo:ro" \
    -v "$REPO_ROOT/config:/ws/config:ro" \
    -v "$WS_DIR:/ws" \
    -w /ws \
    "$DOCKER_IMAGE" \
    bash -euxc '
        if [ ! -d .west ]; then
            west init -l config
        fi
        west update --fetch-opt=--filter=blob:none
        west zephyr-export
    '

echo "==> West workspace ready in $WS_DIR"
