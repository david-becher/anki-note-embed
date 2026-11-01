# Note Embed

Bindet den Inhalt einer **anderen Notiz** direkt in eine Karte ein – als
aufklappbaren Kasten. Die eingebettete Notiz bleibt eine eigene Notiz: Man
bearbeitet sie an einer Stelle, und jede Karte, die sie einbettet, zeigt
immer den aktuellen Stand.

Typischer Einsatz: Ein Prüfungsschema verweist auf einen Baustein, der eine
eigene Karte ist (z. B. „Verfassungsbeschwerde → Begründetheit →
Freiheitsgrundrecht“). In der Verfassungsbeschwerde-Karte lässt sich der
Baustein an Ort und Stelle aufklappen, ohne die Karte zu wechseln.

## Syntax

| Schreibweise im Feld                          | Ergebnis                                                 |
| --------------------------------------------- | -------------------------------------------------------- |
| `![Titel\|nid1234567890123]`                   | Kasten „Titel“, zugeklappt, darin der Inhalt der Notiz    |
| `!+[Titel\|nid1234567890123]`                  | derselbe Kasten, aufgeklappt                             |
| `!=[Titel\|nid1234567890123]`                  | nur der Inhalt, ohne Kasten und Titel                    |
| `<div class="ne-slot">[Titel\|nid…]</div>`     | wie `!=`, mit Kontext-Parametern (für erzeugte Karten)   |

Die Schreibweise ist die Link-Syntax des Add-ons **Anki Note Linker**
(`[Titel|nid…]`) mit einem vorangestellten `!` – angelehnt an Markdown, wo
`[…](…)` ein Link und `![…](…)` ein eingebettetes Bild ist.

- **Im Editor** bleibt die Einbettung ein normaler Note-Linker-Link:
  Doppelklick auf `nid…` öffnet die eingebettete Notiz, die Notiz erscheint
  in den Vorwärts-/Rückwärts-Links und im Graphen des Note Linkers.
- **Beim Lernen, in der Vorschau und in der Kartenvorlagen-Ansicht** wird
  der Inhalt eingesetzt. Der Titel klappt den Kasten auf und zu, das kleine
  `↗` öffnet die eingebettete Notiz (über den Note Linker).
- **Geändert wird immer die eingebettete Notiz selbst.** In der
  einbettenden Karte steht nur der Verweis.

Die Notiz-ID kopiert man wie gewohnt mit dem Note Linker (Kontextmenü
„Copy note link“) und setzt davor `!`, `!+` oder `!=`.

**Wann welche Schreibweise?**

- `![…]` – Vertiefung, die nicht zur Antwort dieser Karte gehört, aber bei
  Bedarf nachlesbar sein soll.
- `!+[…]` – Kern der Antwort, der auf einer eigenen Karte gepflegt wird.
- `!=[…]` – der Inhalt soll aussehen wie selbst geschrieben: ohne Rahmen,
  ohne Titel, ohne Klick. Reiner Text (z. B. eine einzeilige Definition)
  fließt in den Satz ein: `Wohnung, d. h. !=[Def. Wohnung|nid…].` ergibt
  „Wohnung, d. h. räumlich abgeschlossener, privater Lebensbereich.“
  Enthält die Notiz Absätze oder Listen, beginnt der Inhalt auf einer neuen
  Zeile. Auch gut in einem eigenen Kasten (`!+` gäbe dort einen Kasten im
  Kasten).
- `<div class="ne-slot">` – für Karten, die ein Skript erzeugt: eigenes
  Kasten-Design und Kontext-Parameter (siehe unten). Von Hand braucht man
  ihn nicht.

## Verhalten

- **Welches Feld?** Eingebettet wird das erste vorhandene, nicht leere Feld
  aus `embed_fields` (Standard: `Antwort`, `Back`, `Rückseite`, `Answer`),
  sonst das zweite Feld der Notiz. Je Notiztyp einstellbar
  (`embed_fields_by_notetype`), je Platzhalter über `data-ne-field="Feld"`.
- **Verschachtelt:** Einbettungen in der eingebetteten Notiz werden mit
  aufgelöst (bis `max_depth`, Standard 6 Ebenen).
- **Zyklenschutz:** Bettet eine Notiz (auch über Umwege) sich selbst ein,
  erscheint an der Stelle ein Hinweis mit Link statt einer Endlosschleife.
- **Fehlende Notiz:** Hinweis „Notiz nicht gefunden“ mit dem ursprünglichen
  Link.
- **Sauberes Einsetzen:**
  - `<script>` und `[sound:…]` werden aus dem eingebetteten Inhalt entfernt,
    Lückentext `{{c1::…}}` erscheint als normaler Text.
  - `id`, `for` und `name` bekommen je Einbettung ein eigenes Präfix. Radio-
    Buttons, Labels und Anker mehrerer Einbettungen kommen sich dadurch nicht
    in die Quere, auch wenn dieselbe Notiz zweimal eingebettet ist.
  - `<style>`-Blöcke wandern an den Anfang der Karte, jeder gleiche Block nur
    einmal. Haben alle Karten eines Decks dasselbe Stylesheet im Feld, steht
    es pro Karte trotzdem nur einmal im HTML.
- **Nichts wird gespeichert:** Das Add-on verändert keine Notizen. Es setzt
  den Inhalt nur beim Anzeigen ein.

## Kontext für eingebettete Notizen (für eigenes Design)

Ein Platzhalter kann der eingebetteten Notiz einen Kontext mitgeben:

```html
<div class="ne-slot" data-ne-ctx="verfassungsbeschwerde">[Freiheitsgrundrecht|nid…]</div>
```

Der Inhalt landet in `<div class="ne-content" data-ne-ctx="verfassungsbeschwerde">`.
Die eingebettete Notiz kann darauf in ihrem eigenen CSS reagieren, z. B.
Punkte ausblenden, die in diesem Zusammenhang keine Rolle spielen:

```css
.ne-content[data-ne-ctx="verfassungsbeschwerde"] .nur-im-gesetz { display: none }
```

Mit `data-ne-ctx-map="elternKontext=kontext;…"` hängt der Kontext vom
Kontext der umgebenden Einbettung ab (erste passende Zuordnung, sonst
`data-ne-ctx`).

## Konfiguration

Über *Extras → Add-ons → Note Embed → Config* (Beschreibung aller Optionen
auf Englisch in `config.md`):

| Option                     | Standard                                   | Beschreibung                                          |
| -------------------------- | ------------------------------------------ | ----------------------------------------------------- |
| `enabled`                  | `true`                                     | Add-on an/aus                                         |
| `embed_fields`             | `["Antwort","Back","Rückseite","Answer"]`  | eingebettetes Feld (erstes passendes)                 |
| `embed_fields_by_notetype` | `{}`                                       | Felder je Notiztyp, vor `embed_fields`                |
| `fallback_field`           | `1`                                        | Ersatzfeld (Position, 0 = erstes)                     |
| `generic_syntax`           | `true`                                     | `![…]`, `!+[…]`, `!=[…]` erkennen                     |
| `open_by_default`          | `false`                                    | `![…]`-Kästen aufgeklappt starten                     |
| `link_style`               | `"icon"`                                   | `icon` · `title` (Titel ist Link) · `none`            |
| `link_icon`                | `"↗"`                                      | Symbol für den Link                                   |
| `link_mode`                | `"auto"`                                   | `auto` · `linker` (Note-Linker-Syntax) · `own`        |
| `max_depth`                | `6`                                        | maximale Verschachtelungstiefe                        |
| `max_embeds_per_card`      | `200`                                      | Obergrenze je Kartenseite                             |
| `strip_scripts`            | `true`                                     | `<script>` aus eingebettetem Inhalt entfernen         |
| `strip_sound`              | `true`                                     | `[sound:…]` entfernen                                 |
| `reveal_cloze`             | `true`                                     | Lückentext als Text zeigen                            |
| `prefix_ids`               | `true`                                     | `id`/`for`/`name` eindeutig machen                    |
| `dedupe_styles`            | `true`                                     | Styles nach oben ziehen, doppelte entfernen           |
| `lazy_load`                | `false`                                    | Inhalt erst beim Aufklappen einsetzen (Skript)        |
| `inject_css`               | `true`                                     | Standard-Aussehen der Kästen mitliefern               |
| `label_…`                  | deutsche Texte                             | Tooltip und Hinweistexte                              |

## Aussehen anpassen

Das Add-on liefert ein schlichtes, neutrales Aussehen mit (funktioniert hell
und im Nachtmodus). Eigene Regeln im CSS des Notiztyps überschreiben es:

| Selektor      | Element                                    |
| ------------- | ------------------------------------------ |
| `.ne-embed`   | der Kasten (`<details>`)                   |
| `.ne-sum`     | Kopfzeile (`<summary>`)                    |
| `.ne-title`   | Titel                                      |
| `.ne-open`    | Link-Symbol                                |
| `.ne-content` | eingebetteter Inhalt (auch bei Platzhaltern) |
| `.ne-note`    | Hinweise (Zyklus, fehlende Notiz …)        |

## Funktionsweise (technisch)

Das Add-on hängt sich in `anki.hooks.card_did_render` ein. Dieser Hook läuft
bei jedem Rendern einer Karte außerhalb der Browser-Tabelle (Lernen,
Vorschau, Kartenvorlagen) und **vor** `gui_hooks.card_will_show`, in dem der
Note Linker `[Titel|nid…]` in Links umwandelt. Dadurch werden auch die Links
im eingesetzten Inhalt und im Kastentitel vom Note Linker verlinkt – egal, in
welcher Reihenfolge die Add-ons geladen werden. Der Hook wird an den Anfang
der Hook-Liste gesetzt, damit andere Add-ons, die im selben Hook arbeiten,
den eingebetteten Inhalt schon sehen.

Fehler im Hook werden abgefangen: Anki entfernt sonst einen Hook, der eine
Ausnahme wirft, und die Karte bliebe leer. Im Fehlerfall erscheint die Karte
unverändert.

Ohne Note Linker (`link_mode: "auto"`) setzt das Add-on eigene Links, die die
Notiz über `pycmd` im Browser öffnen (`webview_did_receive_js_message`).

## Grenzen

- **AnkiDroid, AnkiMobile, AnkiWeb** führen keine Add-ons aus. Dort erscheint
  statt des Inhalts der Link-Text (wie bisher beim Note Linker).
- In der **Spalte „Antwort“ der Browser-Tabelle** wird nichts eingesetzt
  (Anki ruft dort den Hook bewusst nicht auf).
- Eingebettet wird der **Feldinhalt**, nicht die fertig gerenderte Karte der
  anderen Notiz: Kartenvorlage und Notiztyp-CSS der eingebetteten Notiz
  werden nicht übernommen.
- Der Platzhalter `<div class="ne-slot">` darf nur den Link enthalten (keine
  weiteren `<div>` darin).

## Dateien

| Datei                 | Zweck                                          |
| --------------------- | ---------------------------------------------- |
| `__init__.py`         | Add-on-Code                                    |
| `manifest.json`       | Name/Paket/Metadaten für Anki                  |
| `config.json`         | Standard-Konfiguration                         |
| `config.md`           | Config-Beschreibung (in Anki sichtbar)         |
| `tests/test_render.py`| Tests gegen die echte Anki-Bibliothek, ohne GUI |
| `build.sh`            | Baut das `.ankiaddon`-Paket                    |
| `Makefile`            | `test`, `build`, `upload`, `publish`, `clean`  |
| `upload_ankiweb.py`   | Upload auf AnkiWeb (Playwright, headless)      |
| `ankiweb.md`          | Beschreibung für die AnkiWeb-Seite             |

## Entwicklung

```bash
make test       # Tests mit der echten Anki-Bibliothek (uv run --with anki)
make build      # -> note_embed.ankiaddon
make publish    # test + build + Upload (Zugangsdaten aus 1Password)
```

`make upload` legt beim ersten Mal ein neues AnkiWeb-Listing an und trägt
die neue `ankiweb_id` in `manifest.json` ein (danach committen).

## Installation / Aktivierung

*Extras → Add-ons → Aus Datei installieren…* → `note_embed.ankiaddon`, dann
**Anki neu starten**. Für klickbare Links das Add-on **Anki Note Linker**
installieren (AnkiWeb `1077002392`).

## Kompatibilität

Entwickelt gegen Anki 26.09 (Qt6), lauffähig ab Anki 23.10
(`min_point_version` 231000). Nutzt nur die stabilen Hooks
`card_did_render` und `webview_did_receive_js_message`.

## Lizenz

MIT — siehe [LICENSE](LICENSE).
