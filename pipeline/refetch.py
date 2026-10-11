# -*- coding: utf-8 -*-
"""Phase 1b - rescue firms whose direct crawl failed. Sequential, jina-assisted, patient."""
import json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from firms import F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw")
KEY = ["pricing","price","plans","challenge","rules","faq","terms","payout","drawdown","consistency","how-it-works","accounts","about","evaluation"]

def save(d, man, kind, u, body):
    fn = "%02d_%s_%s.md" % (len(man["pages"]), kind, lib.sha(u))
    open(os.path.join(d, fn), "w", encoding="utf-8", errors="replace").write(body)
    man["pages"].append({"kind": kind, "url": u, "status": 200, "file": fn, "bytes": len(body)})

def rescue(name, url):
    sl = lib.slug(name)
    d = os.path.join(RAW, sl); os.makedirs(d, exist_ok=True)
    mp = os.path.join(d, "manifest.json")
    man = json.load(open(mp)) if os.path.exists(mp) else {"slug": sl, "name": name, "input_url": url, "pages": [], "errors": []}
    if man.get("pages"): return {"slug": sl, "name": name, "status": "already-ok", "pages": len(man["pages"])}
    man["pages"] = []
    if not url:
        u2, ev, tried = None, "", []
        return {"slug": sl, "name": name, "status": "no-url", "pages": 0}
    # 1) direct retry (http + www)
    for cand in [url, url.replace("https://", "http://"), url.replace("https://", "https://www.")]:
        st, fu, txt, err = lib.get(cand, timeout=25, maxbytes=1_500_000)
        if st == 200 and txt and len(txt) > 800:
            fn = "00_home_%s.html" % lib.sha(cand)
            open(os.path.join(d, fn), "w", encoding="utf-8", errors="replace").write(txt)
            man["pages"].append({"kind": "home", "url": fu or cand, "status": 200, "file": fn, "bytes": len(txt)})
            break
    # 2) jina homepage
    if not man["pages"]:
        t = lib.jina(url, timeout=45, tries=2)
        if t and len(t) > 600: save(d, man, "home-jina", url, t)
        time.sleep(2.0)
    if not man["pages"]:
        man["errors"].append("rescue-failed")
        json.dump(man, open(mp, "w"), indent=1)
        return {"slug": sl, "name": name, "status": "failed", "pages": 0}
    # 3) a few likely rule pages via jina, from sitemap if available
    o = lib.origin(man["pages"][0]["url"])
    cands = []
    for sm in [o + "/sitemap.xml", o + "/sitemap_index.xml"]:
        st, fu, txt, err = lib.get(sm, timeout=20, maxbytes=900000)
        if st == 200 and txt and "<loc" in txt:
            locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", txt)
            if "<sitemapindex" in txt:
                for c2 in locs[:3]:
                    s2, u3, t3, e3 = lib.get(c2, timeout=20, maxbytes=900000)
                    if s2 == 200 and t3: locs += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", t3)
            cands += locs
        if cands: break
    for k in KEY:
        for c in cands:
            if k in c.lower() and lib.host(c) == lib.host(o):
                cands.remove(c); cands.insert(0, c); break
    picked, seen = [], set()
    for c in cands:
        p = re.sub(r"[^a-z0-9]", "", c.rsplit("/", 1)[-1].lower())
        if p in seen: continue
        seen.add(p); picked.append(c)
        if len(picked) >= 5: break
    for c in picked:
        t = lib.jina(c, timeout=40, tries=1)
        if t and len(t) > 500: save(d, man, "page-jina", c, t)
        time.sleep(2.0)
    json.dump(man, open(mp, "w"), indent=1)
    return {"slug": sl, "name": name, "status": "rescued", "pages": len(man["pages"])}

if __name__ == "__main__":
    todo = []
    for name, url, cat in F:
        sl = lib.slug(name)
        mp = os.path.join(RAW, sl, "manifest.json")
        if not os.path.exists(mp):
            todo.append((name, url)); continue
        m = json.load(open(mp))
        if not m.get("pages"):
            todo.append((name, m.get("input_url") or url))
    print("to rescue:", len(todo), flush=True)
    for i, (n, u) in enumerate(todo):
        try: r = rescue(n, u)
        except Exception as ex: r = {"name": n, "status": "crash", "error": str(ex)[:120], "pages": 0}
        print("[%d/%d] %-30s %-10s pages=%s" % (i + 1, len(todo), n[:30], r.get("status"), r.get("pages", 0)), flush=True)
    print("DONE")
