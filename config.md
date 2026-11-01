# Note Embed – Configuration

**Syntax:** `![Title|nid1234567890123]` shows note 1234567890123 as a closed box,
`!+[Title|nid…]` as an open box, `!=[Title|nid…]` as bare content without a box
(plain text flows into the sentence). `<div class="ne-slot">[Title|nid…]</div>`
is replaced by the bare content as well and can pass a context (for generated
cards with their own box design).

- **enabled** (default `true`): Switch the add-on off without uninstalling it.

- **embed_fields** (default `["Antwort", "Back", "Rückseite", "Answer"]`): Which
  field of the embedded note is shown. The first field in this list that exists
  in the note and is not empty is used.

- **embed_fields_by_notetype** (default `{}`): Per note type, fields to try
  before `embed_fields`, e.g. `{"Rechtsfrage 2.21": ["Antwort"]}`.

- **fallback_field** (default `1`): If none of the listed fields fits, use the
  field with this position (0 = first field). If that is empty too, the first
  non-empty field is used. A placeholder can name a field directly with
  `data-ne-field="Name"`.

- **generic_syntax** (default `true`): Recognise `![…]`, `!+[…]` and `!=[…]`.
  Set to `false` to use placeholders only.

- **open_by_default** (default `false`): Let `![…]` boxes start open as well.

- **link_style** (default `"icon"`): How the box title links to the note.
  `"icon"`: the title opens/closes the box, a small icon opens the note.
  `"title"`: the title itself is the link. `"none"`: no link.

- **link_icon** (default `"↗"`): Symbol used for `link_style: "icon"`.

- **link_mode** (default `"auto"`): `"auto"` keeps links in Anki Note Linker
  syntax when that add-on is enabled (it turns them into links) and otherwise
  renders its own links, which open the note in the Browser. `"linker"` always
  leaves Note Linker syntax, `"own"` always renders own links.

- **max_depth** (default `6`): How many levels of embeds inside embeds are
  expanded. Deeper embeds are shown as a link.

- **max_embeds_per_card** (default `200`): Upper limit per card side.

- **strip_scripts** (default `true`): Remove `<script>` elements from embedded
  content.

- **strip_sound** (default `true`): Remove `[sound:…]` tags from embedded content.

- **reveal_cloze** (default `true`): Show `{{c1::text}}` in embedded content as
  plain text.

- **prefix_ids** (default `true`): Give `id`/`for`/`name` in embedded content a
  unique prefix, so radio buttons, labels and anchors of several embeds do not
  interfere.

- **dedupe_styles** (default `true`): Move `<style>` blocks of embedded content
  to the top of the card and keep each distinct block only once.

- **lazy_load** (default `false`): Insert the content of a closed box only when
  it is opened (uses a small script). Useful for very large embeds.

- **inject_css** (default `true`): Add the default look of the boxes. Set to
  `false` to style `.ne-embed`, `.ne-sum`, `.ne-title`, `.ne-open`,
  `.ne-content` and `.ne-note` entirely in your note type's CSS.

- **label_open**, **label_missing**, **label_empty**, **label_cycle**,
  **label_depth**, **label_limit**: Texts of the tooltip and of the notices
  shown instead of content (note not found, nothing to embed, cycle, depth
  limit, too many embeds).

Changes take effect for the next card that is shown.
