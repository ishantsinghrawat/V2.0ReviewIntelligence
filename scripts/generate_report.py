from __future__ import annotations
from html import escape
from common import load_json
from pathlib import Path

def main():
    s=load_json("analytics_summary.json",{}); b=load_json("agent_brief.json",{}); d=s.get("generated_for","unknown")
    alerts=[a for a in s.get("anomalies",[]) if a.get("triggered")]
    md=[f"# Customer Voice Daily Brief — {d}","",f"**Reviews (30d):** {s.get('kpis',{}).get('reviews',0)}  ",f"**Negative:** {s.get('kpis',{}).get('negative_pct',0)}%  ",f"**Average rating:** {s.get('kpis',{}).get('avg_rating',0)}  ",f"**Triggered alerts:** {len(alerts)}","", "## Executive brief", b.get("executive_summary") or b.get("summary") or "No brief available.","","## Triggered anomalies"]
    if alerts:
        for a in alerts: md.append(f"- **{a['category']}** — {a['current']} negatives vs {a['baseline_daily_avg']} baseline; severity {a['severity']}/100")
    else: md.append("- No anomaly crossed the configured threshold.")
    md += ["","## Recommended actions"]+[f"- {x}" for x in b.get("recommended_actions",[])]
    Path("delta_report.md").write_text("\n".join(md),encoding="utf-8")
    Path("reports").mkdir(exist_ok=True)
    Path(f"reports/{d}.md").write_text("\n".join(md),encoding="utf-8")
    body="<br>".join(escape(x) for x in md)
    Path(f"reports/{d}.html").write_text(f"<!doctype html><meta charset='utf-8'><title>Customer Voice {d}</title><body style='font-family:system-ui;max-width:900px;margin:40px auto;line-height:1.5'>{body}</body>",encoding="utf-8")

if __name__=="__main__": main()
