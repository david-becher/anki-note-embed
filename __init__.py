"""
Note Embed
==========

Shows the content of another note inside a card, as a collapsible box that
is filled in while the card is rendered. The embedded note stays a note of
its own: it is edited in one place, and every card that embeds it always
shows its current content.

- Generic syntax ``![Title|nid1234567890123]`` (closed box),
  ``!+[Title|nid1234567890123]`` (box that starts open) and
  ``!=[Title|nid1234567890123]`` (content only, no box; plain text flows
  into the surrounding sentence). This is the link syntax of the "Anki Note
  Linker" add-on with a leading ``!``, so in the editor and in the link
  graph the reference remains an ordinary note link.
- Placeholder syntax ``<div class="ne-slot">[Title|nid…]</div>`` for cards
  that are generated with their own box design and pass a context to the
  embedded note: only the placeholder is replaced by the content, the
  surrounding markup is left untouched.
- Works in the reviewer, the card previewer and the card layout screen.
- Embeds inside embedded notes are expanded too, with a depth limit and
  protection against cycles.

Design notes
------------
The replacement runs in ``anki.hooks.card_did_render``. That hook fires
for every render outside the Browser table (reviewer, previewer, card
layout), *before* ``gui_hooks.card_will_show``. The Note Linker converts
``[Title|nid…]`` into clickable links in ``card_will_show``; because this
add-on always runs earlier, the links it leaves in the output (box title,
"open" icon, links inside the embedded content) are converted by the Note
Linker afterwards, regardless of add-on load order. Nothing is written to
the collection: the stored field still contains the plain syntax, so the
editor (double-click on ``nid…``) and the Note Linker's graph keep working.

The hook is inserted at the *front* of the hook list, so that other add-ons
post-processing the rendered text in the same hook see the embedded content.
Anki removes a hook that raises, therefore all work is wrapped and a failure
leaves the card exactly as it was.

Embedded content is the raw HTML of one field of the target note (by default
the first of ``embed_fields`` that exists and is not empty). Before it is
inserted:

1. ``<script>`` elements are removed (they would run once per embed and
   assume they own the page), ``[sound:…]`` tags are removed (they are not
   turned into play buttons outside the regular render) and cloze markup is
   shown as plain text.
2. ``id``, ``for``, ``name`` (and ARIA id references, ``href="#…"``) get a
   prefix that is unique per embed. Embedding the same note twice, or a note
   whose markup also appears in the host card, would otherwise produce
   duplicate ids and radio groups that interfere with each other.
3. ``<style>`` blocks are lifted out and inserted once at the top of the
   card; identical blocks (and blocks the host card already contains) are
   dropped. A deck whose notes all carry the same stylesheet therefore
   ships that stylesheet only once per card.
4. Embeds inside the content are expanded with ``depth + 1``. The chain of
   note ids from the host card down to the current embed is passed along;
   a note that is already part of the chain is shown as a short notice
   instead of being expanded again.

Content inserted without a box (``!=`` and ``<span class="ne-slot">``) is
wrapped in a ``<span>`` when it contains no block-level markup, so a
one-line definition reads as part of the sentence it is embedded in;
otherwise it is wrapped in a ``<div>``.

A placeholder may pass a *context* to the embedded note
(``data-ne-ctx="…"``). It ends up on the content wrapper as
``<div class="ne-content" data-ne-ctx="…">``, so the embedded note's own CSS
can adapt its display to the place where it is embedded.
``data-ne-ctx-map="parentCtx=ctx;…"`` chooses the context depending on the
context of the enclosing embed.

Links are left in Note Linker syntax when that add-on is enabled. Without it
(``link_mode: "auto"``), the add-on renders its own links, which open the
target note in the Browser via ``pycmd``.
"""

import html
import re
import traceback

import anki.collection  # noqa: F401  (import order: anki.hooks needs it outside Anki)
from anki import hooks

try:
    import aqt
    from aqt import gui_hooks, mw
except Exception:  # outside the Anki GUI, e.g. in the tests
    aqt = None
    gui_hooks = None
    mw = None


ADDON_NAME = "Note Embed"
OPEN_CMD = "note_embed:open:"
NOTE_LINKER_ID = "1077002392"  # AnkiWeb id of "Anki Note Linker"

DEFAULT_CONFIG = {
    "enabled": True,
    "embed_fields": ["Antwort", "Back", "Rückseite", "Answer"],
    "embed_fields_by_notetype": {},
    "fallback_field": 1,
    "generic_syntax": True,
    "open_by_default": False,
    "link_style": "icon",
    "link_icon": "↗",
    "link_mode": "auto",
    "max_depth": 6,
    "max_embeds_per_card": 200,
    "strip_scripts": True,
    "strip_sound": True,
    "reveal_cloze": True,
    "prefix_ids": True,
    "dedupe_styles": True,
    "lazy_load": False,
    "inject_css": True,
    "label_open": "Notiz öffnen",
    "label_missing": "Notiz nicht gefunden",
    "label_empty": "Kein Inhalt zum Einbetten",
    "label_cycle": "Wird bereits weiter oben eingebettet",
    "label_depth": "Maximale Einbettungstiefe erreicht",
    "label_limit": "Zu viele Einbettungen auf dieser Karte",
}

_config_cache = None
_linker_cache = None


# =============================================================================
# Configuration
# =============================================================================

def get_config():
    """
    Return the add-on configuration merged with defaults (cached).
    """
    global _config_cache

    if _config_cache is not None:
        return _config_cache

    stored = {}

    if mw is not None and getattr(mw, "addonManager", None) is not None:
        stored = mw.addonManager.getConfig(__name__) or {}

    config = dict(DEFAULT_CONFIG)
    config.update({k: v for k, v in stored.items() if v is not None})

    _config_cache = config
    return config


def on_config_updated(_config=None):
    global _config_cache, _linker_cache
    _config_cache = None
    _linker_cache = None


def note_linker_active():
    """
    True if the "Anki Note Linker" add-on is installed and enabled.
    """
    global _linker_cache

    if _linker_cache is not None:
        return _linker_cache

    active = False
    manager = getattr(mw, "addonManager", None) if mw is not None else None

    if manager is not None:
        try:
            for folder in manager.allAddons():
                if not manager.isEnabled(folder):
                    continue
                name = (manager.addonName(folder) or "").lower()
                if folder == NOTE_LINKER_ID or "note linker" in name or "notelinker" in name:
                    active = True
                    break
        except Exception:
            active = False

    _linker_cache = active
    return active


# =============================================================================
# Syntax
# =============================================================================

# Link title as defined by Anki Note Linker: anything but "[" (escaped as "\[").
LINK_TITLE = r"(?:[^\[]|\\\[)*?"

LINK_RE = re.compile(r"\[(" + LINK_TITLE + r")\|nid(\d{13})\]", re.S)

EMBED_RE = re.compile(
    # <div class="ne-slot" …>[Title|nid…]</div>   (also <span>)
    r"(?P<slot><(?P<tag>div|span)\b(?P<attrs>[^>]*\bne-slot\b[^>]*)>(?P<inner>.*?)</(?P=tag)\s*>)"
    # ![Title|nid…]   !+[Title|nid…]   !=[Title|nid…]
    r"|(?P<gen>!(?P<mode>[+=]?)\[(?P<title>" + LINK_TITLE + r")\|nid(?P<nid>\d{13})\])",
    re.S | re.I,
)

# Markup that cannot live inside a <span>: content containing it is inserted as a block.
BLOCK_RE = re.compile(
    r"<(?:div|p|ul|ol|li|dl|dt|dd|table|thead|tbody|tfoot|tr|td|th|h[1-6]|details|summary|"
    r"section|article|aside|header|footer|nav|blockquote|pre|hr|figure|figcaption|form|fieldset|"
    r"template|center)\b",
    re.I,
)

ATTR_RE = re.compile(r"([\w:.-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')")

SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.S | re.I)
STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style\s*>", re.S | re.I)
SOUND_RE = re.compile(r"\[sound:[^\]]*\]")
CLOZE_RE = re.compile(
    r"\{\{c\d+::((?:(?!\{\{c\d+::|\}\}).)*?)(?:::(?:(?!\{\{|\}\}).)*?)?\}\}", re.S
)

TAG_RE = re.compile(r"<[A-Za-z][^<>]*>")
ID_ATTR_RE = re.compile(r"(\s(?:id|for|name|list|form)\s*=\s*)(\"|')(.*?)\2", re.I | re.S)
IDREF_ATTR_RE = re.compile(
    r"(\s(?:aria-labelledby|aria-describedby|aria-controls|aria-owns)\s*=\s*)(\"|')(.*?)\2",
    re.I | re.S,
)
HREF_ATTR_RE = re.compile(r"(\shref\s*=\s*)(\"|')#(.+?)\2", re.I | re.S)


def may_contain_embed(text):
    """
    Cheap pre-check, so cards without embeds are not touched at all.
    """
    return bool(text) and "|nid" in text and (
        "ne-slot" in text or "![" in text or "!+[" in text or "!=[" in text)


def parse_attrs(source):
    attrs = {}
    for m in ATTR_RE.finditer(source or ""):
        value = m.group(2) if m.group(2) is not None else m.group(3)
        attrs[m.group(1).lower()] = html.unescape(value)
    return attrs


def unescape_title(title):
    return title.replace("\\[", "[")


def resolve_context(attrs, parent_ctx):
    """
    Context for an embed: data-ne-ctx, or the entry of data-ne-ctx-map that
    matches the context of the enclosing embed.
    """
    ctx = (attrs.get("data-ne-ctx") or "").strip()
    mapping = attrs.get("data-ne-ctx-map") or ""

    for pair in mapping.split(";"):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        if key.strip() and key.strip() == parent_ctx:
            return value.strip()

    return ctx


# =============================================================================
# Preparing embedded content
# =============================================================================

def reveal_cloze(text):
    for _ in range(12):
        new = CLOZE_RE.sub(r"\1", text)
        if new == text:
            break
        text = new
    return text


def prefix_ids(text, prefix):
    """
    Make id/for/name (and references to them) unique for one embed.
    """
    def single(m):
        if not m.group(3):
            return m.group(0)
        return f"{m.group(1)}{m.group(2)}{prefix}{m.group(3)}{m.group(2)}"

    def several(m):
        ids = " ".join(prefix + x for x in m.group(3).split())
        return f"{m.group(1)}{m.group(2)}{ids}{m.group(2)}"

    def href(m):
        return f"{m.group(1)}{m.group(2)}#{prefix}{m.group(3)}{m.group(2)}"

    def tag(m):
        t = m.group(0)
        t = ID_ATTR_RE.sub(single, t)
        t = IDREF_ATTR_RE.sub(several, t)
        t = HREF_ATTR_RE.sub(href, t)
        return t

    return TAG_RE.sub(tag, text)


def normalize_css(css):
    return re.sub(r"\s+", " ", css).strip()


# =============================================================================
# Rendering
# =============================================================================

class RenderState:
    """
    Everything that belongs to rendering one side (question or answer).
    """

    def __init__(self, col, config, note_cache=None, use_linker=None):
        self.col = col
        self.config = config
        self.notes = note_cache if note_cache is not None else {}
        self.count = 0
        self.uid = 0
        self.styles = []
        self.style_keys = set()
        self.used = False
        self.lazy_used = False

        if use_linker is None:
            mode = config.get("link_mode", "auto")
            use_linker = mode == "linker" or (mode == "auto" and note_linker_active())
        self.use_linker = use_linker

    def note(self, nid):
        if nid not in self.notes:
            try:
                self.notes[nid] = self.col.get_note(nid)
            except Exception:
                self.notes[nid] = None
        return self.notes[nid]

    # -- links -----------------------------------------------------------------

    def link(self, title, nid):
        """
        A link to the note: Note Linker syntax, or an own link without it.
        """
        if self.use_linker:
            return f"[{title}|nid{nid}]"
        label = unescape_title(title) or f"nid{nid}"
        return (f'<a class="ne-link" href="#" '
                f'onclick="pycmd(\'{OPEN_CMD}{nid}\');return false;">{label}</a>')

    def notice(self, kind, label, title, nid, inline=False):
        icons = {"cycle": "↺", "missing": "⚠", "empty": "∅",
                 "depth": "⋯", "limit": "⋯"}
        tag = "span" if inline else "div"
        return (f'<{tag} class="ne-note ne-{kind}">{icons.get(kind, "")} '
                f'{html.escape(label)}: {self.link(title, nid)}</{tag}>')


def pick_field(note, config, wanted=None):
    names = list(note.keys())

    if wanted:
        return wanted if wanted in names else None

    candidates = []
    try:
        notetype = note.note_type()["name"]
        candidates += list((config.get("embed_fields_by_notetype") or {}).get(notetype, []))
    except Exception:
        pass
    candidates += list(config.get("embed_fields") or [])

    for name in candidates:
        if name in names and note[name].strip():
            return name

    fallback = config.get("fallback_field")
    if isinstance(fallback, int) and 0 <= fallback < len(names) and note[names[fallback]].strip():
        return names[fallback]

    for name in names:
        if note[name].strip():
            return name

    return None


def embedded_content(state, nid, title, depth, chain, ctx, wanted_field=None, inline=False):
    """
    The prepared and recursively expanded content of note ``nid``.

    Returns ``(html, True)`` or ``(notice_html, False)``.
    """
    config = state.config

    def notice(kind):
        return state.notice(kind, config[f"label_{kind}"], title, nid, inline), False

    if nid in chain:
        return notice("cycle")
    if depth >= int(config.get("max_depth", 6)):
        return notice("depth")
    if state.count >= int(config.get("max_embeds_per_card", 200)):
        return notice("limit")

    note = state.note(nid)
    if note is None:
        return notice("missing")

    field = pick_field(note, config, wanted_field)
    if field is None or not note[field].strip():
        return notice("empty")

    state.count += 1
    state.uid += 1
    text = note[field]

    if config.get("strip_scripts", True):
        text = SCRIPT_RE.sub("", text)
    if config.get("strip_sound", True):
        text = SOUND_RE.sub("", text)
    if config.get("reveal_cloze", True):
        text = reveal_cloze(text)
    if config.get("prefix_ids", True):
        text = prefix_ids(text, f"ne{state.uid}-")
    if config.get("dedupe_styles", True):
        text = lift_styles(state, text)

    text = expand(state, text, depth + 1, chain + (nid,), ctx)
    return text, True


def lift_styles(state, text):
    def take(m):
        key = normalize_css(m.group(1))
        if key and key not in state.style_keys:
            state.style_keys.add(key)
            state.styles.append((key, m.group(0)))
        return ""

    return STYLE_RE.sub(take, text)


def is_inline(body):
    return BLOCK_RE.search(body) is None


def content_wrapper(state, nid, ctx, body, lazy, tag="div"):
    ctx_attr = f' data-ne-ctx="{html.escape(ctx, quote=True)}"' if ctx else ""
    if lazy:
        state.lazy_used = True
        tag = "div"
        body = f'<template class="ne-lazy">{body}</template>'
    return f'<{tag} class="ne-content" data-ne-nid="{nid}"{ctx_attr}>{body}</{tag}>'


def expand(state, text, depth=0, chain=(), parent_ctx=""):
    """
    Replace all embeds in ``text`` (one level; deeper levels recursively).
    """
    config = state.config

    def replace(m):
        if m.group("slot") is not None:
            link = LINK_RE.search(m.group("inner"))
            if link is None:
                return m.group(0)
            title, nid = link.group(1), int(link.group(2))
            attrs = parse_attrs(m.group("attrs"))
            ctx = resolve_context(attrs, parent_ctx)
            span = m.group("tag").lower() == "span"
            state.used = True
            body, ok = embedded_content(state, nid, title, depth, chain, ctx,
                                        attrs.get("data-ne-field"), inline=span)
            if not ok:
                return body
            tag = "span" if span and is_inline(body) else "div"
            return content_wrapper(state, nid, ctx, body,
                                   bool(config.get("lazy_load")) and tag == "div", tag)

        if not config.get("generic_syntax", True):
            return m.group(0)

        title, nid, mode = m.group("title"), int(m.group("nid")), m.group("mode")
        state.used = True

        if mode == "=":
            # Content only: no box, no title; plain text flows into the sentence.
            body, ok = embedded_content(state, nid, title, depth, chain, "", inline=True)
            if not ok:
                return body
            return content_wrapper(state, nid, "", body, False,
                                   "span" if is_inline(body) else "div")

        is_open = mode == "+" or bool(config.get("open_by_default"))
        body, ok = embedded_content(state, nid, title, depth, chain, "")
        if ok:
            body = content_wrapper(state, nid, "", body,
                                   bool(config.get("lazy_load")) and not is_open)
        else:
            body = f'<div class="ne-content" data-ne-nid="{nid}">{body}</div>'

        style = config.get("link_style", "icon")
        if style == "title":
            head = f'<span class="ne-title">{state.link(title, nid)}</span>'
        else:
            head = f'<span class="ne-title">{unescape_title(title)}</span>'
            if style == "icon":
                head += (f'<span class="ne-open" title="{html.escape(config["label_open"], quote=True)}">'
                         f'{state.link(title, nid)}</span>')

        return (f'<details class="ne-embed ne-box" data-ne-nid="{nid}"{" open" if is_open else ""}>'
                f'<summary class="ne-sum">{head}</summary>{body}</details>')

    return EMBED_RE.sub(replace, text)


def addon_css(config):
    icon = str(config.get("link_icon") or "↗").replace("\\", "\\\\").replace('"', '\\"')
    return (
        '<style class="ne-style">'
        ".ne-embed{display:block;text-align:left;margin:.45em 0;border:1px solid rgba(128,128,128,.38);"
        "border-radius:8px;background:rgba(128,128,128,.06)}"
        ".ne-embed>summary.ne-sum{display:flex;align-items:baseline;gap:.5em;cursor:pointer;"
        "padding:.35em .75em;list-style:none;font-weight:600}"
        ".ne-embed>summary.ne-sum::-webkit-details-marker{display:none}"
        ".ne-embed>summary.ne-sum::before{content:'\\25B8';flex:none;width:.8em;line-height:1;"
        "text-align:center;opacity:.55;transition:transform .12s}"
        ".ne-embed[open]>summary.ne-sum::before{transform:rotate(90deg)}"
        ".ne-embed>.ne-content{padding:.2em .85em .65em;border-top:1px dashed rgba(128,128,128,.38)}"
        ".ne-title{flex:1 1 auto}"
        ".ne-open{flex:none;font-weight:400}"
        ".ne-open:not(:has(a)){display:none}"
        ".ne-open a{font-size:0;text-decoration:none;color:inherit;opacity:.65}"
        ".ne-open a:hover{opacity:1}"
        f'.ne-open a::after{{content:"{icon}";font-size:14px;padding:0 .2em}}'
        "div.ne-content{display:block}span.ne-content{display:inline}"
        ".ne-note{margin:.3em 0;font-size:.9em;font-style:italic;opacity:.78}"
        "</style>"
    )


LAZY_SCRIPT = (
    "<script>(function(){"
    "function flush(root){for(var g=0;g<50;g++){var n=0;"
    "(root||document).querySelectorAll('template.ne-lazy').forEach(function(t){"
    "var d=t.parentElement&&t.parentElement.closest('details');"
    "if(!d||d.open){t.replaceWith(t.content);n++;}});if(!n)break;}}"
    "if(!window.__noteEmbedLazy){window.__noteEmbedLazy=1;"
    "document.addEventListener('toggle',function(e){var d=e.target;"
    "if(d&&d.open&&d.querySelectorAll)flush(d);},true);}"
    "flush(document);})();</script>"
)


def render_embeds(text, col, config=None, host_nid=0, note_cache=None, use_linker=None):
    """
    Return ``text`` with all embeds replaced. Unchanged if there are none.
    """
    config = config or get_config()

    if not may_contain_embed(text):
        return text

    state = RenderState(col, config, note_cache, use_linker)
    out = expand(state, text, 0, (host_nid,) if host_nid else (), "")

    if not state.used:
        return text

    head = addon_css(config) if config.get("inject_css", True) else ""

    if state.styles:
        own = {normalize_css(m.group(1)) for m in STYLE_RE.finditer(out)}
        head += "".join(block for key, block in state.styles if key not in own)

    tail = LAZY_SCRIPT if state.lazy_used else ""
    return head + out + tail


# =============================================================================
# Hooks
# =============================================================================

def on_card_did_render(output, ctx):
    try:
        config = get_config()
        if not config.get("enabled", True):
            return

        col = ctx.col()
        try:
            host_nid = int(ctx.note().id or 0)
        except Exception:
            host_nid = 0

        cache = {}
        output.question_text = render_embeds(output.question_text, col, config, host_nid, cache)
        output.answer_text = render_embeds(output.answer_text, col, config, host_nid, cache)
    except Exception:
        # Never let Anki drop the hook, and never break the card.
        traceback.print_exc()


def on_js_message(handled, message, context):
    if not isinstance(message, str) or not message.startswith(OPEN_CMD):
        return handled

    try:
        nid = int(message[len(OPEN_CMD):])
    except ValueError:
        return handled

    if aqt is not None and mw is not None:
        aqt.dialogs.open("Browser", mw, search=(f"nid:{nid}",))

    return (True, None)


def register_hooks():
    hook_list = getattr(hooks.card_did_render, "_hooks", None)

    if isinstance(hook_list, list):
        if on_card_did_render not in hook_list:
            hook_list.insert(0, on_card_did_render)
    else:
        hooks.card_did_render.append(on_card_did_render)

    if gui_hooks is not None:
        gui_hooks.webview_did_receive_js_message.append(on_js_message)

    if mw is not None and getattr(mw, "addonManager", None) is not None:
        mw.addonManager.setConfigUpdatedAction(__name__, on_config_updated)


register_hooks()
