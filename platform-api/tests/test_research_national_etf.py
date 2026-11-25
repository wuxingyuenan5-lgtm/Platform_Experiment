import json
from pathlib import Path
import pytest
from app.research_national_etf import validate

def valid():
 return {"sample":False,"dates":["2026-11-03"],"etfs":[{"code":"510300"}],"series":{"510300":{"shares":[1],"close":[2],"flow":[None]}}}
def test_valid_preserves_null():
 assert validate(valid())["series"]["510300"]["flow"]==[None]
@pytest.mark.parametrize("kind",["sample","length","date","nan"])
def test_reject_invalid(kind):
 d=valid()
 if kind=="sample":d["sample"]=True
 if kind=="length":d["series"]["510300"]["flow"]=[]
 if kind=="date":d["dates"]=["bad"]
 if kind=="nan":d["series"]["510300"]["flow"]=[float('nan')]
 with pytest.raises(ValueError):validate(d)
