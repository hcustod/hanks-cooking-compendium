#!/usr/bin/env python3
"""
Console recipe scraper: fetches a URL, extracts schema.org/Recipe (JSON-LD/microdata/RDFa),
falls back to Readability, and prints a clean recipe or JSON.

Legal posture (simple & safe):
- No images are collected or displayed.
- Full source URL is included for attribution.
- A legal note is included in output to discourage redistribution.
"""

import sys
import argparse
import textwrap
import re
import unicodedata
import html as ihtml
from urllib.parse import urlparse

import httpx
import orjson
import extruct
from lxml import html as lxml_html
from readability import Document
from w3lib.html import get_base_url

UA = "CleanRecipeConsole/0.3 (personal-use; no-images; contact: console)"
LEGAL_NOTE = (
    "For personal use/research only. Do not republish; see the original source link."
)

# ---------- text cleanup utilities ----------

_ZERO_WIDTH = "".join(["\u200b", "\u200c", "\u200d", "\ufeff"])

def _strip_html_tags(s: str) -> str:
    if "<" in s and ">" in s:
        try:
            return lxml_html.fromstring(s).text_content()
        except Exception:
            return s
    return s

def clean_text(s: str) -> str:
    if s is None:
        return s
    # 1) Unescape HTML entities (&amp;, &#39;, &nbsp;, &frac12;, etc.)
    s = ihtml.unescape(s)
    # 2) Strip any inline tags left in fields
    s = _strip_html_tags(s)
    # 3) Normalize Unicode (compose accents etc.)
    s = unicodedata.normalize("NFC", s)
    # 4) Remove zero-width & non-breaking spaces
    for z in _ZERO_WIDTH:
        s = s.replace(z, "")
    s = s.replace("\u00a0", " ")
    # 5) Collapse excessive spaces/tabs (but keep newlines)
    s = re.sub(r"[ \t\f\v]+", " ", s)
    # 6) Trim
    return s.strip()

def deep_clean(x):
    """Recursively clean strings in dict/list structures."""
    if isinstance(x, str):
        return clean_text(x)
    if isinstance(x, list):
        out = [deep_clean(v) for v in x]
        # drop empties that may result from cleaning
        return [v for v in out if not isinstance(v, str) or v]
    if isinstance(x, dict):
        return {k: deep_clean(v) for k, v in x.items()}
    return x

# ---------- fetch & parsing ----------

def fetch(url: str) -> tuple[str, bytes]:
    headers = {"User-Agent": UA}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=20.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return str(resp.url), resp.content

def _coerce_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]

def _as_text_list(maybe_list):
    out = []
    for x in _coerce_list(maybe_list):
        if isinstance(x, dict) and "text" in x:
            out.append(x["text"])
        else:
            out.append(str(x))
    return [s.strip() for s in out if s and str(s).strip()]


_ISO_DUR = re.compile(r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$")
_HUMAN_DUR = re.compile(r"(?:(\d+)\s*d(?:ays?)?\b)?\s*(?:(\d+)\s*h(?:ours?|rs?)?\b)?\s*(?:(\d+)\s*m(?:in(?:s|utes)?)?\b)?", re.I)

def _minutes(iso_like: str | None) -> int | None:
    if not iso_like:
        return None
    s = iso_like.strip()
    m = _ISO_DUR.match(s)
    if m:
        days = int(m.group("days") or 0)
        hours = int(m.group("hours") or 0)
        minutes = int(m.group("minutes") or 0)
        seconds = int(m.group("seconds") or 0)
        total = days * 1440 + hours * 60 + minutes + (seconds // 60)
        return total or None
    hm = _HUMAN_DUR.search(s)
    if hm:
        d, h, mi = [int(x or 0) for x in hm.groups()]
        total = d * 1440 + h * 60 + mi
        return total or None
    return None


def _iter_jsonld_objects(jsonld_list):
    """Yield all dict-like JSON-LD objects, flattening lists and @graph."""
    for block in jsonld_list:
        if isinstance(block, dict):
            yield block
            graph = block.get("@graph")
            if isinstance(graph, list):
                for item in graph:
                    if isinstance(item, dict):
                        yield item
        elif isinstance(block, list):
            for b in block:
                if isinstance(b, dict):
                    yield b
                    graph = b.get("@graph")
                    if isinstance(graph, list):
                        for item in graph:
                            if isinstance(item, dict):
                                yield item

def parse_structured(content: bytes, final_url: str):
    base = get_base_url(content.decode(errors="ignore"), final_url)
    data = extruct.extract(
        content,
        base_url=base,
        syntaxes=["json-ld", "microdata", "rdfa"],
        uniform=True,
    )
    # JSON-LD first
    for obj in _iter_jsonld_objects(data.get("json-ld", [])):
        t = obj.get("@type")
        if t == "Recipe" or (isinstance(t, list) and "Recipe" in t):
            return obj
    # microdata / RDFa fallbacks
    for syntax in ("microdata", "rdfa"):
        for item in data.get(syntax, []):
            types = item.get("@type") or []
            if "Recipe" in _coerce_list(types):
                return item
    return None

def _extract_instructions(instr):
    """Flatten various instruction formats (strings, HowToStep arrays, sections)."""
    steps = []

    def add_text(val):
        if val is None:
            return
        s = str(val).strip()
        if s:
            steps.append(s)

    if isinstance(instr, str):
        for line in instr.split("\n"):
            add_text(line)
        return [s for s in steps if s]

    if isinstance(instr, list):
        for it in instr:
            if isinstance(it, dict):
                # Handle HowToSection with itemListElement
                if "itemListElement" in it:
                    steps.extend(_extract_instructions(it["itemListElement"]))
                else:
                    add_text(it.get("text") or it.get("name"))
            else:
                add_text(it)
        return [s for s in steps if s]

    # Unknown shape
    return steps

def normalize_recipe(recipe_obj: dict, final_url: str):
    title = recipe_obj.get("name") or recipe_obj.get("headline") or "Untitled"
    desc = recipe_obj.get("description")

    # Images intentionally ignored for legal safety
    servings = str(recipe_obj.get("recipeYield") or "") or None
    ingredients = _as_text_list(
        recipe_obj.get("recipeIngredient") or recipe_obj.get("ingredients")
    )
    steps = _extract_instructions(recipe_obj.get("recipeInstructions"))

    recipe = {
        "title": title.strip(),
        "description": (desc or None),
        "servings": servings,
        "prep_time_min": _minutes(recipe_obj.get("prepTime")),
        "cook_time_min": _minutes(recipe_obj.get("cookTime")),
        "total_time_min": _minutes(recipe_obj.get("totalTime")),
        "image_url": None,  # always None
        "ingredients": [i for i in ingredients if i.strip()],
        "steps": [s for s in steps if s.strip()],
        "source_url": final_url,
        "source_host": urlparse(final_url).hostname,
        "extraction": "structured",
        "legal_note": LEGAL_NOTE,
    }
    return deep_clean(recipe)

def readability_fallback(content: bytes, final_url: str):
    # Readability expects text, not bytes
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1", errors="ignore")

    doc = Document(text)
    html_part = doc.summary(html_partial=True)
    tree = lxml_html.fromstring(html_part)
    title = (doc.short_title() or "Untitled").strip()

    tokens = [
        "cup", "cups", "tsp", "tbsp", "teaspoon", "tablespoon",
        "g", "gram", "kg", "ml", "l", "oz", "ounce", "lb",
    ]
    candidates = [li.text_content().strip() for li in tree.xpath("//li")]
    ingredients = [c for c in candidates if any(tok in c.lower() for tok in tokens)]
    steps = [
        p.text_content().strip()
        for p in tree.xpath("//p")
        if len(p.text_content().split()) > 5
    ]

    recipe = {
        "title": title,
        "description": None,
        "servings": None,
        "prep_time_min": None,
        "cook_time_min": None,
        "total_time_min": None,
        "image_url": None,  # always None
        "ingredients": ingredients[:50],
        "steps": steps[:50],
        "source_url": final_url,
        "source_host": urlparse(final_url).hostname,
        "extraction": "readability",
        "legal_note": LEGAL_NOTE,
    }
    return deep_clean(recipe)

def scrape(url: str) -> dict:
    final_url, content = fetch(url)
    data = parse_structured(content, final_url)
    return normalize_recipe(data, final_url) if data else readability_fallback(
        content, final_url
    )

def print_pretty(r: dict):
    def t(label, val):
        if val is None or (isinstance(val, str) and not val.strip()):
            return
        print(f"{label}: {val}")

    print("=" * 80)
    print(r["title"])
    print("=" * 80)
    print(f"Note: {LEGAL_NOTE}")
    t("Source", r["source_url"])
    t("Site", r["source_host"])
    t("Servings", r.get("servings"))
    t("Prep (min)", r.get("prep_time_min"))
    t("Cook (min)", r.get("cook_time_min"))
    t("Total (min)", r.get("total_time_min"))

    if r.get("description"):
        print("\nDescription:")
        print(textwrap.fill(r["description"], width=80))

    if r.get("ingredients"):
        print("\nIngredients:")
        for i in r["ingredients"]:
            print(f"  • {i}")

    if r.get("steps"):
        print("\nSteps:")
        for idx, s in enumerate(r["steps"], start=1):
            print(f"  {idx}. {s}")

    print(f"\n[extracted via: {r.get('extraction')}]")
    print()

def main():
    ap = argparse.ArgumentParser(
        description="Console recipe scraper (prints clean info)"
    )
    ap.add_argument("url", nargs="+", help="Recipe URL(s)")
    ap.add_argument(
        "--json", action="store_true", help="Output JSON instead of pretty text"
    )
    args = ap.parse_args()

    error = 0
    for u in args.url:
        try:
            rec = scrape(u)
            if args.json:
                sys.stdout.buffer.write(
                    orjson.dumps(rec, option=orjson.OPT_INDENT_2)
                )
                sys.stdout.write("\n")
            else:
                print_pretty(rec)
        except Exception as e:
            error = 1
            sys.stderr.write(f"[ERROR] {u}: {e}\n")

    sys.exit(error)

if __name__ == "__main__":
    main()
