# -*- coding: utf-8 -*-
import base64, hashlib, html, os, re, socket, ssl, time, urllib.error, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
HDRS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9", "Cache-Control": "no-cache"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
socket.setdefaulttimeout(25)

def slug(name):
    s = name.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "firm"

def get(url, timeout=25, maxbytes=3_000_000):
    """Return (status, final_url, text, err). Never raises."""
    if not url:
        return (0, url, "", "no-url")
    req = urllib.request.Request(url, headers=HDRS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            raw = r.read(maxbytes)
            enc = r.headers.get("Content-Encoding", "")
            if enc == "gzip":
                import gzip; raw = gzip.decompress(raw)
            elif enc == "deflate":
                import zlib; raw = zlib.decompress(raw, -15)
            ct = (r.headers.get("Content-Type") or "").lower()
            cs = "utf-8"
            m = re.search(r"charset=([\w\-]+)", ct)
            if m: cs = m.group(1)
            try: text = raw.decode(cs, "replace")
            except Exception: text = raw.decode("utf-8", "replace")
            return (r.status, r.geturl(), text, None)
    except urllib.error.HTTPError as e:
        return (e.code, url, "", "http-%s" % e.code)
    except Exception as e:
        return (0, url, "", type(e).__name__ + ":" + str(e)[:120])

def strip_html(s):
    s = re.sub(r"<script[^>]*>.*?</script>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<style[^>]*>.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<noscript[^>]*>.*?</noscript>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"<(br|/p|/div|/li|/tr|/h[1-6])[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\x0b\f\r]+\n?", " ", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()

def links(base, htmltext):
    out = set()
    for m in re.finditer(r'<a[^>]+href="([^"#]+)"', htmltext, flags=re.I):
        u = urllib.parse.urljoin(base, html.unescape(m.group(1)).strip())
        if u.startswith("http"):
            out.add(u.split("#")[0])
    return out

def origin(url):
    p = urllib.parse.urlsplit(url)
    return "%s://%s" % (p.scheme, p.netloc)

def host(url):
    return urllib.parse.urlsplit(url).netloc.lower().replace("www.", "")

def bing(query, count=20):
    """Return list of (title, url) from Bing HTML results, decoding the ck/a redirect."""
    q = urllib.parse.quote(query)
    st, fu, txt, err = get("https://www.bing.com/search?q=%s&count=%d&setlang=en" % (q, count), timeout=25)
    if st != 200 or not txt:
        return []
    res = []
    for b in re.split(r'<li class="b_algo"', txt)[1:]:
        m = re.search(r'<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', b, flags=re.S)
        if not m:
            continue
        href = html.unescape(m.group(1))
        title = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        real = href
        mm = re.search(r"[?&]u=a1([A-Za-z0-9_\-]+)", href)
        if mm:
            b64 = mm.group(1).replace("-", "+").replace("_", "/")
            b64 += "=" * (-len(b64) % 4)
            try: real = base64.b64decode(b64).decode("utf-8", "replace")
            except Exception: pass
        if real.startswith("http"):
            res.append((title, real))
    return res

JINA_HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}

def jina(url, timeout=40, tries=3):
    """Read a page through the public r.jina.ai text reader. Simple UA required (a full
    Chrome UA string is rejected with 403 by that service)."""
    for i in range(tries):
        req = urllib.request.Request("https://r.jina.ai/" + url, headers=JINA_HDRS)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.read(1_500_000).decode("utf-8", "replace")
        except Exception:
            time.sleep(1.5 * (i + 1))
    return ""

def sha(s):
    return hashlib.sha1(s.encode("utf-8", "replace")).hexdigest()[:10]
