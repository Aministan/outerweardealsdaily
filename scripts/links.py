#!/usr/bin/env python3
"""Outbound link rules for OuterwearDealsDaily.

Scripts may read a plain merchant product URL. They must never request a
Commission Junction, Awin, or Rakuten click URL.
"""
import re
import urllib.parse

TRACKING_DOMAINS = (
    "anrdoezrs.net",
    "jdoqocy.com",
    "tkqlhce.com",
    "dpbolvw.net",
    "kqzyfj.com",
    "emjcd.com",
    "awin1.com",
    "click.linksynergy.com",
    "linksynergy.com",
)
BLOCKED_RETAILERS = (
    "amazon.",
    "ebay.",
    "walmart.",
    "nordstromrack.",
    "nordstrom.com",
    "sephora.",
)
REDIRECT_PREFIXES = ("/go/", "/out/", "/redirect/", "/r/")
_CJ_CLICK = re.compile(r"/click-\d+-\d+")


def host_of(url):
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower().rstrip(".")
    except Exception:
        return ""


def host_is(host, domain):
    host = (host or "").lower().rstrip(".")
    return host == domain or host.endswith("." + domain)


def is_tracking_host(host):
    return any(host_is(host, domain) for domain in TRACKING_DOMAINS)


def is_tracking_url(url):
    if not isinstance(url, str) or not url:
        return False
    if is_tracking_host(host_of(url)):
        return True
    low = url.lower()
    return any(domain in low for domain in TRACKING_DOMAINS)


def is_blocked_retailer(url):
    host = host_of(url)
    if not host:
        return False
    return any(host_is(host, domain) or domain in host for domain in BLOCKED_RETAILERS)


def is_redirect_path(path):
    path = path or "/"
    if not path.startswith("/"):
        path = "/" + path
    for prefix in REDIRECT_PREFIXES:
        if path == prefix.rstrip("/") or path.startswith(prefix):
            return True
    return False


def safe_request_url(url):
    """A URL this repo's scripts may GET. Never a tracking URL."""
    if not isinstance(url, str) or not url:
        return None
    if is_tracking_url(url) or is_blocked_retailer(url):
        return None
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None
    if is_redirect_path(parsed.path):
        return None
    return url


def sid_part(value):
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9-_]+", "-", (value or "").lower())).strip("-")


def make_sid(pagetype, slug, placement, product=""):
    """{pagetype}-{slug}-{placement}, at most 64 characters.

    On a hub page, the product slug is kept in front of the page slug.
    The placement is never the part that is cut.
    """
    typ = sid_part(pagetype) or "site"
    place = sid_part(placement) or "link"
    extra = "" if typ == "deal" else sid_part(product)
    page = sid_part(slug)
    body = "-".join(part for part in (extra, page) if part)
    sid = "-".join(part for part in (typ, body, place) if part)
    if len(sid) <= 64:
        return sid
    budget = 64 - len(typ) - len(place) - 2
    cut = ""
    if body and budget >= 1:
        cut = body[:budget].rstrip("-")
        if len(body) > budget and "-" in cut:
            cut = cut.rsplit("-", 1)[0]
        cut = cut.strip("-")
    sid = "-".join(part for part in (typ, cut, place) if part)
    return sid[:64].strip("-")


def affiliate_url(product_url, deep_link, sid):
    """Plain product URL, or a CJ deep link once deep_link is set.

    deep_link is the click base only, such as https://www.anrdoezrs.net/click-1-2.
    This function does not request it.
    """
    if not isinstance(product_url, str) or not product_url:
        return product_url
    if is_tracking_url(product_url) or is_blocked_retailer(product_url):
        raise SystemExit(f"refusing product url: {product_url}")
    if not deep_link:
        return product_url
    if not is_tracking_url(deep_link):
        raise SystemExit("deep_link must be a CJ click base, or null")
    parsed = urllib.parse.urlparse(deep_link)
    if not _CJ_CLICK.search(parsed.path or ""):
        raise SystemExit("deep_link is missing a /click-<pid>-<ad> path")
    base = deep_link.split("?", 1)[0]
    sid_q = urllib.parse.quote(sid, safe="-_")
    wrapped = base + "?sid=" + sid_q
    path = parsed.path or ""
    product = urllib.parse.urlparse(product_url)
    if (product.path or "") in ("", "/") and not product.query:
        return wrapped
    return wrapped + "&url=" + urllib.parse.quote(product_url, safe="")
