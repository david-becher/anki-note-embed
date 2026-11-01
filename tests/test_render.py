"""
Headless tests against the real Anki library (no GUI needed).

    uv run --with anki python3 tests/test_render.py
    # or: pip install anki && python3 tests/test_render.py

Creates a temporary collection, adds a few notes that embed each other and
checks the rendered card HTML.
"""
import importlib.util
import os
import re
import sys
import tempfile

from anki.collection import Collection  # must be imported before anki.hooks

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load_addon():
    spec = importlib.util.spec_from_file_location(
        "note_embed", os.path.join(ROOT, "__init__.py"), submodule_search_locations=[ROOT])
    module = importlib.util.module_from_spec(spec)
    sys.modules["note_embed"] = module
    spec.loader.exec_module(module)
    return module


ne = load_addon()
ne._linker_cache = True  # behave as if Anki Note Linker were installed

failures = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failures.append(msg)


def add(col, front, back):
    note = col.new_note(col.models.by_name("Basic"))
    note["Front"], note["Back"] = front, back
    col.add_note(note, col.decks.id("Test"))
    return note


def answer(col, note):
    return note.cards()[0].answer()


def main():
    tmp = tempfile.mkdtemp()
    col = Collection(os.path.join(tmp, "test.anki2"))
    try:
        a = add(col, "A", '<style>.a{color:red}</style><b>Inhalt A</b>'
                          '<input type="radio" name="g" id="r1"><label for="r1">x</label>'
                          '<script>window.ranA=1</script>[sound:a.mp3] {{c1::Lösung::Hinweis}}')
        b = add(col, "B", f"Vor B ![A|nid{a.id}] nach B")
        c = add(col, "C", f"C: !+[B|nid{b.id}]")
        d = add(col, "D", "")
        d["Back"] = f"Selbst: ![D|nid{d.id}]"
        col.update_note(d)
        e = add(col, "E", "Fehlt: ![X|nid1234567890123]")
        f = add(col, "F", f'<div class="ne-slot" data-ne-ctx="k1">[A|nid{a.id}]</div>'
                          f'<div class="ne-slot" data-ne-ctx="z" data-ne-ctx-map="none=q">[A|nid{a.id}]</div>')
        g = add(col, "G", "Ganz normal [A|nid%d] ohne Einbettung" % a.id)
        h = add(col, "H", f"![A|nid{a.id}] ![A2|nid{a.id}]")
        cyc1 = add(col, "Z1", "")
        cyc2 = add(col, "Z2", f"Z2 bettet Z1 ein: ![Z1|nid{cyc1.id}]")
        cyc1["Back"] = f"Z1 bettet Z2 ein: ![Z2|nid{cyc2.id}]"
        col.update_note(cyc1)

        print("generic embed")
        html_b = answer(col, b)
        check('class="ne-embed ne-box"' in html_b, "box is rendered")
        check("<b>Inhalt A</b>" in html_b, "content of A is embedded")
        check(f"[A|nid{a.id}]" in html_b, "Note Linker link stays in the summary")
        check("<details" in html_b and " open>" not in html_b, "box starts closed")
        check("window.ranA" not in html_b, "script removed")
        check("[sound:" not in html_b, "sound tag removed")
        check("Lösung" in html_b and "{{c1::" not in html_b, "cloze shown as text")
        check('id="ne1-r1"' in html_b and 'for="ne1-r1"' in html_b and 'name="ne1-g"' in html_b,
              "ids, for and name prefixed")
        check(html_b.count(".a{color:red}") == 1 and html_b.index(".a{color:red}") < html_b.index("Vor B"),
              "style lifted to the top once")
        check('class="ne-style"' in html_b, "add-on CSS injected")

        print("nested + open")
        html_c = answer(col, c)
        check(" open>" in html_c, "!+ starts open")
        check("Vor B" in html_c and "<b>Inhalt A</b>" in html_c, "nested embed expanded")

        print("cycles, missing")
        html_d = answer(col, d)
        check("ne-cycle" in html_d, "self embed shows cycle notice")
        html_z = answer(col, cyc1)
        check(html_z.count("ne-cycle") == 1 and "Z2 bettet Z1 ein" in html_z, "two-note cycle stopped")
        html_e = answer(col, e)
        check("ne-missing" in html_e, "missing note notice")

        print("placeholder + context")
        html_f = answer(col, f)
        check('data-ne-ctx="k1"' in html_f, "context passed to wrapper")
        check('data-ne-ctx="z"' in html_f, "default context without map match")
        check("ne-slot" not in re.sub(r"<style.*?</style>", "", html_f, flags=re.S), "placeholders replaced")
        check("ne-embed" not in re.sub(r"<style.*?</style>", "", html_f, flags=re.S),
              "placeholder gets no extra box")

        print("untouched cards")
        html_g = answer(col, g)
        check('class="ne-' not in html_g and f"[A|nid{a.id}]" in html_g, "plain links are not touched")

        print("same note twice")
        html_h = answer(col, h)
        ids = re.findall(r'\sid="([^"]+)"', html_h)
        check(len(ids) == len(set(ids)), f"ids unique ({sorted(set(ids))})")

        print("context map")
        state = ne.RenderState(col, ne.get_config(), use_linker=True)
        out = ne.expand(state, f'<div class="ne-slot" data-ne-ctx="d" data-ne-ctx-map="p=m">[A|nid{a.id}]</div>',
                        0, (), "p")
        check('data-ne-ctx="m"' in out, "map picks context by parent context")

        print("own links without Note Linker")
        state = ne.RenderState(col, ne.get_config(), use_linker=False)
        out = ne.expand(state, f"![A|nid{a.id}]", 0, (), "")
        check(f"pycmd('note_embed:open:{a.id}')" in out, "fallback link opens the note")

        print("lazy loading")
        cfg = dict(ne.get_config(), lazy_load=True)
        out = ne.render_embeds(f"![A|nid{a.id}]", col, cfg, use_linker=True)
        check('<template class="ne-lazy">' in out and "__noteEmbedLazy" in out, "content in template + loader")

        print("hook stays registered")
        check(ne.on_card_did_render in ne.hooks.card_did_render._hooks, "hook present")
    finally:
        col.close()

    print()
    print("OK" if not failures else f"{len(failures)} FAILED")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
