#!/usr/bin/env bash
#
# Build a distributable .ankiaddon package for AnkiWeb / manual install.
# The archive contains the add-on files at its root (no wrapping folder)
# and excludes development and runtime artifacts.
#
set -euo pipefail

cd "$(dirname "$0")"

NAME="note_embed"
OUT="${NAME}.ankiaddon"

rm -f "${OUT}"

zip -r "${OUT}" . \
    -x "*.pyc" \
    -x "__pycache__/*" \
    -x "*/__pycache__/*" \
    -x "meta.json" \
    -x ".git/*" \
    -x ".github/*" \
    -x ".idea/*" \
    -x ".gitignore" \
    -x ".DS_Store" \
    -x "build.sh" \
    -x "Makefile" \
    -x "upload_ankiweb.py" \
    -x "ankiweb.md" \
    -x "tests/*" \
    -x "*.ankiaddon"

echo "Wrote ${OUT}"
