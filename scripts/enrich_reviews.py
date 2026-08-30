from __future__ import annotations
import os
from common import load_settings

SENTI_MAP={"negative":"Negative","NEGATIVE":"Negative","LABEL_0":"Negative","neutral":"Neutral","NEUTRAL":"Neutral","LABEL_1":"Neutral","positive":"Positive","POSITIVE":"Positive","LABEL_2":"Positive"}

def confidence_band(score, cfg):
    if score is None: return "Unknown"
    if score >= cfg["high_confidence"]: return "High"
    if score >= cfg["medium_confidence"]: return "Medium"
    return "Low"

def enrich(rows):
    if not rows: return rows
    from transformers import pipeline
    os.environ.setdefault("TOKENIZERS_PARALLELISM","false")
    s=load_settings(); n=s["nlp"]; labels=s["categories"]
    senti=pipeline("sentiment-analysis",model=n["sentiment_model"])
    zshot=pipeline("zero-shot-classification",model=n["zero_shot_model"])
    for i,r in enumerate(rows,1):
        text=str(r.get("review") or "")[:512]
        sv=senti(text)[0]; ss=float(sv.get("score",0))
        z=zshot(text,candidate_labels=labels,multi_label=True)
        issues=[{"label":lab,"score":round(float(sc),4)} for lab,sc in zip(z["labels"],z["scores"]) if float(sc)>=n["multi_label_threshold"]]
        if not issues: issues=[{"label":z["labels"][0],"score":round(float(z["scores"][0]),4)}]
        r.update({"sentiment_std":SENTI_MAP.get(sv["label"],sv["label"]),"sentiment_score":round(ss,4),"primary_category":issues[0]["label"],"category":issues[0]["label"],"category_score":issues[0]["score"],"issues":issues,"classification_confidence":confidence_band(issues[0]["score"],n)})
        if i%25==0: print(f"[nlp] enriched {i}/{len(rows)}",flush=True)
    return rows
