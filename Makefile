# Docker-based build chain for zmk-keyboard-cornix.
#
# Uses the same zmkfirmware/zmk-build-arm:stable image and `west build`
# invocation as the official GitHub Actions CI (build-user-config.yml),
# so results should match what CI produces. No local Zephyr SDK / west
# / Nix install is required, only Docker.
#
# Targets:
#   make init          set up (or update) the isolated west workspace
#   make build          build every target listed in build.yaml
#   make build ARTIFACT=cornix_left_default_nosd   build a single target
#   make targets        list the targets build.yaml defines
#   make vis             regenerate the interactive keymap visualization
#   make shell           interactive shell in the build container
#   make clean            remove build output (keeps west workspace cache)
#   make clean-all         also remove the west workspace (forces re-clone)
#
# Output UF2/bin files land in ./firmware/<artifact-name>.uf2

.PHONY: init build targets vis shell clean clean-all

init:
	./scripts/docker-init.sh

build:
	./scripts/docker-build.sh $(ARTIFACT)

targets:
	python3 scripts/build_targets.py

vis:
	python3 scripts/gen_keymap_viz.py
	@echo "open keymap-viz.html in a browser to view it"

shell:
	docker run --rm -it \
		-v "$(CURDIR):/repo" \
		-v "$(CURDIR)/.west-workspace:/ws" \
		-w /ws \
		zmkfirmware/zmk-build-arm:stable bash

clean:
	rm -rf .west-workspace/.build firmware

clean-all: clean
	rm -rf .west-workspace
