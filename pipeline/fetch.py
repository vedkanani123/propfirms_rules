# -*- coding: utf-8 -*-
"""Phase 1 - discovery + crawl. Writes raw/<slug>/ and resolved.json"""
import json, os, re, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from firms import F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw")
KEY = ["pricing","price","plans","plan","challenge","rules","faq","help","terms","payout","drawdown",
       "consistency","how-it-works","about","contact","accounts","evaluation","refund","legal","program","models","trading-rules"]
PROPFIRM_SIG = ["prop firm","proprietary trading","funded account","challenge","evaluation","payout","drawdown","profit split","trader funding"]

def norm(s): return re.sub(r"[^a-z0-9]", "", s.lower())

def looks_right(name, url, text):
    t = text.lower()
    n = norm(name)
    if n and n not in norm(text[:200000]):
        # allow partial (e.g. 'MyFundedFutures' vs 'My Funded Futures')
        parts = [p for p in re.split(r"[^a-z0-9]", name.lower()) if len(p) > 3]
        if not parts or not all(p in t for p in parts[:2]):
            return False, 0
    hits = sum(1 for s in PROPFIRM_SIG if s in t)
    return hits >= 3, hits

def discover(name):
    """Find the official site for a firm with no URL. Returns (url, evidence, candidates_tried)."""
    tried = []
    cands = []
    sl = lib.slug(name).replace("-", "")
    for tld in (".com", ".io", ".co", ".net", ".org", ".app", ".trade", ".fund"):
        cands.append("https://%s%s/" % (sl, tld))
    cands += ["https://www.%s.com/" % sl, "https://%sfunded.com/" % sl, "https://%sprop.com/" % sl]
    for q in ('"%s" prop firm' % name, '%s funded challenge prop firm' % name, '%s propfirm official website' % name):
        for title, u in lib.bing(q, 20)[:8]:
            cands.append(u)
        time.sleep(0.4)
    seen = set()
    for c in cands:
        h = lib.host(c)
        if h in seen or not h or "bing.com" in h or "wikipedia" in h or "youtube" in h or "reddit" in h:
            continue
        seen.add(h)
        tried.append(c)
        if len(tried) > 26:
            break
        st, fu, txt, err = lib.get(c, timeout=18, maxbytes=700000)
        if st == 200 and txt:
            ok, hits = looks_right(name, c, txt)
            if ok:
                return (fu or c), "name+%d prop-firm signals on homepage" % hits, tried
    return None, "no candidate passed verification", tried

def crawl(slug_, name, url):
    d = os.path.join(RAW, slug_)
    os.makedirs(d, exist_ok=True)
    man = {"slug": slug_, "name": name, "input_url": url, "pages": [], "errors": []}
    st, fu, txt, err = lib.get(url, timeout=28, maxbytes=2_500_000)
    if st != 200 or not txt:
        st2, fu2, txt2, err2 = lib.get(url.replace("https://", "http://"), timeout=25, maxbytes=2_500_000)
        if st2 == 200 and txt2: st, fu, txt, err = st2, fu2, txt2, err2
    if st != 200 or not txt:
        j = lib.jina(url, timeout=40)
        if j and len(j) > 500:
            base = url; o = lib.origin(url)
            def save0(u, body, status):
                fn = "00_homejina_%s.md" % lib.sha(u)
                open(os.path.join(d, fn), "w", encoding="utf-8", errors="replace").write(body)
                man["pages"].append({"kind": "home-jina", "url": u, "status": status, "file": fn, "bytes": len(body)})
            save0(url, j, 200)
            json.dump(man, open(os.path.join(d, "manifest.json"), "w"), indent=1)
            return man
        man["errors"].append("homepage:%s:%s" % (st, err))
        json.dump(man, open(os.path.join(d, "manifest.json"), "w"), indent=1)
        return man
    base = fu or url
    o = lib.origin(base)
    def save(kind, u, body, status):
        fn = "%02d_%s_%s.html" % (len(man["pages"]), kind, lib.sha(u))
        open(os.path.join(d, fn), "w", encoding="utf-8", errors="replace").write(body)
        man["pages"].append({"kind": kind, "url": u, "status": status, "file": fn, "bytes": len(body)})
    save("home", base, txt, st)
    # sitemaps
    sm_urls = []
    for cand in [o + "/sitemap.xml", o + "/sitemap_index.xml", o + "/sitemap-index.xml", o + "/sitemap1.xml"]:
        s, u2, t2, e2 = lib.get(cand, timeout=20, maxbytes=800000)
        if s == 200 and t2 and ("<urlset" in t2 or "<sitemapindex" in t2):
            save("sitemap", u2 or cand, t2, s)
            locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", t2)
            if "<sitemapindex" in t2:
                for c2 in locs[:4]:
                    if re.search(r"(_en|\.xml)", c2):
                        s2, u3, t3, e3 = lib.get(c2, timeout=20, maxbytes=900000)
                        if s2 == 200 and t3:
                            save("sitemap", u3 or c2, t3, s2)
                            sm_urls += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", t3)
            else:
                sm_urls += locs
            if sm_urls: break
    # candidate links: from homepage + sitemap, scored by keyword
    pool = lib.links(base, txt) | set(sm_urls)
    def score(u):
        lu = u.lower()
        if lib.host(u) != lib.host(base):
            return -1
        s = 0
        for i, k in enumerate(KEY):
            if k in lu: s += (30 - i)
        if lu.rstrip("/") == base.rstrip("/"): return -1
        return s
    ranked = sorted([u for u in pool if score(u) > 0], key=lambda u: -score(u))
    picked, seenpath = [], set()
    for u in ranked:
        p = urllib.parse.urlsplit(u).path.rstrip("/").lower()
        if p in seenpath: continue
        seenpath.add(p); picked.append(u)
        if len(picked) >= 12: break
    for u in picked:
        s, u2, t2, e2 = lib.get(u, timeout=22, maxbytes=900000)
        if s == 200 and t2: save("page", u2 or u, t2, s)
        else: man["errors"].append("%s:%s:%s" % (u, s, e2))
    # help / support subdomains
    h = lib.host(base)
    for sub in ("help", "support", "docs", "faq"):
        cand = "https://%s.%s/" % (sub, h)
        s, u2, t2, e2 = lib.get(cand, timeout=18, maxbytes=600000)
        if s == 200 and t2:
            save("sub", u2 or cand, t2, s)
            for smc in [cand.rstrip("/") + "/sitemap.xml"]:
                s3, u4, t4, e4 = lib.get(smc, timeout=18, maxbytes=900000)
                if s3 == 200 and t4 and "<" in t4:
                    save("subsitemap", u4 or smc, t4, s3)
    json.dump(man, open(os.path.join(d, "manifest.json"), "w"), indent=1)
    return man

def job(entry):
    name, url, cat = entry
    sl = lib.slug(name)
    disc = None
    if not url:
        url, ev, tried = discover(name)
        disc = {"url": url, "evidence": ev, "tried": tried[:12]}
        if not url:
            d = os.path.join(RAW, sl); os.makedirs(d, exist_ok=True)
            json.dump({"slug": sl, "name": name, "category": cat, "input_url": None,
                       "discovery": disc, "pages": [], "errors": ["unresolved"]},
                      open(os.path.join(d, "manifest.json"), "w"), indent=1)
            return {"name": name, "slug": sl, "url": None, "pages": 0, "status": "unresolved"}
    man = crawl(sl, name, url)
    man["category"] = cat
    if disc: man["discovery"] = disc
    json.dump(man, open(os.path.join(RAW, sl, "manifest.json"), "w"), indent=1)
    return {"name": name, "slug": sl, "url": man.get("input_url") or url, "pages": len(man.get("pages", [])),
            "status": "ok" if man.get("pages") else "failed"}

if __name__ == "__main__":
    os.makedirs(RAW, exist_ok=True)
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else len(F)
    batch = F[lo:hi]
    out = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(job, e): e for e in batch}
        for i, f in enumerate(as_completed(futs)):
            try: r = f.result()
            except Exception as e: r = {"name": futs[f][0], "status": "crash", "error": str(e)[:200], "pages": 0}
            out.append(r)
            print("[%d/%d] %-32s %-10s pages=%s %s" % (i + 1, len(batch), r.get("name", "?")[:32], r.get("status"), r.get("pages", 0), (r.get("url") or "")[:52]), flush=True)
    json.dump(out, open(os.path.join(ROOT, "raw", "_fetch_results_%d_%d.json" % (lo, hi)), "w"), indent=1)
    print("DONE", lo, hi)
