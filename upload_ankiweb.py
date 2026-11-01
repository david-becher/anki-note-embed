# /// script
# requires-python = ">=3.9"
# dependencies = ["playwright"]
# ///
"""
Upload this add-on's built .ankiaddon package to AnkiWeb (headless).

AnkiWeb has no official upload API and its pages are a JS app, so this drives a
headless Chromium via Playwright: it logs in, opens the add-on's upload page,
sets the description from ``ankiweb.md``, attaches the .ankiaddon file, and
clicks Save.

If ``manifest.json`` has an ``ankiweb_id``, this UPDATES that listing
(``/shared/upload?id=<id>``). Otherwise it CREATES a new listing
(``/shared/upload``): the title is taken from the manifest ``name``, a branch is
added automatically, and the new id returned by AnkiWeb is written back into
``manifest.json`` (not committed — commit it yourself).

Credentials are read from the environment (inject them with 1Password's `op`):

    ANKIWEB_USER  – AnkiWeb email
    ANKIWEB_PASS  – AnkiWeb password

Typical invocation (see the Makefile ``upload`` target):

    ANKIWEB_USER="op://Personal/ankiweb.net/username" \
    ANKIWEB_PASS="op://Personal/ankiweb.net/password" \
    op run -- uv run upload_ankiweb.py

First run only, install the browser binary:

    uv run --with playwright playwright install chromium
"""
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


HERE = Path(__file__).resolve().parent


def read_manifest():
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    return manifest


def find_package(manifest):
    # The built file is "<package>.ankiaddon" next to this script.
    pkg = manifest.get("package")
    candidate = HERE / f"{pkg}.ankiaddon"
    if candidate.exists():
        return candidate
    # Fallback: any single .ankiaddon in the folder.
    files = sorted(HERE.glob("*.ankiaddon"))
    if len(files) == 1:
        return files[0]
    return None


def read_description():
    md = HERE / "ankiweb.md"
    if md.exists():
        return md.read_text(encoding="utf-8").strip()
    return ""


def _save_ankiweb_id(manifest, new_id):
    """Write ``ankiweb_id`` into manifest.json (kept 4-space indented).

    Does not commit — just updates the file so the next upload is an update.
    """
    manifest = dict(manifest)
    manifest["ankiweb_id"] = str(new_id)
    # Keep a stable, readable key order: put ankiweb_id right after homepage.
    ordered = {}
    for key, value in manifest.items():
        if key == "ankiweb_id":
            continue
        ordered[key] = value
        if key == "homepage":
            ordered["ankiweb_id"] = str(new_id)
    if "ankiweb_id" not in ordered:
        ordered["ankiweb_id"] = str(new_id)
    (HERE / "manifest.json").write_text(
        json.dumps(ordered, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main():
    manifest = read_manifest()
    addon_id = str(manifest.get("ankiweb_id", "")).strip()
    title = manifest.get("name", "").strip()

    package = find_package(manifest)
    if package is None:
        print("No built .ankiaddon found — run `make build` first.", file=sys.stderr)
        sys.exit(1)

    description = read_description()

    user = os.environ.get("ANKIWEB_USER", "")
    pw = os.environ.get("ANKIWEB_PASS", "")
    if not user or not pw:
        print("Missing ANKIWEB_USER / ANKIWEB_PASS in environment.", file=sys.stderr)
        sys.exit(2)

    # Update an existing listing, or create a new one if no id is set yet.
    is_update = bool(addon_id)
    upload_url = "https://ankiweb.net/shared/upload"
    if is_update:
        upload_url += "?id=" + addon_id

    print(f"Uploading {package.name} to AnkiWeb "
          f"({'update id ' + addon_id if is_update else 'NEW listing'}) …")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()

        # --- login ---
        page.goto("https://ankiweb.net/account/login", wait_until="networkidle")
        page.fill('input[placeholder="Email"]', user)
        page.fill('input[placeholder="Password"]', pw)
        page.click('button:has-text("Log In")')
        try:
            page.wait_for_url(lambda u: "/account/login" not in u, timeout=20000)
        except PWTimeout:
            print("Login failed (still on login page). Check credentials.",
                  file=sys.stderr)
            browser.close()
            sys.exit(3)

        # --- upload page ---
        page.goto(upload_url, wait_until="networkidle")

        # On the "Share Add-on" (create) page there is no file input until a
        # branch is added. Click "Add New Branch" to reveal it if needed.
        if page.query_selector('input[type="file"]') is None:
            add_branch = page.query_selector('button:has-text("Add New Branch")')
            if add_branch is not None:
                add_branch.click()
                page.wait_for_selector('input[type="file"]', timeout=10000)

        # Title: required for a new listing; for updates only set it if empty so
        # we don't clobber an existing AnkiWeb title.
        try:
            current_title = page.eval_on_selector(
                'input[placeholder="Title"]', "e => e.value"
            )
            if title and (not is_update or not current_title.strip()):
                page.fill('input[placeholder="Title"]', title)
        except Exception:
            pass

        # Description: always refresh from ankiweb.md.
        if description:
            page.fill("textarea", description)

        # Attach the built package.
        file_input = page.query_selector('input[type="file"]')
        if file_input is None:
            print("Could not find the file input on the upload page.",
                  file=sys.stderr)
            browser.close()
            sys.exit(4)
        file_input.set_input_files(str(package))

        # Save.
        page.click('button:has-text("Save")')

        # Success = redirect to /shared/info/<id>.
        try:
            page.wait_for_url("**/shared/info/**", timeout=30000)
            final = page.url
            new_id = final.rstrip("/").split("/")[-1].split("?")[0]
            print(f"Uploaded. Listing: {final}")
            if not is_update and new_id.isdigit():
                _save_ankiweb_id(manifest, new_id)
                print(f"New AnkiWeb id {new_id} written to manifest.json.")
                print("Review and commit it, e.g.:")
                print(f'  git add manifest.json && '
                      f'git commit -m "AnkiWeb: record ankiweb_id {new_id}"')
        except PWTimeout:
            # Surface any visible error message.
            body = ""
            try:
                body = page.inner_text("body")[:500]
            except Exception:
                pass
            print("Upload did not confirm (no redirect to /shared/info).",
                  file=sys.stderr)
            if body:
                print("Page said:\n" + body, file=sys.stderr)
            browser.close()
            sys.exit(5)

        browser.close()


if __name__ == "__main__":
    main()
