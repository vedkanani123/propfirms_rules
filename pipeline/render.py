# -*- coding: utf-8 -*-
"""Phase 4 - render one standalone HTML research report per firm + an index."""
import json, os, re, sys, html, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib, tpl
from firms import F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA, EXT, OUT = os.path.join(ROOT, "data"), os.path.join(ROOT, "external"), os.path.join(ROOT, "reports")
TODAY = "2026-10-11"

def e(s): return html.escape(str(s if s is not None else ""), quote=True)

def badge(kind):
    m = {"verified": ("ok", "Found on official page"), "advertised": ("acc", "Company claim"),
         "external": ("pur", "Third-party source"), "missing": ("warn", "Not found publicly"),
         "conflict": ("bad", "Needs confirmation")}
    c, t = m.get(kind, ("", kind))
    return '<span class="b %s">%s</span>' % (c, e(t))

def ev_block(items, cap=4):
    if not items: return '<p class="sm mu">No supporting text captured.</p>'
    out = []
    for it in items[:cap]:
        out.append('<div class="quote">&ldquo;%s&rdquo;<br><span class="sm">&mdash; <a href="%s" target="_blank" rel="noopener noreferrer">%s</a></span></div>'
                   % (e(it.get("snippet") or it.get("value")), e(it.get("url", "#")), e(re.sub(r"^https?://", "", it.get("url", ""))[:90])))
    return "".join(out)

def sec(n, title, body, sub=""):
    return ('<section id="%s"><h2><span class="n">%s</span>%s</h2>%s%s</section>'
            % (n, n, e(title), ('<p class="lead">%s</p>' % sub) if sub else "", body))

def finding_card(label, items, kind, note=""):
    if items:
        vals = "<br>".join("<strong>%s</strong>" % e(i["value"]) for i in items[:5])
        body = '<div class="quote">&ldquo;%s&rdquo;<br><span class="sm">&mdash; <a href="%s" target="_blank" rel="noopener noreferrer">%s</a></span></div>' % (
            e(items[0].get("snippet") or items[0]["value"]), e(items[0].get("url", "#")), e(re.sub(r"^https?://", "", items[0].get("url", ""))[:80]))
        return '<div class="stat"><div class="k">%s %s</div><div class="v" style="font-size:1rem">%s</div><div class="x">%s</div>%s</div>' % (e(label), badge(kind), vals, e(note), body)
    return '<div class="stat"><div class="k">%s %s</div><div class="v" style="font-size:.95rem;color:var(--mu)">Not found on the public pages we crawled</div><div class="x">%s</div></div>' % (e(label), badge("missing"), e(note))

CATS = [
  ("profit_target", "Profit target(s)", "The evaluation profit target percentage(s) stated on the firm's own pages."),
  ("daily_loss", "Daily loss / daily drawdown", "The maximum loss allowed in a single day."),
  ("max_drawdown", "Maximum total drawdown", "The overall loss limit for the account."),
  ("drawdown_type", "Drawdown mechanism", "Static, trailing, end-of-day or intraday - the single most consequential risk rule."),
  ("consistency", "Consistency rule", "Whether a single big day can block a payout."),
  ("min_trading_days", "Minimum trading days", "How many days must be traded before a phase or payout is valid."),
  ("profit_split", "Profit split", "The share of simulated profit paid to the trader."),
  ("payout_frequency", "Payout frequency", "How often a withdrawal can be requested."),
  ("payout_methods", "Payout methods", "How the firm actually pays out."),
  ("payout_speed", "Payout processing speed", "Stated time to process a withdrawal."),
  ("profit_cap", "Profit / payout cap", "Any maximum withdrawal or per-cycle limit."),
  ("account_sizes", "Account sizes", "Advertised funding levels."),
  ("prices", "Prices and fees", "Advertised challenge fees in the currency shown."),
  ("fees", "Recurring / activation fees", "Subscription, activation, reset or platform charges."),
  ("refund", "Refund policy", "Whether the challenge fee can be recovered."),
  ("news_rule", "News trading rule", "Restrictions around high-impact economic events."),
  ("automation", "Automation / EAs / bots", "Whether algorithmic trading is allowed."),
  ("vpn", "VPN / VPS / IP policy", "Access and device restrictions."),
  ("leverage", "Leverage", "Maximum leverage by asset class."),
  ("regulation", "Regulation and licensing", "Any claimed licence, regulator or explicit non-regulation statement."),
  ("legal_entity", "Legal entity", "The company you actually contract with."),
  ("company_number", "Company registration number", "Registry identifier, if published."),
  ("restricted_countries", "Restricted countries", "Where the firm will not accept clients."),
  ("kyc", "KYC / verification", "Identity and AML requirements."),
  ("scaling", "Scaling plan", "How the account grows."),
]

def build_report(d, ext):
    name = d.get("name") or "Firm"
    slug = d.get("slug")
    url = d.get("url") or ""
    cat = d.get("category") or ""
    f = d.get("findings") or {}
    pages = d.get("pages") or []
    found = sum(1 for k, _, _ in CATS if f.get(k))
    total = len(CATS)
    cov = int(round(found / total * 100))
    ext = ext or {}
    tp = ext.get("trustpilot") or {}
    pfm = ext.get("propfirmmatch") or {}
    parts = []
    # ---- hero
    stats = [
        ("Official site", url.replace("https://", "").replace("http://", "").rstrip("/") or "not resolved", "Resolved from the supplied list or discovered and verified", True),
        ("Pages crawled", str(d.get("page_count") or 0), "%s characters of official text analysed" % f"{(d.get('total_chars') or 0):,}"),
        ("Rule categories found", "%d of %d" % (found, total), "%d%% of the checklist had at least one public statement" % cov),
        ("Trustpilot", (tp.get("score") or "no profile") + (" (suppressed)" if tp.get("rating_suppressed") else ""), (str(tp.get("review_count") or "-") + " reviews recorded") if tp else "No independent rating retrieved"),
        ("PropFirmMatch", (pfm.get("score") or "no profile"), (str(pfm.get("review_count") or "-") + " reviews") if pfm else "No third-party profile retrieved"),
        ("Category", cat, "As classified in the source directory"),
    ]
    hero = '<div class="grid g4">' + "".join(
        '<div class="stat%s"><div class="k">%s</div><div class="v" style="font-size:1rem">%s</div><div class="x">%s</div></div>'
        % (" hl" if (len(s) > 3 and s[3]) else "", e(s[0]), e(s[1]), e(s[2])) for s in stats) + "</div>"
    parts.append('<section id="top"><h1>%s &mdash; Interactive Research Report</h1>' % e(name))
    parts.append('<p class="lead">Automated, evidence-first research pass over the firm\'s own public website, produced %s. Every value below is quoted from a real page and links to its source. Nothing is inferred, and anything not found is labelled <em>Not found publicly</em>.</p>' % TODAY)
    parts.append('<div class="note warn"><span class="nt">Read this first</span>This is an <strong>automated extraction</strong>, not a hand-audited legal review and not affiliated with the firm. Percentages and fees are quoted from marketing and help pages and may be context-specific, outdated, or superseded by the firm\'s terms. Always open the linked source and the firm\'s Terms before paying. No purchase, login or payment was performed.</div>')
    parts.append(hero)
    parts.append('<div class="row" style="margin-top:10px"><span class="b ok">Found on official page</span><span class="b acc">Company claim</span><span class="b pur">Third-party source</span><span class="b warn">Not found publicly</span></div>')
    parts.append('</section>')
    # ---- coverage
    cov_rows = "".join(
        '<tr><td>%s</td><td>%s</td><td>%s</td><td class="sm mu">%s</td></tr>' % (
            e(label), badge("verified" if f.get(key) else "missing"),
            e(", ".join(i["value"] for i in (f.get(key) or [])[:3]) or "&mdash;"), e(desc))
        for key, label, desc in CATS)
    parts.append(sec("c1", "Coverage checklist", '<div class="tw"><table><thead><tr><th>Rule / fact</th><th>Status</th><th>Value captured</th><th>What this covers</th></tr></thead><tbody>%s</tbody></table></div>' % cov_rows,
                     "What the crawl could and could not establish from public pages. A &lsquo;not found&rsquo; row means the firm does not publish it in an easily crawlable place - it does not mean the rule does not exist."))
    return parts, found, total

def more_sections(d, ext):
    f = d.get("findings") or {}
    name = d.get("name") or "Firm"
    P = []
    # ---- company
    body = '<div class="grid g3">'
    body += finding_card("Legal entity", f.get("legal_entity"), "verified", "Companies named in the site text. Incorporation is not regulation.")
    body += finding_card("Registration number", f.get("company_number"), "verified", "Registry identifier if published.")
    body += finding_card("Regulation", f.get("regulation"), "verified", "Any licence claim, regulator name, or explicit non-regulation statement.")
    body += finding_card("Restricted countries", f.get("restricted_countries"), "verified", "Jurisdictions the firm excludes.")
    body += finding_card("Contact", f.get("contact_email"), "verified", "Support email addresses found on the site.")
    body += '</div>'
    P.append(sec("c2", "Company, legal and eligibility", body, "Who you contract with, and where the firm says it will not operate."))
    # ---- programs
    progs = d.get("programs") or []
    if progs:
        rows = "".join('<tr><td><strong>%s</strong></td><td class="sm">%s</td><td class="sm"><a href="%s" target="_blank" rel="noopener noreferrer">source</a></td></tr>'
                       % (e(p["name"]), e(p["snippet"]), e(p["url"])) for p in progs)
        body = '<div class="tw"><table><thead><tr><th>Programme detected</th><th>Supporting text from the site</th><th>Source</th></tr></thead><tbody>%s</tbody></table></div>' % rows
    else:
        body = '<div class="note warn"><span class="nt">No programme keywords matched</span>The crawl did not find the usual evaluation-model keywords (1-Step, 2-Step, Instant Funding, Futures, Crypto). This often means the site is JavaScript-rendered, or the firm is not a retail challenge provider.</div>'
    P.append(sec("c3", "Programmes and account models", body, "Which evaluation models the firm advertises, detected from its own page text."))
    # ---- rules
    body = '<div class="grid g2">'
    for key, label, note in [("profit_target", "Profit target", "Percentage(s) quoted from the firm's own pages."),
                             ("daily_loss", "Daily loss limit", "Maximum single-day loss."),
                             ("max_drawdown", "Maximum drawdown", "Overall account loss limit."),
                             ("drawdown_type", "Drawdown mechanism", "Static vs trailing changes everything about how hard the account is."),
                             ("consistency", "Consistency rule", "Whether one large day can block a payout."),
                             ("min_trading_days", "Minimum trading days", "Days that must be traded."),
                             ("leverage", "Leverage", "Maximum leverage mentioned."),
                             ("news_rule", "News trading", "Restrictions around high-impact events."),
                             ("automation", "Automation / EAs", "Algorithmic trading policy."),
                             ("vpn", "VPN / VPS / IP", "Access restrictions.")]:
        body += finding_card(label, f.get(key), "verified", note)
    body += '</div>'
    P.append(sec("c4", "Trading and risk rules", body,
                 "Extracted verbatim. Where a figure appears here it was stated on an official page; where it does not, the firm does not publish it in a crawlable location. Percentages can differ between programmes and phases - open the linked source for context."))
    # ---- payouts
    body = '<div class="grid g2">'
    for key, label, note in [("profit_split", "Profit split", "Share of simulated profit paid to the trader."),
                             ("payout_frequency", "Payout frequency", "How often a withdrawal can be requested."),
                             ("payout_speed", "Processing speed", "Stated processing time after a request."),
                             ("payout_methods", "Payout methods", "Channels the firm mentions."),
                             ("profit_cap", "Profit / payout cap", "Any maximum withdrawal."),
                             ("refund", "Refunds", "Whether the fee is recoverable."),
                             ("fees", "Recurring / other fees", "Subscription, activation or reset charges."),
                             ("kyc", "KYC / verification", "Identity requirements."),
                             ("scaling", "Scaling plan", "Account growth conditions."),
                             ("account_sizes", "Account sizes", "Advertised funding levels.")]:
        body += finding_card(label, f.get(key), "verified", note)
    body += '</div>'
    P.append(sec("c5", "Payouts, fees and growth", body,
                 "Payout terms are where most disputes happen. Read the exact wording at the linked source rather than the headline number."))
    # ---- platforms
    pl = d.get("platforms") or []
    as_ = d.get("assets") or []
    body = '<div class="grid g3"><div class="stat"><div class="k">Platforms detected</div><div class="v" style="font-size:1rem">%s</div><div class="x">Names appearing in the crawled page text.</div></div>' % (e(", ".join(pl)) if pl else '<span class="mu">None detected</span>')
    body += '<div class="stat"><div class="k">Asset classes detected</div><div class="v" style="font-size:1rem">%s</div><div class="x">Mentioned on the firm\'s pages; not a confirmed tradable instrument list.</div></div>' % (e(", ".join(as_)) if as_ else '<span class="mu">None detected</span>')
    body += '</div>'
    P.append(sec("c6", "Platforms and instruments", body, "Detected from page text only. A platform being named is not proof it is available in your region."))
    # ---- promotions
    codes = d.get("coupon_codes") or []
    if codes:
        rows = "".join('<tr><td><code>%s</code></td><td class="sm">%s</td></tr>' % (e(c["code"]), e(c["context"])) for c in codes)
        body = '<div class="note warn"><span class="nt">Unverified codes</span>These strings look like promo codes in the crawled text. <strong>None were tested at checkout.</strong> A code found in site text or on an affiliate page may be expired, region-locked or ineligible for your account type.</div><div class="tw"><table><thead><tr><th>Code string</th><th>Surrounding text</th></tr></thead><tbody>%s</tbody></table></div>' % rows
    else:
        body = '<div class="note"><span class="nt">No code strings detected</span>No obvious promo-code pattern was found in the crawled pages. The firm may run offers through email or social channels that are not crawlable.</div>'
    P.append(sec("c7", "Promotions and discount codes", body))
    return P

def tail_sections(d, ext):
    f = d.get("findings") or {}
    name = d.get("name") or "Firm"
    P = []
    tp = (ext or {}).get("trustpilot") or {}
    pfm = (ext or {}).get("propfirmmatch") or {}
    body = '<div class="grid g2">'
    if tp and tp.get("score"):
        extra = '<div class="note bad"><span class="nt">Rating suppressed by Trustpilot</span>Trustpilot is displaying a warning that this company\'s rating is unavailable because of a breach of Trustpilot\'s guidelines. The underlying score shown here is embedded in the page but is not currently displayed publicly.</div>' if tp.get("rating_suppressed") else ""
        themes = "".join("<li>%s</li>" % e(t) for t in (tp.get("themes") or [])[:6]) or "<li>No specific complaint text captured.</li>"
        body += ('<div class="calc"><h3 style="margin-top:0">Trustpilot</h3><div class="grid g3"><div class="stat"><div class="k">Score</div><div class="v">%s</div></div>'
                 '<div class="stat"><div class="k">Reviews recorded</div><div class="v">%s</div></div>'
                 '<div class="stat"><div class="k">Rating suppressed</div><div class="v">%s</div></div></div>%s'
                 '<p class="sm mu" style="margin-top:8px">Complaint keywords captured: </p><ul class="tight sm">%s</ul>'
                 '<p class="sm"><a href="%s" target="_blank" rel="noopener noreferrer">Open the Trustpilot profile &rarr;</a></p></div>'
                 % (e(tp.get("score")), e(tp.get("review_count") or "-"), "Yes" if tp.get("rating_suppressed") else "No", extra, themes, e(tp.get("url", ""))))
    else:
        body += '<div class="calc"><h3 style="margin-top:0">Trustpilot</h3><p class="sm mu">No Trustpilot profile with a numeric score could be retrieved for this domain. That is not a clean bill of health - it means no signal was found.</p></div>'
    if pfm and pfm.get("score"):
        body += ('<div class="calc"><h3 style="margin-top:0">PropFirmMatch (affiliate marketplace)</h3><div class="grid g3">'
                 '<div class="stat"><div class="k">Score</div><div class="v">%s</div></div>'
                 '<div class="stat"><div class="k">Reviews</div><div class="v">%s</div></div>'
                 '<div class="stat"><div class="k">Country</div><div class="v" style="font-size:1rem">%s</div></div>'
                 '<div class="stat"><div class="k">Max allocation</div><div class="v" style="font-size:1rem">%s</div></div>'
                 '<div class="stat"><div class="k">Promo listed</div><div class="v" style="font-size:1rem">%s</div></div>'
                 '<div class="stat"><div class="k">Code(s) listed</div><div class="v" style="font-size:1rem">%s</div></div></div>'
                 '<div class="note warn"><span class="nt">Credibility limitation</span>PropFirmMatch is a commercial marketplace with affiliate buy-links, exclusive discount codes and a review-bounty programme. Ratings and payouts shown there may be incentivised and are not independent verification.</div>'
                 '<p class="sm"><a href="%s" target="_blank" rel="noopener noreferrer">Open the PropFirmMatch profile &rarr;</a></p></div>'
                 % (e(pfm.get("score")), e(pfm.get("review_count") or "-"), e(pfm.get("country") or "-"), e(pfm.get("max_allocation") or "-"),
                    e(pfm.get("promo_off") or "-"), e(", ".join(pfm.get("promo_codes") or []) or "-"), e(pfm.get("url", ""))))
    else:
        body += '<div class="calc"><h3 style="margin-top:0">PropFirmMatch</h3><p class="sm mu">No PropFirmMatch profile retrieved. Many smaller firms are not listed there.</p></div>'
    body += '</div>'
    P.append(sec("c8", "Independent reputation signals", body,
                 "Third-party ratings retrieved on %s. Review platforms are not regulators, and affiliate marketplaces are not neutral. Treat these as signals, not proof." % TODAY))
    claims = d.get("claims") or []
    if claims:
        P.append(sec("c9", "Marketing claims captured", '<ul class="tight">%s</ul>' % "".join("<li>%s</li>" % e(c) for c in claims),
                     "Statements lifted directly from the firm's pages. These are company claims, not audited figures."))
    # ---- evidence table
    rows = []
    for key, label, _ in CATS:
        items = f.get(key) or []
        if items:
            rows.append('<tr><td><strong>%s</strong></td><td>%s</td><td class="sm">%s</td><td class="sm"><a href="%s" target="_blank" rel="noopener noreferrer">%s</a></td></tr>'
                        % (e(label), e(", ".join(i["value"] for i in items[:4])), e(items[0].get("snippet", "")[:300]),
                           e(items[0].get("url", "#")), e(re.sub(r"^https?://", "", items[0].get("url", ""))[:70])))
    body = ('<div class="tw"><table><thead><tr><th>Category</th><th>Value(s) captured</th><th>Exact quote</th><th>Source</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(rows)) if rows else '<p class="mu">No categories produced evidence.</p>'
    P.append(sec("c10", "Evidence trail", body, "Every captured value with the exact text it came from and the page it came from. Use this to verify any number before relying on it."))
    # ---- sources
    pages = d.get("pages") or []
    if pages:
        srows = "".join('<tr><td class="sm"><a href="%s" target="_blank" rel="noopener noreferrer">%s</a></td><td class="sm">%s</td><td class="sm">%s</td></tr>'
                        % (e(p["url"]), e(p["url"][:110]), e(p.get("kind", "")), f"{p.get('chars', 0):,}") for p in pages[:60])
        body = '<div class="tw"><table><thead><tr><th>Page fetched</th><th>Type</th><th>Characters</th></tr></thead><tbody>%s</tbody></table></div>' % srows
    else:
        body = '<div class="note bad"><span class="nt">No official page could be retrieved</span>%s</div>' % e("; ".join((d.get("errors") or ["unknown"])[:4]))
    P.append(sec("c11", "Sources fetched", body, "Every URL this report was built from. Links open in a new tab."))
    # ---- unresolved
    miss = [label for key, label, _ in CATS if not f.get(key)]
    qs = [
        "What are the exact profit target, daily loss and maximum drawdown percentages for each programme and phase, and is the maximum drawdown static or trailing?",
        "What is the default profit split, and what does it cost to raise it?",
        "When is the first payout request allowed, and what is the minimum amount?",
        "Is there a consistency rule or any maximum payout cap, now or in the contract?",
        "Which trading strategies, news windows and automation are prohibited, and is a breach hard or soft?",
        "Which jurisdictions are restricted, and which platforms are unavailable in my country?",
        "Are the fees one-off or recurring, and under what conditions is the challenge fee refunded?",
        "Can the firm change risk parameters, reduce leverage or withhold a reward at its own discretion?",
    ]
    body = ('<div class="note warn"><span class="nt">%d of %d checklist items had no public answer</span>These are the questions this crawl could not answer from public pages: <em>%s</em>. The message below bundles them for support.</div>'
            % (len(miss), len(CATS), e(", ".join(miss))))
    body += '<ul class="tight">' + "".join("<li>%s</li>" % e(q) for q in qs) + "</ul>"
    msg = "Hello %s support,\n\nI am reviewing your published terms before purchasing. Please confirm in writing:\n\n" % name
    msg += "\n".join("%d) %s" % (i + 1, q) for i, q in enumerate(qs))
    msg += "\n\nPlease also confirm the exact total I would be charged, in which currency, and whether any add-ons or promotional codes are included.\n\nThank you."
    body += ('<h3>Copyable message to support</h3><textarea id="sm" readonly rows="11" style="width:100%%;font-family:var(--mono);'
             'font-size:.76rem;background:var(--panel2);color:var(--tx);border:1px solid var(--bd2);border-radius:9px;padding:10px">%s</textarea>' % e(msg))
    body += '<div class="row" style="margin-top:7px"><button type="button" id="cp" class="primary">Copy support message</button></div>'
    P.append(sec("c12", "Unresolved questions and conflicts", body))
    # ---- methodology
    body = ('<div class="grid g2"><div class="calc"><h3 style="margin-top:0">How this report was produced</h3><ul class="tight sm">'
            '<li>The official domain was taken from the supplied directory list, or discovered and then <strong>verified</strong> by matching the firm name plus prop-firm vocabulary on the homepage.</li>'
            '<li>The homepage, its sitemap(s) and up to twelve keyword-ranked internal pages were fetched, plus help/support subdomains where they exist.</li>'
            '<li>Page text was extracted locally and matched against a fixed rule vocabulary. Every match stores the exact sentence and its URL.</li>'
            '<li>Trustpilot and PropFirmMatch were read through a public text-reader proxy. Reddit and other blocked sources were not used here.</li>'
            '<li>No login, no account creation, no purchase, no payment data, and no attempt to bypass access controls.</li></ul></div>'
            '<div class="calc"><h3 style="margin-top:0">Known limitations</h3><ul class="tight sm">'
            '<li>Extraction is <strong>pattern-based</strong>. A percentage shown here is the figure the firm published on that page - it may belong to a different programme than the one you are considering.</li>'
            '<li>JavaScript-only sites can hide most rules from a crawler, producing &lsquo;not found&rsquo; where a rule does exist.</li>'
            '<li>Marketing pages are not contracts. The Terms &amp; Conditions govern, and they were not always retrievable.</li>'
            '<li>No live checkout price, no coupon validation and no payout confirmation was performed.</li>'
            '<li>Review-platform data is third-party and, for affiliate marketplaces, commercially incentivised.</li></ul></div></div>')
    P.append(sec("c13", "Method and limitations", body))
    return P

JS = """
(function(){var b=document.getElementById('th'),r=document.documentElement;
function set(t){r.setAttribute('data-theme',t);try{localStorage.setItem('pf-theme',t)}catch(e){}}
try{var s=localStorage.getItem('pf-theme');if(s)r.setAttribute('data-theme',s)}catch(e){}
if(b)b.onclick=function(){set(r.getAttribute('data-theme')==='dark'?'light':'dark')};
var p=document.getElementById('pb');if(p)p.onclick=function(){window.print()};
var c=document.getElementById('cp');if(c)c.onclick=function(){var t=document.getElementById('sm');
 t.removeAttribute('readonly');t.select();t.setSelectionRange(0,999999);var ok=false;
 try{ok=document.execCommand('copy')}catch(e){}
 if(navigator.clipboard){try{navigator.clipboard.writeText(t.value)}catch(e){}}
 t.setAttribute('readonly','');c.textContent=ok?'Copied':'Select & copy';setTimeout(function(){c.textContent='Copy support message'},1600)};
var u=document.getElementById('up');if(u)u.onclick=function(){window.scrollTo({top:0,behavior:'smooth'})};
})();
"""

def page(title, inner, extra_head=""):
    return ("<!DOCTYPE html>\n<html lang=\"en\" data-theme=\"dark\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<title>%s</title>\n<meta name=\"robots\" content=\"noindex\">\n<style>%s</style>%s\n</head>\n<body>\n"
            "<header><div class=\"wrap hin\"><div class=\"brand\"><span class=\"dot\"></span>%s</div>\n"
            "<nav><a href=\"#c1\">Coverage</a><a href=\"#c2\">Company</a><a href=\"#c3\">Programmes</a><a href=\"#c4\">Rules</a>"
            "<a href=\"#c5\">Payouts</a><a href=\"#c6\">Platforms</a><a href=\"#c7\">Promos</a><a href=\"#c8\">Reputation</a>"
            "<a href=\"#c10\">Evidence</a><a href=\"#c11\">Sources</a><a href=\"#c12\">Questions</a></nav>\n"
            "<div class=\"tools\"><button id=\"th\" type=\"button\">Theme</button><button id=\"pb\" type=\"button\">PDF</button>"
            "<a class=\"btn\" href=\"index.html\">All firms</a></div></div></header>\n<main class=\"wrap\">%s</main>\n"
            "<footer><div class=\"wrap\">Independent automated research &middot; generated %s &middot; not affiliated with, endorsed by or verified by %s. "
            "No purchase, login or payment was performed. Figures are quoted from public pages and must be re-checked against the firm's current Terms before you buy. "
            "<button id=\"up\" type=\"button\" style=\"margin-top:8px\">Back to top</button></div></footer>\n<script>%s</script>\n</body>\n</html>\n"
            % (e(title), tpl.CSS, extra_head, e(title.split(" - ")[0]), inner, TODAY, e(title.split(" - ")[0]), JS))

def write_one(slug):
    dp = os.path.join(DATA, slug + ".json")
    if not os.path.exists(dp): return None
    d = json.load(open(dp))
    ep = os.path.join(EXT, slug + ".json")
    ext = json.load(open(ep)) if os.path.exists(ep) else {}
    parts, found, total = build_report(d, ext)
    parts += more_sections(d, ext)
    parts += tail_sections(d, ext)
    title = "%s - Prop Firm Research Report (%s)" % (d.get("name"), TODAY)
    open(os.path.join(OUT, slug + ".html"), "w", encoding="utf-8").write(page(title, "".join(parts)))
    return {"slug": slug, "name": d.get("name"), "cat": d.get("category"), "url": d.get("url"),
            "status": d.get("status"), "pages": d.get("page_count", 0), "found": found, "total": total,
            "cov": int(round(found / total * 100)),
            "tp": ((ext.get("trustpilot") or {}).get("score")), "tp_sup": bool((ext.get("trustpilot") or {}).get("rating_suppressed")),
            "pfm": ((ext.get("propfirmmatch") or {}).get("score"))}

def index_page(rows):
    ok = [r for r in rows if r["status"] == "ok"]
    nr = [r for r in rows if r["status"] != "ok"]
    tr = "".join(
        '<tr><td><a href="%s.html">%s</a></td><td class="sm">%s</td><td class="sm"><a href="%s" target="_blank" rel="noopener noreferrer">%s</a></td>'
        '<td class="sm">%s</td><td class="sm">%s</td><td class="sm">%s%s</td><td class="sm">%s</td></tr>'
        % (e(r["slug"]), e(r["name"]), e(r["cat"]), e(r["url"] or "#"), e((r["url"] or "-").replace("https://", "")[:44]),
           r["pages"], "%d/%d (%d%%)" % (r["found"], r["total"], r["cov"]),
           e(r["tp"] or "-"), " <span class=\"b bad\">suppressed</span>" if r["tp_sup"] else "", e(r["pfm"] or "-"))
        for r in sorted(ok, key=lambda x: (-x["cov"], x["name"])))
    trn = "".join('<tr><td>%s</td><td class="sm">%s</td><td class="sm">%s</td></tr>' % (e(r["name"]), e(r["cat"]), "No official site could be resolved and verified" if r["status"] == "unresolved" else "Site resolved but no content retrieved") for r in sorted(nr, key=lambda x: x["name"]))
    avg = int(round(sum(r["cov"] for r in ok) / len(ok))) if ok else 0
    inner = ('<section id="top"><h1>Prop Firm Research Index</h1>'
             '<p class="lead">Automated, evidence-first research reports on <strong>%d firms</strong>, generated %s. Each report is a standalone HTML file. Open any firm to see exactly what its own public pages say about rules, risk, payouts and fees, with the source link for every figure.</p>'
             '<div class="grid g4"><div class="stat hl"><div class="k">Reports generated</div><div class="v">%d</div><div class="x">One standalone HTML file per firm</div></div>'
             '<div class="stat"><div class="k">Average coverage</div><div class="v">%d%%</div><div class="x">Share of the 25-point rule checklist answered from public pages</div></div>'
             '<div class="stat"><div class="k">Sites unreachable</div><div class="v">%d</div><div class="x">No official domain could be resolved and verified</div></div>'
             '<div class="stat"><div class="k">BrightFunded</div><div class="v" style="font-size:1rem">Separate deep report</div><div class="x">Already delivered as a hand-built dashboard</div></div></div>'
             '<div class="note warn"><span class="nt">How to use this index</span>Coverage percentage is a <em>discovery</em> metric, not a quality score - a low number usually means the site is JavaScript-only or hides rules behind a login. Every report states plainly what could not be found. Nothing here is affiliated with the firms listed.</div></section>'
             '<section id="c1"><h2><span class="n">1</span>Reports</h2><div class="tw"><table><thead><tr><th>Firm</th><th>Category</th><th>Website</th><th>Pages</th><th>Coverage</th><th>Trustpilot</th><th>PFM</th></tr></thead><tbody>%s</tbody></table></div></section>'
             '<section id="c2"><h2><span class="n">2</span>No report generated</h2><div class="tw"><table><thead><tr><th>Firm</th><th>Category</th><th>Reason</th></tr></thead><tbody>%s</tbody></table></div></section>'
             % (len(ok), TODAY, len(ok), avg, len(nr), tr, trn))
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page("Prop Firm Research Index (%s)" % TODAY, inner))

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for i, (name, url, cat) in enumerate(F):
        sl = lib.slug(name)
        try: r = write_one(sl)
        except Exception as ex: r = None; print("ERR", name, ex)
        if r: rows.append(r)
        if (i + 1) % 25 == 0: print("rendered", i + 1, flush=True)
    json.dump(rows, open(os.path.join(OUT, "_index.json"), "w"), indent=1)
    index_page(rows)
    print("reports:", len(rows), "ok:", sum(1 for r in rows if r["status"] == "ok"))
