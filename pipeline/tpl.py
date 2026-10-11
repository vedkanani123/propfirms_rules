# -*- coding: utf-8 -*-
"""Shared HTML template for the per-firm research reports."""
CSS = """
:root{--font:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,Arial,sans-serif;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
--r:13px;--rl:19px;--maxw:1200px;--ok:#22c07a;--warn:#f0a637;--bad:#f0524d;--info:#4f8ef7;--pur:#a273f7}
html[data-theme=dark]{--bg:#0a0d14;--panel:#131a25;--panel2:#182130;--panel3:#1e2939;--bd:#25303f;--bd2:#2f3d50;
--tx:#e9eef7;--mu:#9aa8bd;--mu2:#71809a;--ac:#4f8ef7;--acs:rgba(79,142,247,.14);--sh:0 10px 28px rgba(0,0,0,.45);--cb:#0b1017}
html[data-theme=light]{--bg:#f4f6fa;--panel:#fff;--panel2:#f7f9fc;--panel3:#eef2f8;--bd:#dde4ee;--bd2:#c9d4e4;
--tx:#111827;--mu:#5a6a80;--mu2:#7d8ba0;--ac:#1f66e0;--acs:rgba(31,102,224,.10);--sh:0 8px 24px rgba(19,38,66,.10);--cb:#f1f4f9}
*{box-sizing:border-box}html,body{margin:0;padding:0}
body{background:var(--bg);color:var(--tx);font-family:var(--font);font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased;overflow-x:hidden}
a{color:var(--ac);text-decoration:none}a:hover{text-decoration:underline}
h1,h2,h3,h4{line-height:1.25;margin:0 0 .4em}h1{font-size:clamp(1.4rem,3.6vw,2rem);letter-spacing:-.02em}h2{font-size:clamp(1.12rem,2.4vw,1.45rem)}h3{font-size:1.02rem}
p{margin:0 0 .85em}code{font-family:var(--mono);font-size:.86em;background:var(--cb);border:1px solid var(--bd);border-radius:6px;padding:.1em .4em}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 15px}
header{position:sticky;top:0;z-index:50;background:var(--bg);border-bottom:1px solid var(--bd)}
.hin{display:flex;gap:12px;align-items:center;min-height:56px;flex-wrap:wrap}
.brand{font-weight:750;letter-spacing:-.02em;display:flex;gap:9px;align-items:center;white-space:nowrap}
.dot{width:10px;height:10px;border-radius:50%;background:linear-gradient(135deg,#4f8ef7,#a273f7)}
nav{display:flex;gap:3px;overflow-x:auto;flex:1 1 300px}
nav a{color:var(--mu);font-size:.8rem;padding:5px 9px;border-radius:999px;white-space:nowrap}
nav a:hover{background:var(--panel2);color:var(--tx);text-decoration:none}
.tools{margin-left:auto;display:flex;gap:7px}
button,.btn{font-family:inherit;font-size:.82rem;font-weight:600;color:var(--tx);background:var(--panel2);border:1px solid var(--bd2);border-radius:9px;padding:6px 11px;cursor:pointer;display:inline-flex;gap:6px;align-items:center;text-decoration:none;white-space:nowrap}
button:hover,.btn:hover{border-color:var(--ac);text-decoration:none}button.primary{background:var(--ac);border-color:var(--ac);color:#fff}
button:focus-visible,a:focus-visible{outline:2px solid var(--ac);outline-offset:2px}
main{padding:20px 0 60px}
section{background:var(--panel);border:1px solid var(--bd);border-radius:var(--rl);padding:18px;margin-bottom:18px;box-shadow:var(--sh);scroll-margin-top:72px}
section>h2{display:flex;gap:9px;align-items:center;flex-wrap:wrap}
.n{font-size:.68rem;font-weight:800;color:var(--ac);background:var(--acs);border:1px solid color-mix(in srgb,var(--ac) 35%,transparent);padding:2px 8px;border-radius:999px;letter-spacing:.05em}
.lead{color:var(--mu);font-size:.92rem;max-width:95ch}
.grid{display:grid;gap:11px}.g2{grid-template-columns:repeat(auto-fit,minmax(255px,1fr))}.g3{grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}.g4{grid-template-columns:repeat(auto-fit,minmax(155px,1fr))}
.stat{background:var(--panel2);border:1px solid var(--bd);border-radius:var(--r);padding:11px 12px}
.stat .k{font-size:.71rem;text-transform:uppercase;letter-spacing:.05em;color:var(--mu);font-weight:700}
.stat .v{font-size:1.12rem;font-weight:800;margin-top:4px;word-break:break-word}
.stat .x{font-size:.75rem;color:var(--mu2);margin-top:3px}
.stat.hl{border-color:color-mix(in srgb,var(--ac) 40%,transparent);background:var(--acs)}
.b{display:inline-block;font-size:.64rem;font-weight:800;letter-spacing:.05em;text-transform:uppercase;padding:2px 7px;border-radius:999px;border:1px solid var(--bd2);color:var(--mu);background:var(--panel3)}
.b.ok{color:var(--ok);border-color:color-mix(in srgb,var(--ok) 45%,transparent);background:color-mix(in srgb,var(--ok) 13%,transparent)}
.b.warn{color:var(--warn);border-color:color-mix(in srgb,var(--warn) 45%,transparent);background:color-mix(in srgb,var(--warn) 13%,transparent)}
.b.bad{color:var(--bad);border-color:color-mix(in srgb,var(--bad) 45%,transparent);background:color-mix(in srgb,var(--bad) 13%,transparent)}
.b.acc{color:var(--ac);border-color:color-mix(in srgb,var(--ac) 45%,transparent);background:var(--acs)}
.b.pur{color:var(--pur);border-color:color-mix(in srgb,var(--pur) 45%,transparent);background:color-mix(in srgb,var(--pur) 13%,transparent)}
.tw{overflow-x:auto;border:1px solid var(--bd);border-radius:var(--r);background:var(--panel2)}
table{border-collapse:collapse;width:100%;font-size:.85rem;min-width:520px}
th,td{padding:8px 11px;text-align:left;border-bottom:1px solid var(--bd);vertical-align:top}
th{background:var(--panel3);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--mu);font-weight:800}
tr:last-child td{border-bottom:none}tbody tr:hover{background:var(--panel3)}
.note{border-left:3px solid var(--info);background:var(--panel2);padding:10px 13px;border-radius:0 var(--r) var(--r) 0;margin:11px 0;font-size:.86rem}
.note.warn{border-left-color:var(--warn)}.note.bad{border-left-color:var(--bad)}.note.ok{border-left-color:var(--ok)}
.note .nt{font-weight:800;display:block;margin-bottom:2px;font-size:.78rem;text-transform:uppercase;letter-spacing:.05em}
details{border:1px solid var(--bd);border-radius:var(--r);background:var(--panel2);margin:7px 0;overflow:hidden}
summary{cursor:pointer;padding:10px 13px;font-weight:650;font-size:.88rem;list-style:none;display:flex;gap:8px;align-items:flex-start}
summary::-webkit-details-marker{display:none}summary:before{content:'\25B8';color:var(--mu);flex:0 0 auto;transition:.15s}
details[open] summary:before{transform:rotate(90deg)}details .bd{padding:0 13px 12px 30px;font-size:.85rem}
.quote{font-family:var(--mono);font-size:.76rem;background:var(--cb);border:1px solid var(--bd);border-left:3px solid var(--ac);border-radius:0 var(--r) var(--r) 0;padding:8px 11px;margin:6px 0;color:var(--mu);word-break:break-word}
.mu{color:var(--mu)}.sm{font-size:.79rem}.mono{font-family:var(--mono)}
.row{display:flex;gap:9px;flex-wrap:wrap;align-items:center}.spread{display:flex;justify-content:space-between;gap:11px;flex-wrap:wrap;align-items:center}
ul.tight{margin:.4em 0;padding-left:20px}ul.tight li{margin-bottom:4px}
footer{border-top:1px solid var(--bd);padding:20px 0 40px;color:var(--mu);font-size:.81rem}
@media(max-width:760px){nav{order:3;flex-basis:100%}section{padding:14px}table{min-width:420px}details .bd{padding-left:14px}}
@media print{header,nav,.tools,button,.btn{display:none!important}body{background:#fff;color:#000}section{break-inside:avoid;box-shadow:none;border-color:#ccc}details .bd{display:block!important}:root{--panel:#fff;--panel2:#fff;--panel3:#f4f4f4;--tx:#000;--mu:#333;--bd:#ccc;--bd2:#bbb}}
"""
