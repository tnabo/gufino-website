#!/usr/bin/env python3
"""Static site generator for www.gufino.com (GitHub Pages).

Inputs:  data/catalog.json, data/shopify_products.json, data/policies/*.html, static/
Output:  _site/
Usage:   python build.py
"""
import html
import json
import os
import re
import shutil
from html.parser import HTMLParser

VERSION = "1.0.0"
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "_site")
DATA = os.path.join(ROOT, "data")

catalog = json.load(open(os.path.join(DATA, "catalog.json"), encoding="utf-8"))
SITE = catalog["site"]
BASE = "https://" + SITE["domain"]
esc = html.escape


# ---------------------------------------------------------------- helpers
class Clean(HTMLParser):
    """Keep simple formatting tags from Shopify/Amazon description HTML, drop the rest."""
    KEEP = {"ul", "ol", "li", "p", "strong", "b", "em", "i", "h3", "h4", "br"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag in self.KEEP:
            tag = {"b": "strong", "i": "em", "h3": "h3", "h4": "h3"}.get(tag, tag)
            self.out.append(f"<{tag}>")

    def handle_endtag(self, tag):
        if tag in self.KEEP and tag != "br":
            tag = {"b": "strong", "i": "em", "h4": "h3"}.get(tag, tag)
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        self.out.append(esc(data))


def clean_html(raw):
    c = Clean()
    c.feed(raw or "")
    s = "".join(c.out)
    s = re.sub(r"<(p|strong|li|h3)>\s*</\1>", "", s)
    s = re.sub(r"<(p|strong|li|h3)>\s*</\1>", "", s)
    s = re.sub(r"\s*\n\s*", " ", s)
    return s.strip()


def plain(raw, n=160):
    t = re.sub(r"<[^>]+>", " ", raw or "")
    t = re.sub(r"\s+", " ", html.unescape(t)).strip()
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def ext_of(url):
    m = re.search(r"\.(jpe?g|png|webp|gif)(\?|$)", url, re.I)
    return (m.group(1).lower() if m else "jpg").replace("jpeg", "jpg")


def amazon(asin):
    return f"https://www.amazon.com/dp/{asin}"


def write(rel, content):
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def page_path(url):
    """'/products/x/' -> 'products/x/index.html'"""
    u = url.strip("/")
    return (u + "/index.html") if u else "index.html"


# ---------------------------------------------------------------- data
feed_path = os.path.join(DATA, "shopify_products.json")
if not os.path.exists(feed_path):
    raise SystemExit("data/shopify_products.json missing – run tools/import_shopify.py first.")
shop = {p["handle"]: p for p in json.load(open(feed_path, encoding="utf-8"))["products"]}


def images_for(handle):
    p = shop.get(handle)
    if not p:
        return []
    alt = p["title"]
    return [{"src": f"/images/products/{handle}/{i}.{ext_of(im['src'])}", "alt": im.get("alt") or alt}
            for i, im in enumerate(p["images"], 1)]


COLLECTIONS = {c["handle"]: c for c in catalog["collections"]}
PRODUCTS = []
for entry in catalog["products"]:
    variants = entry.get("variants")
    src_handle = variants[0]["source"] if variants else entry["handle"]
    sp = shop.get(src_handle)
    if not sp:
        print(f"WARNING: {src_handle} not in Shopify feed – skipped")
        continue
    prod = {
        "handle": entry["handle"],
        "title": entry.get("title") or sp["title"],
        "collection": entry["collection"],
        "body": clean_html(sp["body_html"]),
        "summary": plain(sp["body_html"]),
        "variants": [],
    }
    if variants:
        for v in variants:
            prod["variants"].append({
                "name": v["name"], "slug": re.sub(r"[^a-z0-9]+", "-", v["name"].lower()).strip("-"),
                "swatch": v["swatch"], "asin": v["asin"], "images": images_for(v["source"]),
            })
    else:
        prod["variants"].append({"name": None, "slug": "default", "swatch": None,
                                 "asin": entry["asin"], "images": images_for(entry["handle"])})
    prod["image"] = (prod["variants"][0]["images"] or [{"src": "/images/site/05_1.png", "alt": prod["title"]}])[0]
    PRODUCTS.append(prod)


# ---------------------------------------------------------------- layout
NAV = [("/pages/about-us/", "About Us"), ("/collections/all/", "Interactive Toys"),
       ("/pages/bilingual-resources/", "Free Resources"), ("/pages/collab/", "Collaborators"),
       ("/pages/contact/", "Contact")]

ICONS = {
    "Instagram": '<path d="M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zm0 8.2a3.2 3.2 0 1 1 0-6.4 3.2 3.2 0 0 1 0 6.4zM17.3 5.5a1.2 1.2 0 1 0 0 2.4 1.2 1.2 0 0 0 0-2.4zM12 2c-2.7 0-3 0-4.1.1C4.6 2.2 2.2 4.6 2.1 7.9 2 9 2 9.3 2 12s0 3 .1 4.1c.1 3.3 2.5 5.7 5.8 5.8 1.1.1 1.4.1 4.1.1s3 0 4.1-.1c3.3-.1 5.7-2.5 5.8-5.8.1-1.1.1-1.4.1-4.1s0-3-.1-4.1c-.1-3.3-2.5-5.7-5.8-5.8C15 2 14.7 2 12 2zm0 1.8c2.7 0 3 0 4 .1 2.3.1 3.9 1.7 4 4 .1 1 .1 1.4.1 4s0 3-.1 4c-.1 2.3-1.7 3.9-4 4-1 .1-1.4.1-4 .1s-3 0-4-.1c-2.3-.1-3.9-1.7-4-4-.1-1-.1-1.4-.1-4s0-3 .1-4c.1-2.3 1.7-3.9 4-4 1-.1 1.3-.1 4-.1z"/>',
    "TikTok": '<path d="M16.6 2h-3.3v13.4a2.9 2.9 0 1 1-2.9-2.9c.3 0 .6 0 .8.1V9.2a6.2 6.2 0 1 0 5.4 6.2V8.6a7.6 7.6 0 0 0 4.4 1.4V6.7a4.4 4.4 0 0 1-4.4-4.7z"/>',
    "Facebook": '<path d="M13.5 22v-8.2h2.8l.4-3.2h-3.2V8.5c0-.9.3-1.6 1.6-1.6h1.7V4.1c-.3 0-1.3-.1-2.5-.1-2.5 0-4.2 1.5-4.2 4.3v2.3H7.3v3.2h2.8V22h3.4z"/>',
    "Pinterest": '<path d="M12 2a10 10 0 0 0-3.6 19.3c-.1-.8-.2-2 0-2.9l1.2-5s-.3-.6-.3-1.5c0-1.4.8-2.4 1.8-2.4.9 0 1.3.6 1.3 1.4 0 .9-.5 2.1-.8 3.3-.2 1 .5 1.8 1.5 1.8 1.8 0 3.1-1.9 3.1-4.6 0-2.4-1.7-4.1-4.2-4.1-2.9 0-4.5 2.1-4.5 4.4 0 .9.3 1.8.8 2.3.1.1.1.2.1.3l-.3 1.2c0 .2-.2.2-.4.1-1.3-.6-2.1-2.5-2.1-4 0-3.3 2.4-6.3 6.9-6.3 3.6 0 6.4 2.6 6.4 6 0 3.6-2.3 6.5-5.4 6.5-1.1 0-2.1-.6-2.4-1.2l-.7 2.5c-.2.9-.9 2.1-1.3 2.8A10 10 0 1 0 12 2z"/>',
    "YouTube": '<path d="M21.6 7.2a2.5 2.5 0 0 0-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4a2.5 2.5 0 0 0-1.8 1.8C2 8.8 2 12 2 12s0 3.2.4 4.8a2.5 2.5 0 0 0 1.8 1.8c1.6.4 7.8.4 7.8.4s6.2 0 7.8-.4a2.5 2.5 0 0 0 1.8-1.8c.4-1.6.4-4.8.4-4.8s0-3.2-.4-4.8zM10 15V9l5.2 3L10 15z"/>',
}


def social_links(cls="social"):
    return f'<div class="{cls}">' + "".join(
        f'<a href="{u}" target="_blank" rel="noopener" aria-label="{n}"><svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[n]}</svg></a>'
        for n, u in SITE["social"].items()) + "</div>"


def layout(url, title, description, body, image=None, extra_head="", canonical=True):
    full_title = title if title == SITE["home_title"] else f"{title} – {SITE['name']}"
    og_image = BASE + (image or "/images/site/Gufino-AltColor-w2000-trans.png")
    nav = "".join(f'<a href="{h}"{" aria-current=page" if url.startswith(h) else ""}>{t}</a>' for h, t in NAV)
    canon = f'<link rel="canonical" href="{BASE}{url}">' if canonical else ""
    year = "2026"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(description)}">
{canon}
<meta property="og:site_name" content="{esc(SITE['name'])}">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{BASE}{url}">
<meta property="og:image" content="{og_image}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/images/site/05_1.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css?v={VERSION}">
{extra_head}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <div class="wrap header-row">
    <a class="logo" href="/"><img src="/images/site/Gufino-AltColor-w2000-trans.png" alt="Gufino Bilingual Learning" width="160" height="56"></a>
    <button class="menu-btn" aria-expanded="false" aria-controls="nav" aria-label="Menu"><span></span><span></span><span></span></button>
    <nav id="nav" class="nav">{nav}<a class="btn btn-sm nav-cta" href="/collections/all/">Shop toys</a></nav>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-footer">
  <div class="wrap footer-grid">
    <div>
      <img class="footer-logo" src="/images/site/GUFINO_FULL_COLOR_-_TRANS_1_1.png" alt="Gufino" width="150" height="52" loading="lazy">
      <p>Bilingual Spanish–English learning toys, designed with educators for curious little minds.</p>
      {social_links()}
    </div>
    <div>
      <h3>Shop</h3>
      <a href="/collections/all/">All toys</a>
      {"".join(f'<a href="/collections/{c["handle"]}/">{esc(c["title"])}</a>' for c in catalog["collections"])}
    </div>
    <div>
      <h3>Company</h3>
      <a href="/pages/about-us/">About Us</a>
      <a href="/pages/contact/">Contact Us</a>
      <a href="/pages/faqs/">FAQs</a>
      <a href="/pages/collab/">Collaborators</a>
      <a href="/pages/bilingual-resources/">Free Resources</a>
    </div>
    <div>
      <h3>Policies</h3>
      {"".join(f'<a href="/policies/{p["handle"]}/">{esc(p["title"])}</a>' for p in catalog["policies"])}
    </div>
  </div>
  <div class="wrap footer-base">© {year} {esc(SITE['name'])} · <a href="mailto:{SITE['email']}">{SITE['email']}</a></div>
</footer>
<script src="/assets/site.js?v={VERSION}" defer></script>
</body>
</html>
"""


AMZ_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true" class="amz"><path d="M3 16.5c4.6 2.9 11.4 3.6 17.5.5.4-.2.8.3.4.6-4.8 3.8-12.6 4-17.9-.5-.3-.3 0-.8 0-.6zM20.9 15.2c-.4-.5-2.4-.3-3.4-.1-.3 0-.3-.2-.1-.4 1.6-1.1 4.2-.8 4.5-.4.3.4-.1 3-1.6 4.2-.2.2-.4.1-.3-.2.3-.8 1.1-2.6.9-3.1z"/></svg>'


def card(p):
    v = p["variants"][0]
    sw = ""
    if v["name"]:
        sw = '<div class="card-swatches">' + "".join(
            f'<span style="background:{x["swatch"]}" title="{esc(x["name"])}"></span>' for x in p["variants"]) + "</div>"
    return f"""<article class="card">
  <a class="card-img" href="/products/{p['handle']}/"><img src="{p['image']['src']}" alt="{esc(p['image']['alt'])}" loading="lazy" width="600" height="600"></a>
  <div class="card-body">
    <span class="eyebrow">{esc(COLLECTIONS[p['collection']]['title'])}</span>
    <h3><a href="/products/{p['handle']}/">{esc(p['title'])}</a></h3>
    {sw}
    <div class="card-actions">
      <a class="btn btn-amz" href="{amazon(v['asin'])}" target="_blank" rel="noopener">{AMZ_ICON}Buy on Amazon</a>
      <a class="link" href="/products/{p['handle']}/">Details</a>
    </div>
  </div>
</article>"""


def grid(products):
    return '<div class="grid">' + "".join(card(p) for p in products) + "</div>"


def hero_band(kicker, title, sub=""):
    return f"""<section class="band"><div class="wrap">
<span class="kicker">{kicker}</span><h1>{title}</h1>{f'<p class="lede">{sub}</p>' if sub else ''}
</div></section>"""


# ---------------------------------------------------------------- pages
def build_home():
    feat = [p for p in PRODUCTS][:3]
    tiles = "".join(
        f"""<a class="tile" href="/collections/{c['handle']}/">
<img src="{next((p['image']['src'] for p in PRODUCTS if p['collection']==c['handle']), '')}" alt="" loading="lazy" width="400" height="400">
<span>{esc(c['title'])}</span></a>""" for c in catalog["collections"])
    body = f"""
<section class="hero">
  <div class="wrap hero-grid">
    <div class="hero-copy">
      <span class="kicker">English · Español</span>
      <h1>Bilingual Learning Made Fun</h1>
      <p class="lede">Innovative resources designed to enrich your child's future.</p>
      <div class="hero-actions">
        <a class="btn" href="/collections/all/">Shop Now</a>
        <a class="btn btn-ghost" href="/pages/about-us/">Our story</a>
      </div>
    </div>
    <div class="hero-art">
      {"".join(f'<img class="h{i}" src="{p["image"]["src"]}" alt="{esc(p["title"])}" width="400" height="400">' for i, p in enumerate(feat))}
    </div>
  </div>
</section>

<section class="section"><div class="wrap">
  <div class="section-head"><h2>Shop by category</h2></div>
  <div class="tiles">{tiles}</div>
</div></section>

<section class="section alt"><div class="wrap">
  <div class="section-head"><h2>Best Sellers</h2><a class="link" href="/collections/all/">See all</a></div>
  {grid(PRODUCTS)}
</div></section>

<section class="section"><div class="wrap perks">
  <div><h3>Fast shipping with Amazon</h3><p>Every order ships through Amazon, Prime-eligible where available.</p></div>
  <div><h3>Easy returns</h3><p>Hassle-free returns handled by Amazon.</p></div>
  <div><h3>Affordable quality</h3><p>Highest quality with affordable prices.</p></div>
</div></section>

<section class="section alt"><div class="wrap story">
  <img src="/images/site/ImageForWeb.jpg" alt="Child learning with Gufino bilingual toys" loading="lazy" width="700" height="520">
  <div>
    <span class="kicker">Owl Story</span>
    <h2>Who are we?</h2>
    <p>Founded by two families who dreamed of raising bilingual children, GUFINO was born out of the desire to fill a gap in bilingual educational resources. Partnering with experts in language development and professional translators, we have crafted engaging bilingual educational toys that ignite curiosity, nurture cognitive growth, and hone fine motor skills.</p>
    <p>Our products are thoughtfully designed to meet American educational standards, providing playful learning experiences that prepare young minds for second-language success.</p>
    <a class="btn btn-ghost" href="/pages/about-us/">About us</a>
  </div>
</div></section>

<section class="section"><div class="wrap join">
  <h2>Join the Gufino family!</h2>
  <p>Follow us to stay updated on all things GUFINO: new products, free resources, promotions and playful contests.</p>
  {social_links("social social-lg")}
</div></section>
"""
    write("index.html", layout("/", SITE["home_title"], SITE["home_description"], body,
                               extra_head='<meta name="facebook-domain-verification" content="r7umecawhemddj7o4ovftkhh6sty89">\n'
                                          '<meta name="google-site-verification" content="YJUXCSzQbQiOBCHtgj3ZfAKYy3h9bvGQfHijxfbCV4o">\n'
                                          '<meta name="p:domain_verify" content="217e9d4aef705ada3d32b9c9091fae8f">'))


def build_collections():
    chips = '<div class="chips"><a href="/collections/all/" class="chip{a}">All</a>{rest}</div>'

    def chipbar(active):
        rest = "".join(f'<a href="/collections/{c["handle"]}/" class="chip{" on" if c["handle"]==active else ""}">{esc(c["title"])}</a>'
                       for c in catalog["collections"])
        return chips.format(a=" on" if active == "all" else "", rest=rest)

    body = hero_band("Interactive Toys", "All bilingual toys", "Every Gufino toy speaks English and Spanish. Buy securely on Amazon.") + \
        f'<section class="section"><div class="wrap">{chipbar("all")}{grid(PRODUCTS)}</div></section>'
    write(page_path("/collections/all/"), layout("/collections/all/", "Interactive Toys", "All Gufino bilingual Spanish-English learning toys.", body))

    for c in catalog["collections"]:
        items = [p for p in PRODUCTS if p["collection"] == c["handle"]]
        url = f"/collections/{c['handle']}/"
        body = hero_band("Interactive Toys", esc(c["title"]), esc(c["blurb"])) + \
            f'<section class="section"><div class="wrap">{chipbar(c["handle"])}{grid(items)}</div></section>'
        write(page_path(url), layout(url, c["title"], c["blurb"], body))


def build_products():
    for p in PRODUCTS:
        url = f"/products/{p['handle']}/"
        coll = COLLECTIONS[p["collection"]]
        galleries, swatches = [], []
        for i, v in enumerate(p["variants"]):
            imgs = v["images"] or [p["image"]]
            thumbs = "".join(
                f'<button class="thumb{" on" if j==0 else ""}" data-src="{im["src"]}" aria-label="Image {j+1}"><img src="{im["src"]}" alt="" loading="lazy" width="80" height="80"></button>'
                for j, im in enumerate(imgs))
            galleries.append(f"""<div class="gallery" data-variant="{v['slug']}" data-asin="{v['asin']}"{'' if i==0 else ' hidden'}>
  <div class="gallery-main"><img src="{imgs[0]['src']}" alt="{esc(imgs[0]['alt'])}" width="800" height="800"{' fetchpriority="high"' if i==0 else ' loading="lazy"'}></div>
  <div class="thumbs">{thumbs}</div>
</div>""")
            if v["name"]:
                swatches.append(f'<button class="swatch{" on" if i==0 else ""}" data-variant="{v["slug"]}" aria-pressed="{"true" if i==0 else "false"}"><span style="background:{v["swatch"]}"></span>{esc(v["name"])}</button>')
        v0 = p["variants"][0]
        swatch_html = f'<div class="swatches" role="group" aria-label="Color"><span class="label">Color</span>{"".join(swatches)}</div>' if swatches else ""
        related = [x for x in PRODUCTS if x["collection"] == p["collection"] and x["handle"] != p["handle"]][:3] or \
                  [x for x in PRODUCTS if x["handle"] != p["handle"]][:3]
        ld = {"@context": "https://schema.org", "@type": "Product", "name": p["title"], "brand": {"@type": "Brand", "name": "GUFINO"},
              "description": p["summary"], "image": [BASE + p["image"]["src"]], "url": BASE + url}
        body = f"""
<div class="wrap crumbs"><a href="/">Home</a> / <a href="/collections/{coll['handle']}/">{esc(coll['title'])}</a></div>
<section class="wrap product">
  <div class="product-media">{"".join(galleries)}</div>
  <div class="product-info">
    <span class="eyebrow">{esc(coll['title'])}</span>
    <h1>{esc(p['title'])}</h1>
    {swatch_html}
    <a class="btn btn-amz btn-lg" id="buy" href="{amazon(v0['asin'])}" target="_blank" rel="noopener">{AMZ_ICON}Buy on Amazon</a>
    <p class="note">Sold and shipped through Amazon. Prices and availability are shown on Amazon.</p>
    <div class="desc">{p['body']}</div>
  </div>
</section>
<section class="section alt"><div class="wrap">
  <div class="section-head"><h2>You may also like</h2></div>
  {grid(related)}
</div></section>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
"""
        write(page_path(url), layout(url, p["title"], p["summary"], body, image=p["image"]["src"]))


def simple_page(url, title, description, inner, kicker=""):
    body = hero_band(kicker or SITE["name"], esc(title)) + f'<section class="section"><div class="wrap prose">{inner}</div></section>'
    write(page_path(url), layout(url, title, description, body))


def build_pages():
    simple_page("/pages/about-us/", "About Us", "Gufino's vision: high-quality bilingual resources for every American family.", f"""
<div class="split">
  <div>
    <h2>Our vision</h2>
    <p>At GUFINO, our vision is to empower every American family with high-quality bilingual resources that help their children thrive. Inspired by the success of our own children, we create educational products that spark curiosity, foster growth, and make learning through play a joyful experience. We believe every family deserves access to the tools that nurture their children's potential, and we're committed to making this vision a reality.</p>
  </div>
  <img src="/images/site/02c.jpg" alt="Gufino bilingual learning toys" loading="lazy" width="600" height="600">
</div>
<div class="split rev">
  <img src="/images/site/3-ALPHABETPOSTER.jpg" alt="Gufino bilingual alphabet poster" loading="lazy" width="600" height="600">
  <div>
    <h2>Not your typical educational toys…</h2>
    <p>Introducing a second language during a child's early years is crucial, as it enhances cognitive development, improves problem-solving skills, and increases creativity. At GUFINO, our bilingual educational toys not only help children learn a second language but also improve fine motor skills, teach numbers, promote self-awareness, and explore various topics. We design our products following federal educational standards, ensuring kids receive the best resources to learn while having fun. With GUFINO, playful learning opens the door to endless possibilities!</p>
    <a class="btn" href="/collections/all/">Explore our toys</a>
  </div>
</div>""", kicker="Owl Story")

    simple_page("/pages/bilingual-resources/", "Free Resources", "Free bilingual printables, videos and guides for parents and educators.", f"""
<p class="badge">Coming soon…</p>
<p>Welcome to our Free Resources page! Here, you'll find a wide range of free printables, videos, images, blogs, and interviews designed to support parents and educators in bilingual education. We are constantly adding new resources, and you won't want to miss any!</p>
<p>Follow us on social media to be the first to know when new resources are available.</p>
{social_links("social social-lg")}""", kicker="Bilingual Resources")

    simple_page("/pages/collab/", "Collaborator Program", "Partner with Gufino as an influencer or creator.", f"""
<p class="lede">We're looking for passionate influencers and creators for a partnership that promises mutual growth and an enhanced community impact.</p>
<div class="split">
  <div>
    <h2>GUFINO's mission</h2>
    <p>At GUFINO, our vision is to empower every American family with high-quality bilingual resources that help their children thrive. We create educational products that spark curiosity, foster growth, and make learning through play a joyful experience. We believe every family deserves access to the tools that nurture their children's potential, and we're committed to making this vision a reality.</p>
    <h2>Why partner with us?</h2>
    <ul class="checks">
      <li>Help children start their bilingual journey</li>
      <li>Get free top quality products on a frequent basis</li>
      <li>Develop your influencer/creator portfolio</li>
      <li>Commission based &amp; paid collaborations</li>
      <li>Be the first to test and enjoy our newest products</li>
    </ul>
    <a class="btn" href="{SITE['collab_form']}" target="_blank" rel="noopener">Sign up to the Collaborator Program</a>
    <p class="small">By registering, you grant G5M LLC unrestricted permission to use any and all content produced in connection with this collaboration program, related to the promotion of GUFINO's trademarked products and its social media outreach.</p>
  </div>
  <img src="/images/site/2024-03-05_165615.jpg" alt="Gufino collaborators" loading="lazy" width="600" height="600">
</div>""", kicker="Collaborators")

    simple_page("/pages/contact/", "Contact", "Get in touch with Gufino Bilingual Learning.", f"""
<h2>Have a question?</h2>
<p>We'd love to hear from you. Email us and our bilingual team will get back to you. <em>¡Hablamos español!</em></p>
<p><a class="btn" href="mailto:{SITE['email']}">Email {SITE['email']}</a></p>
<p>For orders placed on Amazon, you can also contact us through your Amazon order page.</p>
{social_links("social social-lg")}""", kicker="Contact Us")

    faqs = [
        ("How long does it take to get my products?",
         "<p>Orders are fulfilled by Amazon. Domestic shipping can take up to 5 business days; foreign shipping could take up to 14 business days. Due to global supply chain challenges, shipping times could be longer than usual.</p>"),
        ("Do you offer warranty for your products?",
         "<p>All our products are subject to quality control. Our warranty provides a guarantee against manufacturer defects. The guarantee covers any manufacturing, design, or material defect. Please notify us within 2 months of noticing any defects. It does not cover blows, improper use, or other issues that are not attributable to manufacturer defects.</p>"),
        ("Do you offer refunds?",
         f"<p>Yes, we offer full and partial refunds. Returns for Amazon orders can be started from your Amazon order page. See our <a href=\"/policies/refund-policy/\">Refund Policy</a> or email <a href=\"mailto:{SITE['email']}\">{SITE['email']}</a>.</p>"),
        ("What shipping methods do you offer?",
         "<p>Orders ship through Amazon using all major carriers and local courier partners. Shipping options and rates are shown at Amazon checkout.</p>"),
    ]
    inner = '<div class="faq">' + "".join(f"<details><summary>{esc(q)}</summary>{a}</details>" for q, a in faqs) + "</div>"
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": plain(a, 1000)}} for q, a in faqs]}
    inner += f'<script type="application/ld+json">{json.dumps(ld)}</script>'
    simple_page("/pages/faqs/", "Frequently Asked Questions", "Shipping, warranty and refund answers from Gufino.", inner, kicker="FAQs")


def build_policies():
    for pol in catalog["policies"]:
        src = os.path.join(DATA, "policies", pol["handle"] + ".html")
        if os.path.exists(src):
            inner = open(src, encoding="utf-8").read()
        else:
            inner = f'<p>This policy is being updated. Please contact <a href="mailto:{SITE["email"]}">{SITE["email"]}</a>.</p>'
        simple_page(f"/policies/{pol['handle']}/", pol["title"], f"Gufino {pol['title']}.", inner, kicker="Policies")


def build_redirects():
    for old, new in catalog["redirects"].items():
        target = new if new.startswith("http") else BASE + new
        write(page_path("/" + old + "/"), f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Redirecting…</title><link rel="canonical" href="{target}"><meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={new}"><script>location.replace({json.dumps(new)})</script>
</head><body><a href="{new}">Continue</a></body></html>""")


def build_misc():
    body = hero_band("404", "Page not found", "That page has moved. Our toys haven't!") + \
        f'<section class="section"><div class="wrap">{grid(PRODUCTS[:3])}<p class="center"><a class="btn" href="/collections/all/">See all toys</a></p></div></section>'
    write("404.html", layout("/404.html", "Page not found", "Page not found", body, canonical=False))
    write("CNAME", SITE["domain"] + "\n")
    write(".nojekyll", "")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    urls = ["/", "/collections/all/"] + [f"/collections/{c['handle']}/" for c in catalog["collections"]] + \
        [f"/products/{p['handle']}/" for p in PRODUCTS] + \
        [f"/pages/{x}/" for x in ("about-us", "bilingual-resources", "collab", "contact", "faqs")] + \
        [f"/policies/{p['handle']}/" for p in catalog["policies"]]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "".join(f"  <url><loc>{BASE}{u}</loc></url>\n" for u in urls) + "</urlset>\n")


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(os.path.join(ROOT, "static"), OUT)
    build_home()
    build_collections()
    build_products()
    build_pages()
    build_policies()
    build_redirects()
    build_misc()
    n = sum(len(f) for _, _, f in os.walk(OUT))
    print(f"Built {len(PRODUCTS)} products, {n} files -> _site/ (build.py v{VERSION})")


if __name__ == "__main__":
    main()
