from __future__ import annotations
import json, os
from collections import Counter
from common import load_json, save_json


def deterministic(summary):
    alerts=[a for a in summary.get("anomalies",[]) if a.get("triggered")]
    releases=[r for r in summary.get("release_health",[]) if r.get("status")=="Degrading"][:3]
    emerging=summary.get("emerging_issues",[])[:3]
    status="Deteriorating" if alerts else "Stable / no threshold alert"
    bullets=[f"{a['category']} recorded {a['current']} negative reviews versus a {a['baseline_daily_avg']} daily baseline (severity {a['severity']}/100)." for a in alerts[:3]]
    if not bullets: bullets=["No category crossed the configured anomaly threshold today."]
    return {"mode":"deterministic","overall_health":status,"summary":" ".join(bullets),"key_findings":bullets,"degrading_releases":releases,"emerging_issues":emerging,"recommended_actions":["Investigate any triggered category against the affected app version and platform.","Review the linked customer comments before escalating a defect.","Validate suspected regressions with telemetry and targeted QA regression tests."]}


def build_tools(summary, rows):
    def get_version_metrics(source=None, version=None):
        data=summary.get("release_health",[])
        return [x for x in data if (not source or x.get("source")==source) and (not version or str(x.get("version"))==str(version))][:20]
    def get_negative_reviews(category=None, source=None, version=None, limit=12):
        out=[]
        for r in rows:
            if r.get("sentiment_std")!="Negative" and int(r.get("rating") or 0)>2: continue
            if category and not (r.get("primary_category")==category or any(i.get("label")==category for i in (r.get("issues") or []) if isinstance(i,dict))): continue
            if source and r.get("source")!=source: continue
            if version and str(r.get("app_version"))!=str(version): continue
            out.append({k:r.get(k) for k in ["review_id","review_date","source","app_version","rating","review","primary_category","issues"]})
        return out[:max(1,min(int(limit),20))]
    def get_category_trend(category=None):
        return [x for x in summary.get("anomalies",[]) if not category or x.get("category")==category]
    def get_emerging_issues(limit=8):
        return summary.get("emerging_issues",[])[:max(1,min(int(limit),10))]
    funcs={"get_version_metrics":get_version_metrics,"get_negative_reviews":get_negative_reviews,"get_category_trend":get_category_trend,"get_emerging_issues":get_emerging_issues}
    schemas=[
      {"type":"function","name":"get_version_metrics","description":"Get calculated release health metrics, optionally filtered by store/source and version.","parameters":{"type":"object","properties":{"source":{"type":["string","null"]},"version":{"type":["string","null"]}},"additionalProperties":False},"strict":True},
      {"type":"function","name":"get_negative_reviews","description":"Retrieve negative customer-review evidence filtered by issue category, store/source or app version.","parameters":{"type":"object","properties":{"category":{"type":["string","null"]},"source":{"type":["string","null"]},"version":{"type":["string","null"]},"limit":{"type":"integer","minimum":1,"maximum":20}},"required":["category","source","version","limit"],"additionalProperties":False},"strict":True},
      {"type":"function","name":"get_category_trend","description":"Get deterministic current-vs-7-day-baseline anomaly metrics for issue categories.","parameters":{"type":"object","properties":{"category":{"type":["string","null"]}},"required":["category"],"additionalProperties":False},"strict":True},
      {"type":"function","name":"get_emerging_issues","description":"Get recurring phrases mined from recent negative reviews.","parameters":{"type":"object","properties":{"limit":{"type":"integer","minimum":1,"maximum":10}},"required":["limit"],"additionalProperties":False},"strict":True}
    ]
    return funcs,schemas


def ai_brief(summary, rows):
    from openai import OpenAI
    client=OpenAI(); funcs,tools=build_tools(summary,rows)
    instructions="""You are a QA/product Review Investigation Agent. Use the supplied tools to investigate the latest deterministic analytics before concluding. Never invent root causes. Clearly separate observed evidence from hypotheses. Focus on customer-impacting regressions, affected versions/platforms, emerging issues, and practical QA/product follow-up. Your FINAL response must be valid JSON only with keys: overall_health, executive_summary, key_findings, hypotheses, recommended_actions, evidence_review_ids."""
    input_items=[{"role":"user","content":f"Investigate the Customer Voice run for {summary.get('generated_for')}. There are {summary.get('kpis',{}).get('alerts',0)} triggered deterministic alerts. Use tools as needed, then return the requested JSON."}]
    response=client.responses.create(model=os.getenv("OPENAI_MODEL","gpt-5"),instructions=instructions,input=input_items,tools=tools,tool_choice="auto")
    for _ in range(4):
        calls=[item for item in response.output if getattr(item,"type",None)=="function_call"]
        if not calls: break
        input_items += response.output
        for call in calls:
            try:
                args=json.loads(call.arguments or "{}")
                result=funcs[call.name](**args)
            except Exception as e:
                result={"error":str(e)[:200]}
            input_items.append({"type":"function_call_output","call_id":call.call_id,"output":json.dumps(result,ensure_ascii=False)})
        response=client.responses.create(model=os.getenv("OPENAI_MODEL","gpt-5"),instructions=instructions,input=input_items,tools=tools,tool_choice="auto")
    text=response.output_text.strip()
    if text.startswith('```'):
        text=text.strip('`').replace('json\n','',1).strip()
    try: out=json.loads(text)
    except Exception: out={"overall_health":"See executive summary","executive_summary":text,"key_findings":[],"hypotheses":[],"recommended_actions":[],"evidence_review_ids":[]}
    out["mode"]="openai-tool-agent"; return out


def main():
    summary=load_json("analytics_summary.json",{}); rows=load_json("data.json")
    out=deterministic(summary)
    if os.getenv("OPENAI_API_KEY"):
        try: out=ai_brief(summary,rows)
        except Exception as e: out["agent_error"]=str(e)[:300]
    save_json("agent_brief.json",out); print(f"[agent] mode={out.get('mode')}")

if __name__=="__main__": main()
