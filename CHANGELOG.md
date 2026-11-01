# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [1.1.0] - 2026-11-01

### Added
- Syntax `!=[Title|nid…]`: inserts the content without box and title, typed in
  the normal editor (no HTML editor needed).
- Content without block-level markup is inserted as a `<span>` by `!=` and by
  `<span class="ne-slot">`, so a one-line note reads as part of the sentence.

## [1.0.0] - 2026-11-01

### Added
- Embed the content of another note into a card while it is rendered
  (reviewer, previewer, card layout), via `anki.hooks.card_did_render`.
- Generic syntax `![Title|nid…]` (closed box) and `!+[Title|nid…]` (open box),
  compatible with the Anki Note Linker link format.
- Placeholder syntax `<div class="ne-slot">[Title|nid…]</div>` that inserts
  the bare content into a card's own box design.
- Recursive expansion with depth limit, per-card limit and cycle detection.
- Context passing to embedded notes via `data-ne-ctx` / `data-ne-ctx-map`.
- Clean insertion: scripts and sound tags removed, cloze shown as text,
  `id`/`for`/`name` prefixed per embed, `<style>` blocks lifted and deduplicated.
- Own links (opening the note in the Browser) when Anki Note Linker is not
  enabled.
- Optional lazy loading of closed boxes.
- Headless tests against the real Anki library (`make test`).
