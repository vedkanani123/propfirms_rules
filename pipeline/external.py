# -*- coding: utf-8 -*-
"""Phase 3 - independent reputation lookup (Trustpilot + PropFirmMatch) via the public
r.jina.ai text reader. SEQUENTIAL on purpose: that service rate-limits concurrent calls.
Reads data/<slug>.json, writes external/<slug>.json. Records only what is literally present."""
import json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from firms import F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA, EXT = os.path.join(ROOT, "data"), os.path.join(ROOT, "external")

def clean(md):
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", md)
    md = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)
    return re.sub(r"\s+", " ", md).strip()

def tp(domain):
    url = "https://www.trustpilot.com/review/%s" % domain
    t = lib.jina(url, timeout=40, tries=2)
    time.sleep(2.2)
    if not t or len(t) < 700: return None
    c = clean(t)
    if re.search(r"(page not found|we can't find that page|404)", c[:400], re.I): return None
    o = {"source": "Trustpilot", "url": url}
    m = (re.search(r"with\s+([0-9](?:[.,][0-9])?)\s*/\s*5", c)
         or re.search(r"TrustScore\s*([0-9](?:[.,][0-9])?)", c)
         or re.search(r"\b([0-9]\.[0-9])\s*/\s*5", c)
         or re.search(r"\b([0-9]\.[0-9])\s*(?:out of|/)\s*5", c))
    o["score"] = m.group(1).replace(",", ".") if m else None
    m = (re.search(r"([\d,]{1,9})\s*(?:total\s*)?reviews", c, re.I)
         or re.search(r"Reviews\s*[:\s]+([\d,]{1,9})", c, re.I)
         or re.search(r"([\d,]{2,9})\s*reviews?\s*(?:in the last|total)", c, re.I))
    o["review_count"] = m.group(1) if m else None
    o["rating_suppressed"] = bool(re.search(r"rating is unavailable due to a breach|breach of our guidelines|rating is unavailable", c, re.I))
    if re.search(r"not enough reviews|Be the first to write a review|no reviews yet", c, re.I):
        o["empty"] = True
    themes, seen = [], set()
    for kw in ["scam", "payout", "breach", "banned", "withdraw", "refund", "support", "slippage", "denied", "delay"]:
        for m in re.finditer(r"([^.]{0,150}%s[^.]{0,150})" % re.escape(kw), c, re.I):
            s = re.sub(r"\s+", " ", m.group(1)).strip()
            k = s[:60].lower()
            if k in seen: continue
            seen.add(k); themes.append(s[:280]); break
        if len(themes) >= 6: break
    o["themes"] = themes
    o["excerpt"] = c[:900]
    return o

EXTRA = {"the-5ers": "the5ers", "e8-markets": "e8markets", "alpha-capital-group": "alphacapitalgroup",
         "crypto-fund-trader": "cryptofundtrader", "top-one-trader": "toponetrader", "goat-funded-trader": "goatfundedtrader",
         "hola-prime": "holaprime", "city-traders-imperium": "citytradersimperium", "atmos-funded": "atmosfunded",
         "for-traders": "fortraders", "instant-funding": "instantfunding", "bem-funding": "bemfunding",
         "hantec-trader": "hantectrader", "lark-funding": "larkfunding", "my-funded-futures": "myfundedfutures",
         "apex-trader-funding": "apextraderfunding", "take-profit-trader": "takeprofittrader", "one-up-trader": "oneuptrader",
         "funded-trading-plus": "fundedtradingplus", "the-funded-trader": "thefundedtrader", "futures-elite": "futureselite",
         "trade-day": "tradeday", "top-one-futures": "toponefutures", "the-trading-pit": "thetradingpit",
         "maven-trading": "maventrading", "prop-number-one": "propnumberone", "funded-trader-markets": "fundedtradermarkets",
         "moneta-funded": "monetafunded", "funded-elite": "fundedelite", "traders-launch": "traderslaunch",
         "blue-guardian": "blueguardian", "tradeify-fx": "tradeify-fx", "elite-trader-funding": "elitetraderfunding",
         "funded-futures-network": "fundedfuturesnetwork", "apex-proprietary": "apexproprietary"}

def pfm(name):
    sl = lib.slug(name)
    variants = [EXTRA.get(sl, sl), sl, sl.replace("-", "")]
    for v in dict.fromkeys(variants):
        url = "https://propfirmmatch.com/prop-firms/%s" % v
        t = lib.jina(url, timeout=40, tries=1)
        time.sleep(2.2)
        if not t or len(t) < 1500: continue
        c = clean(t)
        if re.search(r"page not found|404", c[:400], re.I): continue
        o = {"source": "PropFirmMatch", "url": url, "slug": v}
        m = re.search(r"\b([0-9]\.[0-9])\b", c)
        o["score"] = m.group(1) if m else None
        m = re.search(r"\b([\d,]{1,7})\s*reviews?\b", c, re.I)
        o["review_count"] = m.group(1) if m else None
        m = re.search(r"([A-Za-z .()\-]{3,40})\s*(?:\d+\s*years|years in operation)", c)
        o["country"] = m.group(1).strip() if m else None
        m = re.search(r"(\$[\d.]+\s?[KMB]?)\s*(?:Max|max)", c) or re.search(r"Max Allocations?[^$]{0,25}(\$[\d.]+\s?[KMB]?)", c, re.I)
        o["max_allocation"] = m.group(1).strip() if m else None
        codes = sorted(set(re.findall(r"\b(MATCH[A-Z0-9]{0,10}|PFM\d{2,4}|MATCHFIRST|MATCHNEW)\b", c)))
        o["promo_codes"] = codes[:6]
        m = re.search(r"(\d{1,3})\s*%\s*OFF", c)
        o["promo_off"] = m.group(1) + "%" if m else None
        o["excerpt"] = c[:900]
        return o
    return None

def job(entry):
    name, url, cat = entry
    sl = lib.slug(name)
    ep = os.path.join(EXT, sl + ".json")
    if os.path.exists(ep):
        prev = json.load(open(ep))
        if prev.get("trustpilot") or prev.get("propfirmmatch"):
            return {"slug": sl, "name": name, "status": "skip", "tp": (prev.get("trustpilot") or {}).get("score"),
                    "pfm": (prev.get("propfirmmatch") or {}).get("score"),
                    "tp_sup": bool((prev.get("trustpilot") or {}).get("rating_suppressed"))}
    dp = os.path.join(DATA, sl + ".json")
    d = json.load(open(dp)) if os.path.exists(dp) else {}
    site = d.get("url") or url
    if not site:
        return {"slug": sl, "name": name, "status": "no-url"}
    dom = lib.host(site)
    out = {"slug": sl, "name": name, "domain": dom, "checked": "2026-10-11"}
    try: out["trustpilot"] = tp(dom)
    except Exception as e: out["trustpilot"] = {"error": str(e)[:120]}
    try: out["propfirmmatch"] = pfm(name)
    except Exception as e: out["propfirmmatch"] = {"error": str(e)[:120]}
    os.makedirs(EXT, exist_ok=True)
    json.dump(out, open(os.path.join(EXT, sl + ".json"), "w"), indent=1)
    return {"slug": sl, "name": name, "status": "ok",
            "tp": (out.get("trustpilot") or {}).get("score"),
            "pfm": (out.get("propfirmmatch") or {}).get("score"),
            "tp_sup": bool((out.get("trustpilot") or {}).get("rating_suppressed"))}

if __name__ == "__main__":
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else len(F)
    batch = F[lo:hi]
    for i, en in enumerate(batch):
        r = job(en)
        print("[%d/%d] %-30s %-7s TP=%-5s PFM=%-5s %s" % (i + 1, len(batch), r.get("name", "?")[:30], r.get("status"),
              r.get("tp") or "-", r.get("pfm") or "-", "SUPPRESSED" if r.get("tp_sup") else ""), flush=True)
    print("DONE", lo, hi)
