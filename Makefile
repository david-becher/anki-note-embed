# Makefile for building and publishing this Anki add-on.
#
# Targets:
#   make test             Run the headless render tests (real Anki library, no GUI).
#   make build            Build the .ankiaddon package (runs build.sh).
#   make install-browser  One-time: install the headless Chromium for Playwright.
#   make upload           Upload the built package to AnkiWeb (headless).
#   make publish          test + build + upload.
#   make clean            Remove the built .ankiaddon.
#
# Credentials for `upload` come from 1Password via `op run`, using the item
# "ankiweb.net" in the Personal vault. Requires: uv, op (1Password CLI).

PACKAGE := $(shell python3 -c "import json;print(json.load(open('manifest.json'))['package'])")
ANKIADDON := $(PACKAGE).ankiaddon

OP_USER := op://Personal/ankiweb.net/username
OP_PASS := op://Personal/ankiweb.net/password

.PHONY: test build upload publish install-browser clean

test:
	uv run --with anki python3 tests/test_render.py

build:
	./build.sh

install-browser:
	uv run --with playwright playwright install chromium

upload:
	@test -f "$(ANKIADDON)" || { echo "Build first: make build"; exit 1; }
	ANKIWEB_USER="$(OP_USER)" ANKIWEB_PASS="$(OP_PASS)" \
		op run -- uv run upload_ankiweb.py

publish: test build upload

clean:
	rm -f "$(ANKIADDON)"
