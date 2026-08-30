from __future__ import annotations
import time, requests
import pandas as pd
import numpy as np
from google_play_scraper import reviews_all, Sort
from common import load_settings, stable_review_id


def fetch_google_play(cfg):
    rows = reviews_all(cfg["package"], sleep_milliseconds=0, lang=cfg["lang"], country=cfg["country"], sort=Sort.NEWEST)
    if not rows: return []
    g = pd.DataFrame(np.array(rows), columns=["row"])
    df = g.join(pd.DataFrame(g.pop("row").tolist()))
    df.rename(columns={"score":"rating","userName":"user_name","reviewId":"review_id","content":"review","at":"review_date","replyContent":"developer_response","repliedAt":"developer_response_date","thumbsUpCount":"thumbs_up","appVersion":"app_version"}, inplace=True)
    out=[]
    for _,x in df.iterrows():
        out.append({"source":"Google Play","review_id":x.get("review_id"),"review":x.get("review"),"rating":int(x.get("rating") or 0),"review_date":pd.to_datetime(x.get("review_date"),errors="coerce").strftime("%Y-%m-%d"),"user_name":x.get("user_name"),"review_title":None,"app_version":x.get("app_version"),"developer_response":x.get("developer_response"),"thumbs_up":int(x.get("thumbs_up") or 0),"country_code":cfg["country"],"language_code":cfg["lang"]})
    return out


def fetch_app_store(cfg):
    if not cfg.get("enabled", True): return []
    rows=[]
    for page in range(1, int(cfg.get("max_pages",10))+1):
        url=f'https://itunes.apple.com/rss/customerreviews/page={page}/id={cfg["app_id"]}/sortby=mostrecent/json?l={cfg["lang"]}&cc={cfg["country"]}'
        r=requests.get(url,timeout=30)
        if r.status_code != 200: break
        entries=r.json().get("feed",{}).get("entry",[])
        if not entries or len(entries)<=1: break
        for e in entries[1:]:
            updated=(e.get("updated") or {}).get("label")
            item={"source":"App Store","review":(e.get("content") or {}).get("label"),"rating":int((e.get("im:rating") or {}).get("label","0") or 0),"review_date":pd.to_datetime(updated,errors="coerce").strftime("%Y-%m-%d") if updated else None,"user_name":((e.get("author") or {}).get("name") or {}).get("label"),"review_title":(e.get("title") or {}).get("label"),"app_version":(e.get("im:version") or {}).get("label"),"developer_response":None,"thumbs_up":0,"country_code":cfg["country"],"language_code":cfg["lang"]}
            item["review_id"]=stable_review_id(item); rows.append(item)
        time.sleep(.15)
    return rows


def fetch_all():
    s=load_settings(); rows=fetch_google_play(s["google_play"])+fetch_app_store(s["app_store"])
    cleaned=[]
    for r in rows:
        if not str(r.get("review") or "").strip() or not r.get("review_date"): continue
        r["review_id"]=stable_review_id(r); cleaned.append(r)
    return cleaned

if __name__ == "__main__":
    import json
    print(json.dumps(fetch_all(),ensure_ascii=False))
