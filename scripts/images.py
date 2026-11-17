"""Save each product photo in the repo and point the data row at that file.

Remote picture URLs are read once, resized to a 600px JPEG, and stored at
media/products/{slug}.jpg. The generator never requests an affiliate click URL.
"""
import html
import io
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import links

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "links.json"
MAX_EDGE = 600
MAX_BYTES = 12_000_000
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


class RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if links.safe_request_url(newurl) is None:
            raise urllib.error.HTTPError(newurl, code, "refusing redirect", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def local_rel(slug):
    return f"media/products/{slug}.jpg"


def fetch(url):
    safe = links.safe_request_url(url)
    if not safe:
        return None
    req = urllib.request.Request(
        safe,
        headers={"User-Agent": UA, "Accept": "text/html,image/avif,image/webp,image/*,*/*;q=0.8"},
    )
    opener = urllib.request.build_opener(RefuseRedirect)
    try:
        with opener.open(req, timeout=40) as resp:
            final = resp.geturl()
            if links.safe_request_url(final) is None:
                return None
            data = resp.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                return None
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            return data, ctype
    except Exception as exc:
        print(f"image fetch failed: {url} ({exc})")
        return None


def looks_like_image(data, ctype):
    if not data or len(data) < 32:
        return False
    if data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n" or data[:4] == b"RIFF" or data[:4] == b"GIF8":
        return True
    return ctype.startswith("image/") and ctype != "image/svg+xml"


def save_jpeg(data, dest):
    from PIL import Image

    im = Image.open(io.BytesIO(data))
    im.load()
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.getchannel("A"))
        im = bg
    else:
        im = im.convert("RGB")
    resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
    im.thumbnail((MAX_EDGE, MAX_EDGE), resample)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=85, optimize=True)


def image_from_html(page, page_url):
    text = page.decode("utf-8", "replace")
    patterns = (
        r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]*content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*property=["\']og:image(?::secure_url)?["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*name=["\']twitter:image["\']',
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        url = urllib.parse.urljoin(page_url, html.unescape(match.group(1)).strip())
        if links.safe_request_url(url):
            return url
    return None


def bytes_for(product, current):
    if current.startswith(("http://", "https://")):
        got = fetch(current)
        if got and looks_like_image(got[0], got[1]):
            return got[0]
        if got and ("html" in got[1] or got[0][:1] == b"<"):
            found = image_from_html(got[0], current)
            if found:
                img = fetch(found)
                if img and looks_like_image(img[0], img[1]):
                    return img[0]
    page_url = product.get("url") or ""
    if not page_url:
        return None
    page = fetch(page_url)
    if not page:
        return None
    if "html" not in page[1] and page[0][:1] != b"<":
        return None
    found = image_from_html(page[0], page_url)
    if not found or found == current:
        return None
    img = fetch(found)
    if img and looks_like_image(img[0], img[1]):
        return img[0]
    return None


def localize(data):
    """Download any remote product photo and store media/products/{slug}.jpg on the row."""
    changed = False
    for product in data["products"].values():
        rel = local_rel(product["slug"])
        dest = ROOT / rel
        current = product.get("image") or ""
        if current in (rel, "/" + rel) and dest.is_file() and dest.stat().st_size > 500:
            if product.get("image") != rel:
                product["image"] = rel
                changed = True
            continue
        blob = bytes_for(product, current) if not (dest.is_file() and current in (rel, "/" + rel)) else None
        if blob is not None:
            save_jpeg(blob, dest)
        if dest.is_file() and dest.stat().st_size > 500:
            if product.get("image") != rel:
                product["image"] = rel
                changed = True
        else:
            print(f"no local photo: {product['slug']}")
            if product.get("image") is not None:
                product["image"] = None
                changed = True
    if changed:
        DATA_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return changed
