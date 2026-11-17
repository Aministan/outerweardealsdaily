#!/usr/bin/env python3
"""Render site/ from data/links.json.

SITE_URL is the origin (https://outerweardealsdaily.com).
PATH_PREFIX is empty on that domain. Set it only for a project-site path such as /outerweardealsdaily.
"""
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import images
import links

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data" / "links.json").read_text())
OUT = ROOT / "site"
SITE_URL = os.environ.get("SITE_URL", "https://outerweardealsdaily.com").rstrip("/")
PREFIX = os.environ.get("PATH_PREFIX", "").rstrip("/")
NAME = DATA["site"]["name"]
OWNER = DATA["site"]["owner"]
CHECKED = DATA["site"]["price_checked"]
PRODUCTS = DATA["products"]
MERCHANTS = DATA["merchants"]
PAGES = []

BANNED = (
    "anrdoezrs.net", "jdoqocy.com", "tkqlhce.com", "dpbolvw.net", "kqzyfj.com",
    "emjcd.com", "awin1.com", "linksynergy.com", "amazon.", "ebay.", "walmart.",
    "nordstrom", "sephora.",
)


def e(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def money(value):
    return f"${value:,.2f}"


def href(path):
    path = path.strip("/")
    if not path:
        return PREFIX + "/" if PREFIX else "/"
    return f"{PREFIX}/{path}/"


def absolute(path):
    return SITE_URL + href(path)


def merchant(product):
    return MERCHANTS[product["merchant"]]


def priced(product):
    price = product.get("price")
    return isinstance(price, (int, float)) and not isinstance(price, bool)


def compare(product):
    was = product.get("compare_at")
    if not priced(product) or not isinstance(was, (int, float)) or isinstance(was, bool):
        return None
    if was <= product["price"]:
        return None
    return was


def outbound(product, pagetype, pageslug, placement):
    sid = links.make_sid(pagetype, pageslug, placement, product=product["slug"])
    url = links.affiliate_url(product["url"], merchant(product).get("deep_link"), sid)
    sponsored = bool(merchant(product).get("deep_link"))
    rel = "nofollow sponsored noopener" if sponsored else "noopener"
    return url, sid, rel


def button(product, pagetype, pageslug, placement, cls="btn"):
    url, sid, rel = outbound(product, pagetype, pageslug, placement)
    label = f"Buy at {merchant(product)['name']}" if priced(product) else "Check today's price"
    if placement == "cta":
        label += " →"
    return (
        f'<a class="{cls}" rel="{rel}" target="_blank" data-sid="{e(sid)}" href="{e(url)}">{e(label)}</a>'
    )


def text_link(product, pagetype, pageslug, placement, label=None):
    url, sid, rel = outbound(product, pagetype, pageslug, placement)
    label = label or merchant(product)["name"]
    return f'<a rel="{rel}" target="_blank" data-sid="{e(sid)}" href="{e(url)}">{e(label)}</a>'


def deal_path(product):
    kind = "jacket" if product["category"] == "jacket" else "boot"
    return f"{kind}/{product['slug']}"


_JPEG_SIZE = {}


def for_sale(product):
    """False only when the merchant page said the item was out of stock."""
    return product.get("in_stock") is not False


def image_file(product):
    src = product.get("image") or ""
    if not src or src.startswith(("http://", "https://")):
        return None
    path = ROOT / src.lstrip("/")
    return path if path.is_file() else None


def image_src(product):
    path = image_file(product)
    if path is None:
        return ""
    rel = "/" + str(path.relative_to(ROOT)).replace("\\", "/")
    return f"{PREFIX}{rel}" if PREFIX else rel


def jpeg_size(path):
    key = str(path)
    if key in _JPEG_SIZE:
        return _JPEG_SIZE[key]
    width, height = 600, 600
    try:
        data = path.read_bytes()
    except OSError:
        data = b""
    sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in sof:
                height = int.from_bytes(data[i + 5:i + 7], "big")
                width = int.from_bytes(data[i + 7:i + 9], "big")
                break
            if marker in (0xD8, 0xD9, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            length = int.from_bytes(data[i + 2:i + 4], "big")
            if length < 2:
                break
            i += 2 + length
    _JPEG_SIZE[key] = (width, height)
    return width, height


def img_tag(product, eager=False):
    src = image_src(product)
    path = image_file(product)
    if not src or path is None:
        return ""
    alt = product["name"]
    width, height = jpeg_size(path)
    extra = 'fetchpriority="high"' if eager else 'loading="lazy"'
    return f'<img {extra} decoding="async" src="{e(src)}" alt="{e(alt)}" width="{width}" height="{height}">'


def thumb_tag(product):
    """72px photo for a price-table row. Same file the product card already uses."""
    src = image_src(product)
    if not src:
        return ""
    alt = product["name"]
    return (
        f'<img class="thumb" loading="lazy" decoding="async" src="{e(src)}" alt="{e(alt)}" width="72" height="72">'
    )


CSS = """
:root{--ink:#1c1915;--muted:#5e584f;--line:#e4ddd2;--paper:#f7f3ec;--card:#fff;--accent:#9a3412;--accent-ink:#fff;--good:#14532d}
*{box-sizing:border-box}
body{margin:0;font:17px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--paper)}
a{color:#9a3412}
header{display:flex;flex-wrap:wrap;gap:12px 28px;align-items:baseline;padding:16px 22px;background:#1c1915;color:#f7f3ec}
.logo{font-weight:700;font-size:22px;color:#f7f3ec;text-decoration:none;letter-spacing:-.02em}
.logo span{color:#fdba74}
nav{display:flex;flex-wrap:wrap;gap:14px}
nav a{color:#f7f3ec;text-decoration:none;font:15px/1.2 system-ui,sans-serif}
main{max-width:1040px;margin:0 auto;padding:22px}
h1{font-size:34px;line-height:1.15;margin:0 0 8px}
h2{font-size:24px;margin:28px 0 10px}
.sub,.meta{color:var(--muted);font:15px/1.45 system-ui,sans-serif}
.crumbs{font:13px/1.4 system-ui,sans-serif;color:var(--muted);margin:0 0 8px}
.crumbs a{color:var(--muted)}
.lead-offer{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 16px;margin:0 0 16px;position:sticky;top:0;z-index:20;box-shadow:0 2px 12px rgba(28,25,21,.08)}
.lead-offer .btn{max-width:360px}
.price{font-size:28px;font-weight:700}
.was{color:var(--muted);text-decoration:line-through;margin-left:8px;font-size:18px}
.badge{display:inline-block;background:#ffedd5;color:#9a3412;border-radius:999px;padding:2px 8px;font:13px system-ui,sans-serif;margin-left:8px}
.btn{display:inline-block;background:var(--accent);color:var(--accent-ink);text-decoration:none;font:700 16px/1.2 system-ui,sans-serif;padding:12px 16px;border-radius:10px;margin-top:8px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;display:flex;flex-direction:column}
.card img{width:100%;aspect-ratio:1/1;height:auto;object-fit:contain;background:#fff;border-radius:10px;display:block}
.hero img{width:min(100%,320px);aspect-ratio:1/1;height:auto;object-fit:contain;background:#fff;border-radius:10px;display:block}
.card .nm{font-weight:700;margin-top:8px}
.card .nm a{color:inherit;text-decoration:none}
.hero{display:flex;gap:18px;flex-wrap:wrap;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px}
.specs{flex:1;min-width:240px}
table{width:100%;border-collapse:collapse;font:15px/1.4 system-ui,sans-serif}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
table.prices{border-collapse:separate;border-spacing:0}
table.prices th.photo,table.prices td.photo{position:sticky;left:0;width:84px;background:var(--paper);z-index:1;vertical-align:top}
table.prices img.thumb{width:72px;height:72px;max-width:72px;object-fit:contain;background:#fff;border-radius:8px;display:block}
table.prices .btn{white-space:nowrap;margin-top:4px}
.box{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 16px;margin:16px 0}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chips a{background:#fff;border:1px solid var(--line);border-radius:999px;padding:6px 10px;text-decoration:none;font:14px system-ui,sans-serif}
footer{padding:22px;color:#d6d3d1;background:#1c1915;font:14px/1.5 system-ui,sans-serif}
footer a{color:#fdba74}
.note{font:14px/1.45 system-ui,sans-serif;color:var(--muted)}
@media(max-width:640px){
 h1{font-size:26px}header{padding:12px}.lead-offer{padding:10px 12px}th,td{padding:8px 8px}
 .scroll{overflow:visible}
 table.prices thead{display:none}
 table.prices,table.prices tbody,table.prices tr{display:block;width:100%}
 table.prices tr{background:#fff;border:1px solid var(--line);border-radius:14px;margin:0 0 12px;padding:12px}
 table.prices td{display:grid;grid-template-columns:7.25rem minmax(0,1fr);gap:8px;align-items:center;border:0;padding:5px 0;width:auto}
 table.prices td::before{content:attr(data-label);font-weight:700;color:var(--muted)}
 table.prices td.photo{display:block;position:static;width:auto;background:transparent;padding:0 0 8px}
 table.prices td.photo::before{content:none}
 table.prices img.thumb{width:72px;height:72px;max-width:72px}
 table.prices .btn{white-space:normal}
}
"""


def page(path, title, desc, body, jsonld=None, index=True):
    url = absolute(path.replace("/index.html", "").replace("index.html", ""))
    if path.endswith("index.html") and path != "index.html":
        url = absolute(path[: -len("index.html")])
    elif path == "index.html":
        url = absolute("")
    ld = "".join(
        f'<script type="application/ld+json">{json.dumps(block, ensure_ascii=False)}</script>'
        for block in (jsonld or [])
    )
    robots = "" if index else '<meta name="robots" content="noindex">'
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{robots}<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}"><link rel="stylesheet" href="{e(href('style.css')[:-1] if False else PREFIX + '/style.css')}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{e(NAME)}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">{ld}</head><body>
<header><a class="logo" href="{href('')}">Outerwear<span>Deals</span>Daily</a>
<nav><a href="{href('')}">Deals</a><a href="{href('jackets')}">Jackets</a><a href="{href('boots')}">Boots</a>
<a href="{href('best')}">Best of</a><a href="{href('gifts')}">Gifts</a><a href="{href('black-friday-outerwear-boot-deals')}">Black Friday</a>
<a href="{href('brands')}">Brands</a></nav></header>
<main>{body}</main>
<footer><p><b>Affiliate disclosure:</b> {e(OWNER)} runs {NAME}. Applications to Columbia, Sorel, Canada Goose, Hunter, Dr. Martens, Thursday Boot Company, and Frye on CJ are pending. Until a program is approved, buttons go to the merchant's own product page with no tracking. We may earn a commission later, at no extra cost to you. <a href="{href('disclosure')}">Full disclosure</a>.</p>
<p>Prices shown were read from the merchant page on {CHECKED}. Where no number was on the page, the button says Check today's price. We do not invent prices, ratings, or test scores.</p>
<p>© {CHECKED[:4]} {NAME} · <a href="{href('about')}">About</a> · <a href="{href('privacy')}">Privacy</a> · <a href="{href('sitemap.xml')[:-1] if False else PREFIX + '/sitemap.xml'}">Sitemap</a></p>
</footer></body></html>"""
    # stylesheet and sitemap links should not grow a trailing slash from href()
    doc = doc.replace(PREFIX + "/style.css", (PREFIX + "/style.css") if PREFIX else "/style.css")
    fp = OUT / path
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(doc)
    if index:
        PAGES.append(url if path != "index.html" else absolute(""))


def crumbs(items):
    bits = [f'<a href="{href("")}">Home</a>']
    for label, path in items[:-1]:
        bits.append(f'<a href="{href(path)}">{e(label)}</a>')
    bits.append(f'<span aria-current="page">{e(items[-1][0])}</span>')
    return '<nav class="crumbs" aria-label="Breadcrumb">' + '<span class="sep"> / </span>'.join(bits) + "</nav>"


def lead(product, pagetype, pageslug):
    if priced(product):
        was = compare(product)
        was_html = f'<span class="was">{money(was)}</span>' if was else ""
        save = ""
        if was:
            off = round((1 - product["price"] / was) * 100)
            save = f'<span class="badge">-{off}% vs listed original</span>'
        price_html = f'<span class="price">{money(product["price"])}</span>{was_html}{save}'
        when = f'Price read from the merchant page on {CHECKED}'
    else:
        price_html = '<span class="price">Check today\'s price</span>'
        when = "No price was on the merchant page we read, so we are not printing one"
    stock = ""
    if product.get("in_stock") is False:
        stock = '<p class="meta">The product page said out of stock on the day we read it.</p>'
    return (
        f'<div class="lead-offer"><p class="meta">{e(when)}</p>'
        f'<p class="lead-name"><b>{e(product["name"])}</b></p>'
        f'<p class="lead-price">{price_html} <span class="meta">at {e(merchant(product)["name"])}</span></p>'
        f"{stock}{button(product, pagetype, pageslug, 'cta')}</div>"
    )


def card(product, pagetype, pageslug):
    photo = img_tag(product)
    if not photo:
        return ""
    price = money(product["price"]) if priced(product) else "Check today's price"
    was = compare(product)
    was_html = f'<span class="was">{money(was)}</span>' if was else ""
    return (
        f'<article class="card">{photo}'
        f'<div class="meta">{e(product["brand"])}</div>'
        f'<div class="nm"><a href="{href(deal_path(product))}">{e(product["name"])}</a></div>'
        f'<div><span class="price" style="font-size:20px">{price}</span>{was_html}</div>'
        f'{button(product, pagetype, pageslug, "grid")}</article>'
    )


def related(product, limit=4):
    rows = [
        other for other in PRODUCTS.values()
        if other["slug"] != product["slug"] and (
            other["brand"] == product["brand"] or other["family"] == product["family"]
        )
    ]
    rows.sort(key=lambda row: (row.get("in_stock") is False, row["family"] != product["family"], row["brand"] != product["brand"], row["name"]))
    return rows[:limit]


def product_ld(product):
    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product["name"],
        "brand": {"@type": "Brand", "name": product["brand"]},
        "description": product["summary"],
        "url": absolute(deal_path(product)),
    }
    src = image_src(product)
    if src:
        data["image"] = SITE_URL + src
    if product.get("style"):
        data["sku"] = product["style"]
    if priced(product):
        offer = {
            "@type": "Offer",
            "price": f"{product['price']:.2f}",
            "priceCurrency": "USD",
            "url": product["url"],
            "seller": {"@type": "Organization", "name": merchant(product)["name"]},
            "validFrom": product.get("price_checked") or CHECKED,
        }
        if product.get("in_stock") is False:
            offer["availability"] = "https://schema.org/OutOfStock"
        data["offers"] = offer
    return data


def faq_ld(pairs):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in pairs
        ],
    }


def faq_html(pairs):
    blocks = "".join(f"<h3>{e(q)}</h3><p>{e(a)}</p>" for q, a in pairs)
    return f'<section class="box"><h2 style="margin-top:0">Questions</h2>{blocks}</section>'


def deal_faqs(product):
    if priced(product):
        was = compare(product)
        price_a = f"On {CHECKED}, {merchant(product)['name']} listed {product['name']} at {money(product['price'])}."
        if was:
            price_a += f" The same page showed {money(was)} as the original price."
        if product.get("in_stock") is False:
            price_a += " The page also said the item was out of stock."
    else:
        price_a = (
            f"The {merchant(product)['name']} page we read on {CHECKED} did not show a price, "
            "so this page does not print one. Use Check today's price to see the live page."
        )
    spec_bits = "; ".join(f"{label}: {value}" for label, value in product["specs"][:4])
    return [
        (f"What does {product['name']} cost?", price_a),
        (
            f"Where does the buy button go?",
            f"It goes to the {merchant(product)['name']} product page. "
            + (
                "A CJ deep link is not turned on yet, so the URL has no tracking parameters."
                if not merchant(product).get("deep_link")
                else "The merchant program is approved, so the button uses the deep link in the central link file."
            ),
        ),
        (
            f"What does the manufacturer say about {product['name']}?",
            product["summary"] + (f" Details from that page: {spec_bits}." if spec_bits else ""),
        ),
    ]


def render_deal(product):
    path = deal_path(product) + "/index.html"
    use_slug = product["slug"]
    others = related(product)
    spec_rows = "".join(f"<tr><td>{e(label)}</td><td>{e(value)}</td></tr>" for label, value in product["specs"])
    price_row = ""
    if priced(product):
        was = compare(product)
        was_cell = money(was) if was else "—"
        price_row = (
            "<h2>Price on the merchant page</h2><table><thead><tr><th>Retailer</th><th>Price</th><th>Original on that page</th><th>Read</th></tr></thead><tbody>"
            f"<tr><td>{text_link(product, 'deal', use_slug, 'table')}</td><td><b>{money(product['price'])}</b></td>"
            f"<td>{was_cell}</td><td class='meta'>{CHECKED}</td></tr></tbody></table>"
            "<p class='note'>Original means a compare-at price printed on the same product page. It is not a price we measured somewhere else.</p>"
        )
    else:
        price_row = "<p class='note'>This page has no price because the merchant page did not show one we could record. The button opens that page.</p>"
    faqs = deal_faqs(product)
    also = ""
    if others:
        cards = "".join(card(row, "deal", use_slug) for row in others)
        if cards:
            also = '<h2>Also popular</h2><div class="grid">' + cards + "</div>"
    guides = guide_links_for(product)
    guide_html = ""
    if guides:
        guide_html = '<div class="chips">' + "".join(f'<a href="{href(path)}">{e(label)}</a>' for path, label in guides) + "</div>"
    if priced(product):
        title = f"{product['name']}: {money(product['price'])}"
        desc = f"{product['name']} was {money(product['price'])} at {merchant(product)['name']} on {CHECKED}. {product['summary']}"
    else:
        title = f"{product['name']}: check today's price"
        desc = f"{product['name']} at {merchant(product)['name']}. No price was on the page we read on {CHECKED}. {product['summary']}"
    title = title[:70]
    desc = desc[:160]
    body = (
        crumbs([(product["name"], deal_path(product))])
        + f"<h1>{e(product['name'])}</h1>"
        + lead(product, "deal", use_slug)
        + f'<div class="hero">{img_tag(product, eager=True)}<div class="specs"><h2 style="margin-top:0">From the manufacturer page</h2>'
        + f"<table>{spec_rows}</table></div></div>"
        + price_row
        + f"<p>{e(product['summary'])}</p>"
        + guide_html
        + faq_html(faqs)
        + also
    )
    page(path, title, desc, body, [product_ld(product), faq_ld(faqs)], index=True)


GUIDE_INDEX = []


def add_guide(path, title, desc, intro, slugs, faqs, extra=""):
    rows = [PRODUCTS[slug] for slug in slugs if slug in PRODUCTS]
    rows.sort(key=lambda row: row.get("in_stock") is False)
    featured = next((row for row in rows if for_sale(row)), None)
    pagetype = path.split("/")[0]
    pageslug = path.strip("/").split("/")[-1]
    body = (
        crumbs([(title, path)])
        + f"<h1>{e(title)}</h1><p class='sub'>{e(intro)}</p>"
        + (lead(featured, pagetype, pageslug) if featured else "")
        + extra
        + '<div class="grid">' + "".join(card(row, pagetype, pageslug) for row in rows) + "</div>"
        + faq_html(faqs)
    )
    page(path.strip("/") + "/index.html", title, desc, body, [faq_ld(faqs)] if faqs else None)
    GUIDE_INDEX.append((path, title))


def guide_links_for(product):
    found = []
    for path, title, slugs in GUIDE_MEMBERSHIP:
        if product["slug"] in slugs:
            found.append((path, title))
    return found[:6]


def comparison_note():
    return (
        '<section class="box"><h2 style="margin-top:0">Names people also compare</h2>'
        "<p>Patagonia's Down Sweater and Better Sweater, The North Face 1996 Retro Nuptse, and UGG boots come up in the same searches. "
        "This site does not have an approved program for those brands, so they are named here without a buy link and without a price.</p></section>"
    )


def vs_page():
    caribou = PRODUCTS["sorel-womens-caribou"]
    joan = PRODUCTS["sorel-joan-of-arctic"]
    path = "vs/sorel-caribou-vs-joan-of-arctic"
    faqs = [
        (
            "Which costs less, the women's Caribou or the Joan of Arctic?",
            f"On {CHECKED}, Sorel listed the women's Caribou at {money(caribou['price'])} and the Joan of Arctic at {money(joan['price'])}.",
        ),
        (
            "Does either page say which boot is warmer?",
            "No. Both pages describe waterproof construction and a removable 9 mm lining. This site does not add a warmth score.",
        ),
    ]
    rows = "".join(
        f"<tr><td>{e(label)}</td><td>{e(a)}</td><td>{e(b)}</td></tr>"
        for label, a, b in [
            ("Price on the page", money(caribou["price"]), money(joan["price"])),
            ("Upper", "Waterproof nubuck leather", "Waterproof suede with a faux-fur cuff"),
            ("Lining", "Removable 9 mm", "Removable 9 mm"),
            ("Laces", "Not waterproof, per Sorel", "Not waterproof, per Sorel"),
        ]
    )
    extra = (
        "<table><thead><tr><th></th><th>Women's Caribou</th><th>Joan of Arctic</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        f"<p>{button(caribou, 'vs', 'sorel-caribou-vs-joan-of-arctic', 'cta')} "
        f"{button(joan, 'vs', 'sorel-caribou-vs-joan-of-arctic', 'also')}</p>"
    )
    # lead() already prints a button; keep the table as the comparison and use a normal guide.
    title = "Sorel Caribou vs Joan of Arctic"
    desc = f"Women's Caribou was {money(caribou['price'])} and Joan of Arctic was {money(joan['price'])} on Sorel's pages on {CHECKED}."
    body = (
        crumbs([(title, path)])
        + f"<h1>{e(title)}</h1><p class='sub'>Prices and construction notes from the two Sorel product pages on {CHECKED}. No lab test is added here.</p>"
        + lead(caribou, "vs", "sorel-caribou-vs-joan-of-arctic")
        + extra
        + '<div class="grid">' + card(caribou, "vs", "sorel-caribou-vs-joan-of-arctic") + card(joan, "vs", "sorel-caribou-vs-joan-of-arctic") + "</div>"
        + faq_html(faqs)
    )
    page(path + "/index.html", title, desc, body, [faq_ld(faqs)])
    GUIDE_INDEX.append((path, title))

    boot = PRODUCTS["drmartens-1460"]
    jadon = PRODUCTS["drmartens-jadon"]
    path = "vs/dr-martens-1460-vs-jadon"
    faqs = [
        (
            "What is the price difference between the 1460 and the Jadon?",
            f"On {CHECKED}, Dr. Martens listed the 1460 Smooth at {money(boot['price'])} and the Jadon platform at {money(jadon['price'])}.",
        ),
        (
            "How does Dr. Martens describe the Jadon versus the 1460?",
            "The 1460 page describes the original 8-eye lace-up with a PVC sole. The Jadon page describes a platform sole and an inside zip. This page does not rank them.",
        ),
    ]
    rows = "".join(
        f"<tr><td>{e(label)}</td><td>{e(a)}</td><td>{e(b)}</td></tr>"
        for label, a, b in [
            ("Price on the page", money(boot["price"]), money(jadon["price"])),
            ("Style number", boot["style"], jadon["style"]),
            ("Sole, in the brand's words", "100% PVC", "Platform sole with yellow welt stitching"),
            ("Closure", "Lace-up, 8-eye", "Inside zip"),
        ]
    )
    title = "Dr. Martens 1460 vs Jadon"
    desc = f"The 1460 was {money(boot['price'])} and the Jadon was {money(jadon['price'])} on the Dr. Martens pages on {CHECKED}."
    body = (
        crumbs([(title, path)])
        + f"<h1>{e(title)}</h1><p class='sub'>Side-by-side notes from the two Dr. Martens product pages. Not a wear test.</p>"
        + lead(boot, "vs", "dr-martens-1460-vs-jadon")
        + f"<table><thead><tr><th></th><th>1460</th><th>Jadon</th></tr></thead><tbody>{rows}</tbody></table>"
        + '<div class="grid">' + card(boot, "vs", "dr-martens-1460-vs-jadon") + card(jadon, "vs", "dr-martens-1460-vs-jadon") + "</div>"
        + faq_html(faqs)
    )
    page(path + "/index.html", title, desc, body, [faq_ld(faqs)])
    GUIDE_INDEX.append((path, title))


def by_slugs(slugs):
    return [slug for slug in slugs if slug in PRODUCTS]


def all_slugs(**pred):
    rows = []
    for slug, product in PRODUCTS.items():
        if all(product.get(key) == value for key, value in pred.items()):
            rows.append(slug)
    return rows


def under_200_jackets():
    slugs = []
    for slug, product in PRODUCTS.items():
        if product["category"] == "jacket" and priced(product) and product["price"] < 200:
            slugs.append(slug)
    slugs.sort(key=lambda slug: PRODUCTS[slug]["price"])
    return slugs


def with_price(slugs):
    known = [slug for slug in slugs if priced(PRODUCTS[slug])]
    unknown = [slug for slug in slugs if not priced(PRODUCTS[slug])]
    known.sort(key=lambda slug: PRODUCTS[slug]["price"])
    return known + unknown


def build_guides():
    jackets_under = under_200_jackets()
    mens_boots = with_price([
        slug for slug, product in PRODUCTS.items()
        if product["category"] == "boot" and product["gender"] in ("men", "unisex")
    ])
    womens_boots = with_price([
        slug for slug, product in PRODUCTS.items()
        if product["category"] == "boot" and product["gender"] in ("women", "unisex")
    ])
    rain_boots = with_price([
        slug for slug, product in PRODUCTS.items() if product["family"] == "rain-boot"
    ])
    waterproof = with_price([
        "sorel-womens-caribou", "sorel-mens-caribou", "sorel-joan-of-arctic", "sorel-out-n-about-iv",
        "hunter-womens-original-tall", "hunter-mens-original-tall", "hunter-womens-original-short", "hunter-mens-original-short",
        "columbia-womens-ice-maiden-ii", "columbia-womens-minx-mid-iii", "columbia-mens-bugaboot-celsius",
        "columbia-mens-newton-ridge-plus-ii", "columbia-womens-newton-ridge-plus-ii",
        "xtratuf-mens-legacy-15", "xtratuf-womens-legacy-15", "xtratuf-mens-ankle-deck", "xtratuf-womens-ankle-deck",
        "muck-mens-arctic-sport-tall", "muck-womens-arctic-sport-ii-tall",
    ])
    alternatives = [
        "columbia-mens-bugaboo-ii", "columbia-womens-bugaboo-iv", "columbia-mens-whirlibird-v",
        "columbia-womens-whirlibird-v", "columbia-mens-powder-lite-ii", "columbia-womens-powder-lite-ii",
        "columbia-mens-puffect-iv", "columbia-womens-puffect-ii",
    ]
    warmest = [
        "canada-goose-mens-expedition-parka", "canada-goose-womens-expedition-parka",
        "canada-goose-langford-parka", "canada-goose-crofton-puffer",
        "canada-goose-shelburne-parka", "canada-goose-mens-chilliwack-bomber",
        "canada-goose-womens-chilliwack-bomber",
    ]
    jackets = [slug for slug, product in PRODUCTS.items() if product["category"] == "jacket"]
    him = [slug for slug, product in PRODUCTS.items() if product["gender"] in ("men", "unisex")]
    her = [slug for slug, product in PRODUCTS.items() if product["gender"] in ("women", "unisex")]
    global GUIDE_MEMBERSHIP
    GUIDE_MEMBERSHIP = [
        ("best/winter-coats-under-200", "Best winter coats under $200", jackets_under),
        ("best/mens-winter-boots", "Best men's winter boots", mens_boots),
        ("best/womens-winter-boots", "Best women's winter boots", womens_boots),
        ("best/rain-boots", "Best rain boots", rain_boots),
        ("best/canada-goose-alternatives", "Canada Goose alternatives", alternatives),
        ("best/waterproof-boots", "Best waterproof boots", waterproof),
        ("best/warmest-parkas", "Warmest parkas", warmest),
        ("black-friday-jacket-deals", "Black Friday jacket deals", jackets),
        ("gifts/christmas-gifts-for-him", "Christmas gifts for him", him),
        ("gifts/christmas-gifts-for-her", "Christmas gifts for her", her),
        ("gifts/for-him", "Gifts for him", him),
        ("gifts/for-her", "Gifts for her", her),
        ("gifts/winter-boots", "Winter boot gifts", mens_boots + [s for s in womens_boots if s not in mens_boots]),
        ("gifts/rain-boots", "Rain boot gifts", rain_boots),
    ]
    low = PRODUCTS[jackets_under[0]]["price"] if jackets_under else None
    add_guide(
        "best/winter-coats-under-200",
        "Winter coats under $200",
        f"Jackets on this site whose merchant page listed a price under $200 on {CHECKED}.",
        "Only jackets with a price we read on the merchant page, and only when that price was under $200. Canada Goose parkas are not in this list.",
        jackets_under,
        [("How is this list chosen?", "A jacket is included when its own product page showed a price under $200 on the day we read it. Missing prices are left off, not guessed.")],
    )
    add_guide(
        "best/mens-winter-boots",
        "Men's winter boots",
        "Men's and unisex boots we track, with the price from each merchant page when one was printed.",
        "These are famous men's and unisex boots from the merchants we link. The order with a price is low to high. That is not a warmth ranking.",
        mens_boots,
        [("Are these ranked by warmth?", "No. Where a price was on the page, the cards run from the lower price to the higher price. Boots with no recorded price follow them.")],
    )
    add_guide(
        "best/womens-winter-boots",
        "Women's winter boots",
        "Women's and unisex boots we track, with merchant prices when the page showed one.",
        "Famous women's and unisex boots from the merchants on this site. A lower price is not a claim that the boot is better.",
        womens_boots,
        [("Why are some Dr. Martens on a women's list?", "The 1460, 2976, Jadon, and 1461 pages are the classic unisex styles, so they also appear on the men's list.")],
    )
    add_guide(
        "best/rain-boots",
        "Rain boots",
        "Hunter Original rain boots and Xtratuf Legacy deck boots, with the prices on their product pages.",
        "Hunter calls the Original a waterproof rubber rain boot. Xtratuf calls the Legacy and Ankle Deck boots 100% waterproof on their pages.",
        rain_boots,
        [("Are Thursday boots in this rain list?", "No. Thursday's pages we used describe welt construction, not a waterproof rain boot, so they are not in this list.")],
    )
    add_guide(
        "best/canada-goose-alternatives",
        "Canada Goose alternatives",
        "Columbia jackets people shop when they are not buying a Canada Goose parka, with prices only where Columbia printed one.",
        "These Columbia jackets are different products at different prices. They are not copies of a Canada Goose parka, and this page does not claim they are as warm.",
        alternatives,
        [("Is a Columbia jacket the same as a Canada Goose parka?", "No. The construction, fill, and prices are different. Compare the spec tables on each deal page, which quote the brand's own page.")],
        extra=comparison_note(),
    )
    add_guide(
        "best/waterproof-boots",
        "Waterproof boots",
        "Boots whose merchant page describes waterproof construction, with prices when the page showed one.",
        "A boot is here only when the manufacturer page we read describes it as waterproof or seam-sealed waterproof. Dress boots that do not say that are left off.",
        waterproof,
        [("Did you test these for leaks?", "No. The waterproof line is the manufacturer's wording from the product page, not a test run by this site.")],
        extra=comparison_note(),
    )
    warm_extra = (
        '<section class="box"><h2 style="margin-top:0">How this page is ordered</h2>'
        "<p>Canada Goose prints its own temperature line and TEI label on several of these pages. "
        "The Expedition pages say -22°F and below, TEI 5. Langford and the Crofton EnduraLuxe Puffer say 5°F to -13°F, TEI 4. "
        "Shelburne and the men's Chilliwack say 14°F to -4°F, TEI 3. "
        "The women's Chilliwack price is listed, without a temperature line, because that line was not read on the women's page. "
        "These are the brand's labels, not an independent lab result.</p></section>"
        + comparison_note()
    )
    add_guide(
        "best/warmest-parkas",
        "Warmest parkas",
        "Canada Goose parkas ordered by the temperature line printed on the brand's own page.",
        "Ordered using Canada Goose's own temperature guidance where that page printed one. This is not a warmth test by OuterwearDealsDaily.",
        warmest,
        [("What does TEI mean here?", "It is the label Canada Goose prints on the product page. This site does not translate it into a score of our own.")],
        extra=warm_extra,
    )
    add_guide(
        "black-friday-jacket-deals",
        "Black Friday jacket deals",
        f"Jackets we track, with the price on each merchant page on {CHECKED}. Not a promise that a Black Friday code is active.",
        "Use this as a checklist of jacket model pages. A crossed-out price appears only when that product page printed an original price next to the current one.",
        jackets,
        [("Are these Black Friday discounts?", f"Only when the merchant page itself showed a current price and a higher original price on {CHECKED}. We do not add a holiday percent on top.")],
    )
    add_guide(
        "gifts/christmas-gifts-for-him",
        "Christmas gifts for him",
        "Men's and unisex jackets and boots, with a buy button on each model page.",
        "A gift shortlist of the men's and unisex models on this site. Open a deal page for the price and the manufacturer specs.",
        him,
        [("Do you ship the gift?", "No. The button goes to the brand's own product page, where you check size and shipping.")],
    )
    add_guide(
        "gifts/christmas-gifts-for-her",
        "Christmas gifts for her",
        "Women's and unisex jackets and boots to check before buying.",
        "Women's and unisex models from the brands we link. Prices are printed only when the product page showed one.",
        her,
        [("Which boots are under $200?", "Filter is not a second price list. On this page, cards with a number were under or over $200 exactly as the merchant printed it. The women's Caribou and Joan of Arctic were over $200 on the day we read them.")],
    )
    add_guide(
        "gifts/for-him",
        "Gifts for him",
        "The same men's and unisex shortlist as the Christmas page, for people shopping outside that season.",
        "Men's and unisex jackets and boots. Each card links to a single-product deal page.",
        him,
        [("Is this different from the Christmas list?", "It uses the same products. The Christmas page is the seasonal URL people search.")],
    )
    add_guide(
        "gifts/for-her",
        "Gifts for her",
        "Women's and unisex jackets and boots on single-product pages.",
        "Women's and unisex models. The button on each card uses the plain merchant URL until a CJ link is approved.",
        her,
        [("Can I see rain boots only?", "Yes. The rain boot gift page lists Hunter and Xtratuf.")],
    )
    add_guide(
        "gifts/winter-boots",
        "Winter boot gifts",
        "Winter and hiking boots we track, for gift shopping.",
        "Boots rather than jackets. Rain-specific Hunter and Xtratuf pages are on the rain boot gift page.",
        [slug for slug in (mens_boots + womens_boots) if PRODUCTS[slug]["family"] != "rain-boot"],
        [("Are dress boots included?", "Yes. Dr. Martens, Thursday, and Frye are boots people give as gifts, so they are on this list. Their pages do not claim a winter temperature rating.")],
    )
    add_guide(
        "gifts/rain-boots",
        "Rain boot gifts",
        "Hunter Original and Xtratuf Legacy boots with the price from each product page.",
        "Rain and deck boots. Each price was on the merchant page on the check date.",
        rain_boots,
        [("Which Hunter is the tall women's boot?", f"The women's Original Tall in black was {money(PRODUCTS['hunter-womens-original-tall']['price'])} on {CHECKED}.")],
    )
    # index pages for best and gifts
    best_links = "".join(f'<a href="{href(path)}">{e(title)}</a>' for path, title in GUIDE_INDEX if path.startswith("best/") or path.startswith("vs/"))
    gift_links = "".join(f'<a href="{href(path)}">{e(title)}</a>' for path, title in GUIDE_INDEX if path.startswith("gifts/"))
    page(
        "best/index.html",
        "Best jackets and boots",
        "Roundups of winter coats, parkas, rain boots, and waterproof boots, using merchant prices only.",
        f"<h1>Best of</h1><p class='sub'>Roundups built from the deal pages. A list never adds a price that was not on the product page.</p><div class='chips'>{best_links}</div>",
    )
    page(
        "gifts/index.html",
        "Jacket and boot gifts",
        "Gift pages for him and her, plus winter boots and rain boots.",
        f"<h1>Gifts</h1><p class='sub'>Each gift page is a set of deal pages, with the price above the photo on the product itself.</p><div class='chips'>{gift_links}</div>",
    )


BF_PATH = "black-friday-outerwear-boot-deals"


def savings_amount(product):
    """Dollar gap versus the original price already stored. None when either number is missing."""
    was = compare(product)
    if was is None:
        return None
    return round(was - float(product["price"]), 2)


def render_black_friday():
    deals = [p for p in PRODUCTS.values() if savings_amount(p) is not None and for_sale(p)]
    deals.sort(key=lambda p: (-savings_amount(p), p["name"]))
    unpriced = [p for p in PRODUCTS.values() if not priced(p)]
    unpriced.sort(key=lambda p: (0 if p["category"] == "jacket" else 1, p["name"]))
    jackets = [p for p in PRODUCTS.values() if p["category"] == "jacket" and priced(p)]
    boots = [p for p in PRODUCTS.values() if p["category"] == "boot" and priced(p)]
    jackets.sort(key=lambda p: (p.get("in_stock") is False, -(savings_amount(p) or 0), p["price"], p["name"]))
    boots.sort(key=lambda p: (p.get("in_stock") is False, -(savings_amount(p) or 0), p["price"], p["name"]))
    pageslug = BF_PATH
    rows = []
    for product in deals:
        was = compare(product)
        saved = savings_amount(product)
        stock = " Out of stock on the merchant page." if product.get("in_stock") is False else ""
        rows.append(
            "<tr>"
            f"<td class='photo'>{thumb_tag(product)}</td>"
            f"<td data-label='Model'><a href='{href(deal_path(product))}'>{e(product['name'])}</a></td>"
            f"<td data-label='Current'>{money(product['price'])}</td>"
            f"<td data-label='Original'>{money(was)}</td>"
            f"<td data-label='Savings'>{money(saved)}</td>"
            f"<td data-label='Merchant'>{e(merchant(product)['name'])}.{e(stock)} {button(product, 'black-friday', pageslug, 'table')}</td>"
            "</tr>"
        )
    unpriced_items = "".join(
        f"<li><a href='{href(deal_path(product))}'>{e(product['name'])}</a> "
        f"<span class='meta'>{e(merchant(product)['name'])}</span></li>"
        for product in unpriced
    )
    top = deals[0]
    faqs = [
        (
            "When is Black Friday 2026?",
            "Black Friday 2026 is Friday, November 27. Cyber Monday is Monday, November 30.",
        ),
        (
            "Which recorded deal saves the most?",
            f"On {CHECKED}, the largest gap versus an original price printed on the same merchant page is {money(savings_amount(top))} "
            f"for the {top['name']}: {money(top['price'])} versus {money(compare(top))} at {merchant(top)['name']}."
            + (" That page said the item was out of stock." if top.get("in_stock") is False else ""),
        ),
        (
            "Why are some models listed without a price?",
            "The merchant page we read did not show a number, so this page does not invent one. Those models are linked by name only.",
        ),
        (
            "Is this a prediction of Black Friday percent-off?",
            "No. A savings figure is only the difference between two prices already stored from the merchant page. This page does not estimate a weekend discount.",
        ),
        (
            "Where does the buy button go?",
            "To the brand's own product page. The link stays the plain product URL, with no tracking parameters, until that merchant's program is approved.",
        ),
    ]
    title = "Black Friday 2026 Outerwear and Boot Deals"
    desc = (
        f"Black Friday 2026 is November 27 and Cyber Monday is November 30. "
        f"Jacket and boot markdowns already on file, sorted by the biggest recorded savings. Prices from {CHECKED}."
    )
    intro = (
        f"Black Friday 2026 is Friday, November 27, and Cyber Monday is Monday, November 30. "
        f"The deals below use only prices already stored from merchant pages on {CHECKED}. "
        f"Savings are the gap between the current price and a higher original price on that same page. This is not a forecast."
    )
    expect = (
        "<section class='box' id='what-to-expect'><h2 style='margin-top:0'>What to expect on Black Friday</h2>"
        "<p>Black Friday is the Friday after Thanksgiving. In 2026 that is November 27, and Cyber Monday is November 30. "
        "Brands often start offers before Friday and leave some of them up through the weekend. Each brand sets its own offer. "
        "This page does not predict how deep a markdown will be.</p>"
        "<p>Use the prices already recorded here as a baseline, then confirm the live price, size, and stock on the merchant page. "
        "Popular sizes go first. Shipping cutoffs and return windows belong to the store you buy from.</p></section>"
    )
    body = (
        crumbs([("Black Friday 2026", BF_PATH)])
        + f"<h1>Black Friday 2026 outerwear and boot deals</h1>"
        + f"<p class='sub'>{e(intro)}</p>"
        + "<h2>Biggest recorded savings</h2>"
        + "<p class='note'>Sorted by the dollar gap between the current price and the original price on the same merchant page. "
        + "Models with only one price, with no price, or out of stock on that page are not in this table.</p>"
        + "<div class='scroll'><table class='prices'><thead><tr><th class='photo'><span class='sr-only'>Photo</span></th><th>Model</th><th>Current</th><th>Original on that page</th><th>Savings</th><th>Merchant</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
        + "<h2>Jackets and coats</h2>"
        + "<p class='note'>Every jacket we track that has a recorded price. Open the deal page for the manufacturer specs.</p>"
        + "<div class='grid'>" + "".join(card(p, "black-friday", pageslug) for p in jackets) + "</div>"
        + "<h2>Boots</h2>"
        + "<p class='note'>Every boot we track that has a recorded price.</p>"
        + "<div class='grid'>" + "".join(card(p, "black-friday", pageslug) for p in boots) + "</div>"
        + "<h2>No price recorded</h2>"
        + "<p class='note'>These merchant pages did not show a price when we read them. Names only, no numbers.</p>"
        + f"<ul id='no-price'>{unpriced_items}</ul>"
        + expect
        + faq_html(faqs)
        + f"<p class='note'>Jacket-only roundup: <a href='{href('black-friday-jacket-deals')}'>Black Friday jacket deals</a>.</p>"
    )
    page(BF_PATH + "/index.html", title, desc, body, [faq_ld(faqs)])
    GUIDE_INDEX.append((BF_PATH, "Black Friday 2026 outerwear and boot deals"))
    print(f"black friday deals={len(deals)} unpriced={len(unpriced)} jackets={len(jackets)} boots={len(boots)}")


def render_home():
    priced_rows = [p for p in PRODUCTS.values() if priced(p)]
    priced_rows.sort(key=lambda p: (p.get("in_stock") is False, p["price"], p["name"]))
    lead_product = next(p for p in priced_rows if p["slug"] == "columbia-mens-watertight-ii" and for_sale(p))
    rest = [p for p in priced_rows if p["slug"] != lead_product["slug"]]
    missing = [p for p in PRODUCTS.values() if not priced(p)]
    missing.sort(key=lambda p: (p.get("in_stock") is False, p["name"]))
    bf = (
        f"<section class='box' id='black-friday-2026'><h2 style='margin-top:0'><a href='{href(BF_PATH)}'>Black Friday 2026 outerwear and boot deals</a></h2>"
        "<p>Friday, November 27. Recorded jacket and boot markdowns, largest savings first. Cyber Monday is November 30.</p></section>"
    )
    body = (
        f"<h1>Jacket and boot deals</h1>"
        f"<p class='sub'>One page per famous model. The price and the buy button sit above the photo. Prices were read from the merchant on {CHECKED}.</p>"
        + bf
        + lead(lead_product, "home", "index")
        + '<div class="grid">' + "".join(card(p, "home", "index") for p in rest) + "".join(card(p, "home", "index") for p in missing) + "</div>"
        + '<h2>Guides</h2><div class="chips">'
        + "".join(f'<a href="{href(path)}">{e(title)}</a>' for path, title in GUIDE_INDEX)
        + "</div>"
    )
    page(
        "index.html",
        "OuterwearDealsDaily: jacket and boot deals",
        f"Deal pages for Columbia, Canada Goose, Sorel, Hunter, Dr. Martens, Thursday, Frye, Xtratuf, and Muck. Prices from merchant pages on {CHECKED}.",
        body,
    )


def render_indexes():
    jackets = [p for p in PRODUCTS.values() if p["category"] == "jacket"]
    boots = [p for p in PRODUCTS.values() if p["category"] == "boot"]
    for path, title, rows in (
        ("jackets", "Jackets and parkas", jackets),
        ("boots", "Boots", boots),
        ("men", "Men's jackets and boots", [p for p in PRODUCTS.values() if p["gender"] in ("men", "unisex")]),
        ("women", "Women's jackets and boots", [p for p in PRODUCTS.values() if p["gender"] in ("women", "unisex")]),
    ):
        rows = sorted(rows, key=lambda p: (p.get("in_stock") is False, p["name"]))
        body = f"<h1>{e(title)}</h1><div class='grid'>" + "".join(card(p, path, "index") for p in rows) + "</div>"
        page(path + "/index.html", title, f"{title} with a deal page for each model.", body)
    brands = {}
    for product in PRODUCTS.values():
        brands.setdefault(product["brand"], []).append(product)
    chips = "".join(
        f'<a href="{href("brands/" + re.sub(r"[^a-z0-9]+", "-", brand.lower()).strip("-"))}">{e(brand)}</a>'
        for brand in brands
    )
    page("brands/index.html", "Brands", "Jacket and boot brands on OuterwearDealsDaily.", f"<h1>Brands</h1><div class='chips'>{chips}</div>")
    for brand, rows in brands.items():
        bslug = re.sub(r"[^a-z0-9]+", "-", brand.lower()).strip("-")
        rows = sorted(rows, key=lambda p: (p.get("in_stock") is False, p["name"]))
        body = f"<h1>{e(brand)}</h1><div class='grid'>" + "".join(card(p, "brand", bslug) for p in rows) + "</div>"
        page(f"brands/{bslug}/index.html", f"{brand} deals", f"{brand} models we track, with merchant links.", body)


def render_static():
    rates = []
    for row in MERCHANTS.values():
        rate = "rate not entered" if row["commission_pct"] is None else f"{row['commission_pct']}%"
        cj = row["cj_advertiser_id"] or "none on file"
        rates.append(f"<li><b>{e(row['name'])}</b> — CJ {e(cj)}, {e(rate)}. Status: {e(row['status'])}.</li>")
    disclosure = (
        "<h1>Affiliate disclosure</h1>"
        f"<p>{e(OWNER)} publishes {NAME}. Some buttons may earn a commission later, at no extra cost to you. "
        "Until a CJ program is approved, every product button is the merchant's own product URL, with no click-tracking parameters.</p>"
        "<ul>" + "".join(rates) + "</ul>"
        "<p>Xtratuf and Muck are linked because the models are part of this niche. No affiliate program is on file for them. "
        "Patagonia, The North Face, and UGG are mentioned only as comparison names. They have no buy button and no price on this site.</p>"
        "<p>We do not link to Amazon, eBay, Walmart, Nordstrom Rack, or Sephora.</p>"
    )
    about = (
        "<h1>About</h1>"
        f"<p>{NAME} is a static deal site run by {e(OWNER)}. Each famous jacket or boot gets its own page: the price, when we have one, and a button above the photo, then the specs copied from the manufacturer page.</p>"
        "<p>The public site is https://outerweardealsdaily.com. Canonical URLs, the sitemap, and internal links use that origin with no path prefix.</p>"
        "<p>We are not Columbia, Sorel, Canada Goose, Hunter, Dr. Martens, Thursday Boot Company, Frye, Xtratuf, Muck, Patagonia, The North Face, or UGG.</p>"
    )
    privacy = (
        "<h1>Privacy</h1>"
        "<p>This is a static site. It has no account, no newsletter, and no form that stores your email. "
        "We do not sell personal information.</p>"
        "<p>GitHub Pages, which hosts the site, receives the usual request logs for a web server. "
        "When you use a product button, you leave this site for the merchant. After a CJ program is approved, that click can set the network's own cookie. "
        "Today the buttons do not add tracking parameters.</p>"
    )
    page("disclosure/index.html", "Affiliate disclosure", f"How {NAME} links to merchants and which CJ programs are pending.", disclosure)
    page("about/index.html", f"About {NAME}", f"{NAME} is run by {OWNER}.", about)
    page("privacy/index.html", "Privacy", f"Privacy notes for {NAME}.", privacy)
    page(
        "404.html",
        "Page not found",
        "That page is not on OuterwearDealsDaily.",
        f"<h1>Page not found</h1><p><a href='{href('')}'>Back to today's deals</a></p>",
        index=False,
    )


def publish_media():
    src_root = ROOT / "media"
    if not src_root.exists():
        return
    for path in src_root.rglob("*"):
        if not path.is_file():
            continue
        dest = OUT / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)


def write_feeds():
    publish_media()
    (OUT / "style.css").write_text(CSS)
    (OUT / ".nojekyll").write_text("")
    urls = []
    seen = set()
    for url in PAGES:
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    urls.sort()
    body = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        body.append(f"<url><loc>{e(url)}</loc></url>")
    body.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(body) + "\n")
    origin = absolute("")
    (OUT / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nDisallow: /go/\nDisallow: /out/\nDisallow: /redirect/\nDisallow: /r/\n\n"
        f"Sitemap: {origin.rstrip('/')}/sitemap.xml\n"
    )
    (OUT / "llms.txt").write_text(
        f"# {NAME}\n\nOwned by {OWNER}. Static deal pages for jackets and boots.\n"
        "Prices are copied from merchant product pages. Missing prices are labeled Check today's price.\n"
        "Do not treat comparison names (Patagonia, The North Face, UGG) as offers.\n"
        f"Sitemap: {origin.rstrip('/')}/sitemap.xml\n"
    )
    public = []
    for product in PRODUCTS.values():
        public.append({
            "slug": product["slug"],
            "name": product["name"],
            "merchant": merchant(product)["name"],
            "url": product["url"],
            "price": product["price"],
            "compare_at": product["compare_at"] if compare(product) else None,
            "price_checked": product["price_checked"],
            "in_stock": product["in_stock"],
            "page": absolute(deal_path(product)),
        })
    (OUT / "deals.json").write_text(json.dumps({"checked": CHECKED, "products": public}, indent=2) + "\n")


def assert_site():
    html_files = list(OUT.rglob("*.html"))
    deal_pages = [p for p in html_files if "/jacket/" in str(p) or "/boot/" in str(p)]
    if len(deal_pages) < 40:
        raise SystemExit(f"expected at least 40 deal pages, got {len(deal_pages)}")
    hrefs = []
    srcs = []
    blob_parts = []
    for path in html_files:
        text = path.read_text()
        blob_parts.append(text)
        hrefs.extend(re.findall(r'href="([^"]+)"', text))
        srcs.extend(re.findall(r'src="([^"]+)"', text))
    blob = "\n".join(blob_parts)
    for href_value in hrefs + srcs:
        low = href_value.lower()
        for banned in BANNED:
            if banned in low:
                raise SystemExit(f"banned host in output: {banned} in {href_value}")
        if "/go/" in low or low.startswith("go/"):
            raise SystemExit(f"redirect path in output: {href_value}")
        if href_value in srcs and (low.startswith("http:") or low.startswith("https:")):
            raise SystemExit(f"hotlinked image: {href_value}")
    if "No photo from the merchant page" in blob or "Georgia" in (OUT / "style.css").read_text():
        raise SystemExit("grey photo box or serif body font is still in the site")
    for src_value in srcs:
        if src_value.startswith("/media/"):
            if not (OUT / src_value.lstrip("/")).is_file():
                raise SystemExit(f"missing local image: {src_value}")
    if "aggregateRating" in blob or "reviewCount" in blob:
        raise SystemExit("ratings leaked into schema")
    for product in PRODUCTS.values():
        page_file = OUT / (deal_path(product) + "/index.html")
        text = page_file.read_text()
        lead_at = text.find("lead-offer")
        img_at = text.find("<img")
        if lead_at < 0:
            raise SystemExit(f"missing lead: {product['slug']}")
        if product.get("image"):
            if img_at < 0 or lead_at > img_at:
                raise SystemExit(f"price/button is not above the photo: {product['slug']}")
        elif img_at >= 0 or "nophoto" in text:
            raise SystemExit(f"photoless page still shows a photo box: {product['slug']}")
        if priced(product):
            if money(product["price"]) not in text:
                raise SystemExit(f"missing price for {product['slug']}")
        else:
            if re.search(r"\$\d", text.split("Also popular")[0]):
                raise SystemExit(f"unpriced page shows a dollar amount: {product['slug']}")
        if "FAQPage" not in text:
            raise SystemExit(f"missing FAQ schema: {product['slug']}")
        if product["url"] not in text:
            raise SystemExit(f"missing product url: {product['slug']}")
    bf = (OUT / "black-friday-outerwear-boot-deals" / "index.html").read_text()
    if "FAQPage" not in bf:
        raise SystemExit("black friday page missing FAQPage")
    if absolute(BF_PATH) not in bf:
        raise SystemExit("black friday canonical missing")
    expect = bf.split("id='what-to-expect'", 1)[1].split("</section>", 1)[0]
    if "$" in expect or "%" in expect:
        raise SystemExit("what-to-expect contains a number we should not print")
    noprice = bf.split("id='no-price'", 1)[1].split("</ul>", 1)[0]
    if "$" in noprice:
        raise SystemExit("no-price list contains a price")
    table_at = bf.find("<table class='prices'>")
    grid_at = bf.find("<div class='grid'>")
    if table_at < 0 or grid_at < 0 or table_at > grid_at:
        raise SystemExit("black friday price table is not before the card grid")
    table_html = bf[table_at:grid_at]
    for product in PRODUCTS.values():
        if savings_amount(product) is None:
            continue
        if not for_sale(product):
            if product["name"] in table_html or href(deal_path(product)) in table_html:
                raise SystemExit(f"out of stock product is in the savings table: {product['slug']}")
            continue
        photo = thumb_tag(product)
        if photo not in table_html:
            raise SystemExit(f"price table missing thumbnail: {product['slug']}")
        if 'loading="lazy"' not in photo or 'width="72"' not in photo or 'height="72"' not in photo:
            if product.get("image"):
                raise SystemExit(f"thumbnail is missing lazy size: {product['slug']}")
        if product.get("image") and img_tag(product) not in bf[grid_at:]:
            raise SystemExit(f"card image missing below the table: {product['slug']}")
        if money(product["price"]) not in table_html:
            raise SystemExit(f"table price missing: {product['slug']}")
        was = compare(product)
        saved = savings_amount(product)
        if was is None or saved is None or money(was) not in table_html or money(saved) not in table_html:
            raise SystemExit(f"table savings changed: {product['slug']}")
    home = (OUT / "index.html").read_text()
    if href(BF_PATH) not in home:
        raise SystemExit("home page missing black friday link")
    if href(BF_PATH) not in home.split("<nav>", 1)[1].split("</nav>", 1)[0]:
        raise SystemExit("nav missing black friday link")
    box = home.split("id='black-friday-2026'", 1)[1].split("</section>", 1)[0]
    if "btn" in box or box.count("Black Friday") != 1:
        raise SystemExit("home black friday promo is still repeated")
    boots_page = (OUT / "best" / "mens-winter-boots" / "index.html").read_text()
    lead_name = re.search(r'class="lead-name"><b>([^<]+)', boots_page)
    if not lead_name or "2976" in lead_name.group(1):
        raise SystemExit("out of stock boot leads the men's winter boots page")
    if "data-label='Savings'" not in bf or "data-label='Merchant'" not in bf:
        raise SystemExit("savings rows are missing mobile labels")
    print(f"pages={len(html_files)} deals={len(deal_pages)} priced={sum(1 for p in PRODUCTS.values() if priced(p))}")


def main():
    images.localize(DATA)
    if OUT.exists():
        for child in sorted(OUT.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
    OUT.mkdir(parents=True, exist_ok=True)
    build_guides()
    vs_page()
    for product in PRODUCTS.values():
        render_deal(product)
    render_indexes()
    render_static()
    render_black_friday()
    render_home()
    write_feeds()
    assert_site()


if __name__ == "__main__":
    main()
