import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from common import stable_review_id,load_settings
from enrich_reviews import confidence_band
from analytics import severity

def test_stable_id_repeatable():
    r={'source':'App Store','review_date':'2026-01-01','user_name':'a','review':'hello'}
    assert stable_review_id(r)==stable_review_id(r)

def test_taxonomy_unique_and_spelling():
    c=load_settings()['categories']; assert len(c)==len(set(c)); assert 'Performance/Speed' in c; assert all('Perfromance' not in x for x in c)

def test_confidence_bands():
    n=load_settings()['nlp']; assert confidence_band(.9,n)=='High'; assert confidence_band(.6,n)=='Medium'; assert confidence_band(.2,n)=='Low'

def test_severity_rises_with_anomaly():
    assert severity(10,1,10,1.0)>severity(2,2,2,3.0)
