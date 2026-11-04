#!/usr/bin/env python3
"""One-time import from the live Shopify store (www.gufino.com) into this repo.

Pulls:
  * data/shopify_products.json           – the store's public product feed
  * static/images/products/<handle>/N.ext – every product image
  * static/images/site/<file>             – logos and page images listed in data/catalog.json
  * data/policies/<handle>.html           – the four Shopify policy pages

Run it BEFORE the Shopify store is closed. Safe to re-run: existing images are skipped.
Usage: python tools/import_shopify.py [--force]
"""
import json
import os
import re
import sys
import time
import urllib.request

VERSION = "1.0.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = "https://www.gufino.com"
FILES_CDN = STORE + "/cdn/shop/files/"
UA = {"User-Agent": "Mozilla/5.0 (gufino-site-import)"}
FORCE = "--force" in sys.argv


def get(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if i == retries - 1:
                raise
            print(f"  retry {url}: {e}")
            time.sleep(2 * (i + 1))


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def ext_of(url):
    m = re.search(r"\.(jpe?g|png|webp|gif)(\?|$)", url, re.I)
    return (m.group(1).lower() if m else "jpg").replace("jpeg", "jpg")


def sized(url, width=1600):
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}width={width}"


def inner_div(html, class_name):
    """Return the inner HTML of the first <div> whose class contains class_name."""
    m = re.search(r'<div[^>]*class="[^"]*' + re.escape(class_name) + r'[^"]*"[^>]*>', html)
    if not m:
        return None
    start = m.end()
    depth = 1
    for tag in re.finditer(r"<(/?)div\b[^>]*>", html[start:], re.I):
        depth += -1 if tag.group(1) else 1
        if depth == 0:
            return html[start:start + tag.start()].strip()
    return None


def main():
    catalog = json.load(open(os.path.join(ROOT, "data", "catalog.json"), encoding="utf-8"))

    print("Products feed…")
    feed = json.loads(get(STORE + "/products.json?limit=250"))
    save(os.path.join(ROOT, "data", "shopify_products.json"),
         json.dumps(feed, indent=1, ensure_ascii=False).encode("utf-8"))
    print(f"  {len(feed['products'])} products")

    print("Product images…")
    count = 0
    for p in feed["products"]:
        for i, img in enumerate(p["images"], 1):
            dest = os.path.join(ROOT, "static", "images", "products", p["handle"], f"{i}.{ext_of(img['src'])}")
            if os.path.exists(dest) and not FORCE:
                continue
            save(dest, get(sized(img["src"])))
            count += 1
    print(f"  downloaded {count}")

    print("Site images…")
    for name in catalog["site_images"]:
        dest = os.path.join(ROOT, "static", "images", "site", name)
        if os.path.exists(dest) and not FORCE:
            continue
        save(dest, get(sized(FILES_CDN + name, 2000)))
        print(f"  {name}")

    print("Policies…")
    for pol in catalog["policies"]:
        html = get(f"{STORE}/policies/{pol['handle']}").decode("utf-8", "replace")
        body = inner_div(html, "shopify-policy__body")
        if not body:
            print(f"  WARNING: could not extract {pol['handle']}")
            continue
        body = re.sub(r"\s(class|style|data-[\w-]+)=\"[^\"]*\"", "", body)
        save(os.path.join(ROOT, "data", "policies", pol["handle"] + ".html"), body.encode("utf-8"))
        print(f"  {pol['handle']} ({len(body)} chars)")

    print("Import complete.")


if __name__ == "__main__":
    main()
