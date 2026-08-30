from __future__ import annotations
from datetime import timedelta
from common import load_settings, load_json, save_json, stable_review_id, utc_today
from ingest_reviews import fetch_all
from enrich_reviews import enrich

CANON=["review_id","source","review_date","app_version","rating","review","user_name","review_title","developer_response","thumbs_up","country_code","language_code","sentiment_std","sentiment_score","primary_category","category","category_score","issues","classification_confidence"]

def migrate(r):
    r=dict(r); r["review_id"]=stable_review_id(r)
    if not r.get("primary_category"): r["primary_category"]=r.get("category")
    if not r.get("issues") and r.get("category"): r["issues"]=[{"label":r["category"],"score":r.get("category_score")}]
    for k in CANON: r.setdefault(k,None if k!="issues" else [])
    return {k:r.get(k) for k in CANON}

def main():
    s=load_settings(); master=[migrate(r) for r in load_json("data_master.json")]
    if not master:
        master=[migrate(r) for r in load_json("data.json")]
    by_id={r["review_id"]:r for r in master}
    fetched=[migrate(r) for r in fetch_all()]
    fresh=[r for r in fetched if r["review_id"] not in by_id]
    print(f"[pipeline] fetched={len(fetched)} existing={len(by_id)} new={len(fresh)}")
    fresh=enrich(fresh)
    for r in fresh: by_id[r["review_id"]]=migrate(r)
    cutoff=utc_today()-timedelta(days=int(s["history_days"]))
    master=[r for r in by_id.values() if r.get("review_date") and __import__('datetime').date.fromisoformat(r["review_date"])>=cutoff]
    master.sort(key=lambda r:(r.get("review_date") or "",r.get("review_id") or ""),reverse=True)
    save_json("data_master.json",master)
    dcut=utc_today()-timedelta(days=int(s["dashboard_days"]))
    data=[r for r in master if __import__('datetime').date.fromisoformat(r["review_date"])>=dcut]
    save_json("data.json",data)
    latest=max((r["review_date"] for r in master),default=None)
    save_json("data_1d.json",[r for r in master if r.get("review_date")==latest])
    print(f"[pipeline] master={len(master)} dashboard={len(data)} latest_day={latest}")

if __name__=="__main__": main()
