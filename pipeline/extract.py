# -*- coding: utf-8 -*-
"""Phase 2 - evidence extraction. Reads raw/<slug>/ and writes data/<slug>.json.
Every finding stores the exact matched snippet + the source URL. Nothing is inferred.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from firms import F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW, DATA = os.path.join(ROOT, "raw"), os.path.join(ROOT, "data")

def load_pages(sl):
    d = os.path.join(RAW, sl)
    mp = os.path.join(d, "manifest.json")
    if not os.path.exists(mp): return None, []
    man = json.load(open(mp))
    out = []
    for p in man.get("pages", []):
        fp = os.path.join(d, p["file"])
        if not os.path.exists(fp): continue
        raw = open(fp, encoding="utf-8", errors="replace").read()
        txt = raw if p["kind"].endswith("jina") else lib.strip_html(raw)
        txt = re.sub(r"[ \t]+", " ", txt)
        out.append({"url": p["url"], "kind": p["kind"], "text": txt})
    return man, out

def sentences(text):
    return re.split(r"(?<=[.!?])\s+|\n", text)

def find(pat, pages, flags=re.I, window=170, limit=6):
    """Return list of {value, snippet, url} for regex pat (group 1 = value)."""
    res, seen = [], set()
    rx = re.compile(pat, flags)
    for p in pages:
        t = p["text"]
        for m in rx.finditer(t):
            v = (m.group(1) if m.groups() else m.group(0)).strip()
            key = re.sub(r"\W+", "", v.lower())
            if not v or key in seen: continue
            seen.add(key)
            a = max(0, m.start() - window // 2); b = min(len(t), m.end() + window)
            sn = re.sub(r"\s+", " ", t[a:b]).strip()
            res.append({"value": v[:120], "snippet": sn[:340], "url": p["url"], "kind": p["kind"]})
            if len(res) >= limit: return res
    return res

def uniq_findings(items):
    out, seen = [], set()
    for it in items:
        k = re.sub(r"\W+", "", it["value"].lower())
        if k in seen: continue
        seen.add(k); out.append(it)
    return out

PLATFORMS = ["MetaTrader 5","MetaTrader 4","MT5","MT4","cTrader","DXtrade","DXTrade","TradeLocker","Match-Trader",
             "Match Trader","MatchTrader","TradingView","Tradovate","NinjaTrader","Quantower","Sierra Chart","Rithmic",
             "ProjectX","Volumetrica","TradeSea","Tradesea","WealthCharts","ATAS","TradersYard"]
ASSETS = ["Forex","FX","Indices","Metals","Gold","Silver","Crypto","Energy","Oil","Commodities","Stocks","Equities",
          "Futures","CFD","Options","Bonds","ETFs"]
PROGRAMS = [("Instant Funding", r"instant funding"),("1-Step", r"1[- ]step|one[- ]step"),("2-Step", r"2[- ]step|two[- ]step"),
            ("3-Step", r"3[- ]step|three[- ]step"),("4-Step", r"4[- ]step|four[- ]step"),("Swing", r"swing account|swing trading account"),
            ("Pay-later", r"pay[- ]later|pay after you pass"),("Free trial / demo", r"free (challenge|trial)"),
            ("Futures", r"futures (account|challenge|evaluation)"),("Crypto", r"crypto (account|challenge)")]

def extract(sl, name, cat, url):
    man, pages = load_pages(sl)
    if not pages:
        return {"slug": sl, "name": name, "category": cat, "url": url, "status": "no-content",
                "findings": {}, "pages": [], "errors": (man or {}).get("errors", ["no manifest"])}
    blob = "\n".join(p["text"] for p in pages)
    F_ = {}
    F_["profit_target"] = find(r"profit target[^.]{0,40}?(\d{1,3}(?:\.\d+)?)\s?%", pages) or find(r"(\d{1,3}(?:\.\d+)?)\s?%[^.]{0,30}profit target", pages)
    F_["daily_loss"] = find(r"daily (?:loss|drawdown)[^.]{0,50}?(\d{1,3}(?:\.\d+)?)\s?%", pages) or find(r"(\d{1,3}(?:\.\d+)?)\s?%[^.]{0,25}daily (?:loss|drawdown)", pages)
    F_["max_drawdown"] = find(r"(?:max(?:imum)? (?:total |overall )?(?:loss|drawdown))[^.]{0,60}?(\d{1,3}(?:\.\d+)?)\s?%", pages) or find(r"(\d{1,3}(?:\.\d+)?)\s?%[^.]{0,30}(?:max(?:imum)? (?:total |overall )?(?:loss|drawdown))", pages)
    F_["profit_split"] = find(r"(\d{2,3})\s?%[^.]{0,40}(?:profit split|profit share|payout|split|revenue share)", pages) or find(r"(?:profit split|profit share|revenue share)[^.]{0,40}?(\d{2,3})\s?%", pages)
    F_["min_trading_days"] = find(r"(?:min(?:imum)?(?:\s+of)?\s+trading days|minimum days)[^.]{0,30}?(\d{1,2})", pages)
    F_["account_sizes"] = find(r"\$\s?(\d{1,3}(?:,\d{3})+|\d{1,4})\s?[Kk]\b", pages, limit=10)
    F_["prices"] = find(r"(?:€|\$|£)\s?(\d{1,4}(?:[.,]\d{2})?)", pages, limit=12)
    F_["drawdown_type"] = find(r"(static|trailing|end[- ]of[- ]day|EOD|intraday)\s*(?:drawdown|loss|max)", pages) or find(r"(?:drawdown|loss)[^.]{0,25}(static|trailing|end[- ]of[- ]day|EOD|intraday)", pages)
    F_["consistency"] = find(r"consistency (?:rule|requirement)[^.]{0,90}", pages) or find(r"(no|without) consistency rule", pages)
    F_["payout_frequency"] = find(r"(?:payouts?|withdrawals?)[^.]{0,50}?(daily|weekly|bi[- ]?weekly|biweekly|every \d+ days|monthly|on demand|anytime)", pages) or find(r"(daily|weekly|bi[- ]?weekly|biweekly|monthly) payouts?", pages)
    F_["payout_methods"] = find(r"(crypto|bank transfer|wire transfer|PayPal|Wise|Deel|Rise|Skrill|USDT|USDC)", pages, limit=8)
    F_["regulation"] = find(r"(not regulated|unregulated|regulated by|licensed by|authorised by|authorized by|FCA|CySEC|ASIC|CFTC|NFA|FSCA|BaFin|MAS|VFSC|FSC|CMA|SCA)[^.]{0,110}", pages, limit=8)
    F_["legal_entity"] = find(r"([A-Z][A-Za-z0-9&.,'\- ]{2,50}(?:Ltd|Limited|LLC|L\.L\.C|GmbH|B\.V|BV|FZCO|FZE|SIA|OÜ|SA|AG|Inc|SRL|S\.R\.L|Pty|DMCC|JSC|KFT|Sp\. z o\.o|doo|d\.o\.o))", pages, limit=8)
    F_["company_number"] = find(r"(?:company|registration|reg\.?)\s*(?:number|no\.?|#)\s*[:.]?\s*([A-Z0-9\-]{5,20})", pages)
    F_["restricted_countries"] = find(r"(?:restricted|not available|unavailable|prohibited)[^.]{0,30}(?:countries|jurisdictions|residents)[^.]{0,150}", pages) or find(r"(?:residents?|citizens?) of[^.]{0,150}(?:are not|cannot|not permitted|prohibited)", pages)
    F_["refund"] = find(r"refund[^.]{0,130}", pages, limit=4)
    F_["news_rule"] = find(r"news trading[^.]{0,140}", pages, limit=4) or find(r"(?:high[- ]impact|red folder|major) news[^.]{0,140}", pages, limit=4)
    F_["automation"] = find(r"(?:expert advisor|EA|algo(?:rithmic)?|bot|automated trading|HFT|high[- ]frequency)[^.]{0,120}", pages, limit=5)
    F_["vpn"] = find(r"(VPN|VPS|IP address)[^.]{0,110}", pages, limit=4)
    F_["contact_email"] = find(r"([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})", pages, limit=5)
    F_["payout_speed"] = find(r"(?:payouts?|withdrawals?)[^.]{0,60}?(within \d+[^.]{0,20}|in \d+[^.]{0,20}|instant|same day|24 hours|48 hours)", pages, limit=5)
    F_["leverage"] = find(r"(?:leverage)[^.]{0,40}?(1:\d{1,4})", pages, limit=6) or find(r"(1:\d{1,4})[^.]{0,25}leverage", pages, limit=6)
    F_["profit_cap"] = find(r"(?:profit cap|maximum payout|max payout|payout cap)[^.]{0,110}", pages, limit=4)
    F_["scaling"] = find(r"scaling (?:plan|program)[^.]{0,130}", pages, limit=3)
    F_["kyc"] = find(r"KYC[^.]{0,110}", pages, limit=3)
    F_["fees"] = find(r"(?:activation fee|monthly fee|subscription|platform fee|reset fee)[^.]{0,110}", pages, limit=5)
    # programs
    progs = []
    for label, pat in PROGRAMS:
        m = re.search(pat, blob, flags=re.I)
        if m:
            a = max(0, m.start() - 100); b = min(len(blob), m.end() + 160)
            progs.append({"name": label, "snippet": re.sub(r"\s+", " ", blob[a:b]).strip()[:300], "url": next((p["url"] for p in pages if re.search(pat, p["text"], re.I)), pages[0]["url"])})
    # platforms / assets
    plats = [x for x in PLATFORMS if re.search(r"\b" + re.escape(x) + r"\b", blob, re.I)]
    assets = [x for x in ASSETS if re.search(r"\b" + re.escape(x) + r"\b", blob, re.I)]
    # coupon codes
    codes = {}
    for m in re.finditer(r"(?:promo(?:tion)? code|discount code|coupon code|code)[:\s]{1,3}([A-Z0-9]{4,14})\b", blob):
        c = m.group(1)
        if c.isdigit(): continue
        codes.setdefault(c, re.sub(r"\s+", " ", blob[max(0, m.start() - 90):m.end() + 60]).strip()[:220])
    for m in re.finditer(r"\b([A-Z]{3,10}\d{2})\b(?=[^a-zA-Z]{0,20}(?:OFF|%))", blob):
        codes.setdefault(m.group(1), re.sub(r"\s+", " ", blob[max(0, m.start() - 90):m.end() + 90]).strip()[:220])
    # headline claims
    claims = []
    for m in re.finditer(r"(\d{1,3}(?:[.,]\d+)?\s?(?:K|M|\+)?\s*(?:traders|accounts|payouts?|countries|clients))", blob, re.I):
        s = re.sub(r"\s+", " ", blob[max(0, m.start() - 110):m.end() + 60]).strip()
        claims.append(s[:250])
        if len(claims) >= 6: break
    found = {k: uniq_findings(v) for k, v in F_.items()}
    found = {k: v for k, v in found.items() if v}
    return {"slug": sl, "name": name, "category": cat, "url": url,
            "status": "ok", "discovery": (man or {}).get("discovery"),
            "pages": [{"url": p["url"], "kind": p["kind"], "chars": len(p["text"])} for p in pages],
            "page_count": len(pages), "total_chars": len(blob),
            "findings": found, "programs": progs, "platforms": platforms_fix(plats), "assets": assets,
            "coupon_codes": [{"code": k, "context": v} for k, v in codes.items()],
            "claims": claims, "errors": (man or {}).get("errors", [])}

def platforms_fix(pl):
    out = []
    canon = {"MT5": "MetaTrader 5", "MT4": "MetaTrader 4", "DXTrade": "DXtrade", "MatchTrader": "Match-Trader",
             "Match Trader": "Match-Trader", "TradeSea": "TradeSea", "Tradesea": "TradeSea"}
    for p in pl:
        c = canon.get(p, p)
        if c not in out: out.append(c)
    return out

if __name__ == "__main__":
    os.makedirs(DATA, exist_ok=True)
    res = []
    for i, (name, url, cat) in enumerate(F):
        sl = lib.slug(name)
        try:
            d = extract(sl, name, cat, url)
        except Exception as e:
            d = {"slug": sl, "name": name, "category": cat, "url": url, "status": "error", "error": str(e)[:200]}
        json.dump(d, open(os.path.join(DATA, sl + ".json"), "w"), indent=1)
        nf = len(d.get("findings", {}))
        res.append({"slug": sl, "name": name, "status": d.get("status"), "pages": d.get("page_count", 0), "categories": nf})
        print("[%3d/%d] %-32s %-9s pages=%-3s cats=%s" % (i + 1, len(F), name[:32], d.get("status"), d.get("page_count", 0), nf), flush=True)
    json.dump(res, open(os.path.join(ROOT, "data", "_extract_summary.json"), "w"), indent=1)
    print("DONE")
