Embeds the content of another note right inside a card, as a collapsible box. The embedded note stays a note of its own: edit it in one place, and every card that embeds it always shows the current version.

<b>Syntax</b>
<ul>
<li><code>![Title|nid1234567890123]</code> – closed box with the content of that note</li>
<li><code>!+[Title|nid1234567890123]</code> – the same box, open</li>
<li><code>&lt;div class="ne-slot"&gt;[Title|nid…]&lt;/div&gt;</code> – only the content, for cards with their own box design</li>
</ul>

<b>Works together with Anki Note Linker</b>
<ul>
<li>The syntax is the Note Linker link format with a leading <code>!</code>, so in the editor it stays a regular link (double-click opens the note) and shows up in the link graph</li>
<li>In the reviewer, the previewer and the card layout screen the content is inserted; the title toggles the box, a small ↗ opens the embedded note</li>
<li>Without Note Linker the add-on renders its own links, which open the note in the Browser</li>
</ul>

<b>Behaviour</b>
<ul>
<li>Embeds inside embedded notes are expanded too (depth limit), cycles are detected and shown as a notice</li>
<li>Field to embed is configurable (default: Antwort / Back / Rückseite / Answer, per note type if needed)</li>
<li>Scripts and sound tags are removed from embedded content, cloze markup is shown as text</li>
<li>ids, labels and radio groups are made unique per embed, so interactive content keeps working when embedded</li>
<li>Style blocks are moved to the top and each one is kept only once</li>
<li>Optional context per embed (<code>data-ne-ctx</code>) lets the embedded note adapt its display via CSS</li>
<li>Nothing is written to your collection – content is inserted while the card is shown</li>
</ul>

<b>Configuration</b> (Tools → Add-ons → Config)
<ul>
<li><code>embed_fields</code>, <code>embed_fields_by_notetype</code>, <code>fallback_field</code></li>
<li><code>open_by_default</code>, <code>link_style</code>, <code>link_icon</code>, <code>link_mode</code></li>
<li><code>max_depth</code>, <code>max_embeds_per_card</code>, <code>lazy_load</code></li>
<li><code>strip_scripts</code>, <code>strip_sound</code>, <code>reveal_cloze</code>, <code>prefix_ids</code>, <code>dedupe_styles</code>, <code>inject_css</code></li>
</ul>

Note: AnkiDroid, AnkiMobile and AnkiWeb do not run add-ons; there the link text is shown instead of the content.

Developed for modern Anki (Qt6), 23.10 and later.

<b>Source & issues</b>
https://github.com/david-becher/anki-note-embed

Licensed under the MIT License.
