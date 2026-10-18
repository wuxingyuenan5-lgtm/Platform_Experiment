import json
import sqlite3
import pytest
from app.research_gold import analyst_page, read_gold
from app.research_provider_errors import ResearchProviderError


def make_store(tmp_path, monkeypatch):
    monkeypatch.setenv('HEDGE_BOARD_DATA_ROOT', str(tmp_path))
    folder = tmp_path / 'research'; folder.mkdir()
    db = sqlite3.connect(folder / 'analyst_views.sqlite3')
    db.executescript('CREATE TABLE articles(id TEXT, analyst_id TEXT,published_at TEXT, search_text TEXT, stances TEXT,payload_json TEXT); CREATE TABLE analysts(payload_json TEXT); CREATE TABLE sources(analyst_id TEXT,last_success TEXT,last_attempt TEXT,error TEXT);')
    for aid, author, title, stance in [('1','a','Gold outlook','bull'),('2','b','Silver 10%','unspecified'),('3','a','Gold risk','bear')]:
        db.execute('INSERT INTO articles VALUES(?,?,?,?,?,?)',(aid,author,'2020-01-01',title.lower(),stance,json.dumps(dict(id=aid,analystId=author,title=title))))
    db.execute('INSERT INTO sources VALUES(?,?,?,NULL)',('a','2020-01-01T00:00:00+00:00','2020-01-01T00:00:00+00:00'))
    db.commit(); db.close()


def test_filter_pagination_and_missing_stance(tmp_path, monkeypatch):
    make_store(tmp_path, monkeypatch)
    assert analyst_page(author='a', query='gold outlook')['total'] == 1
    assert analyst_page(stance='unspecified')['articles'][0]['id'] == '2'
    assert analyst_page(stance='neutral')['total'] == 0
    assert analyst_page(page=2, page_size=2)['articles'][0]['id'] == '3'
    assert analyst_page()['status'] == 'stale'
    assert analyst_page(query='%')['total'] == 1
    assert analyst_page(query='_')['total'] == 0
    assert analyst_page(author="a' OR 1=1 --")['total'] == 0
    assert analyst_page(page=-1,page_size=999)['pageSize'] == 100
    with pytest.raises(ResearchProviderError): read_gold('../invalid')


def test_initial_unavailable_analysts_are_not_empty_search_results(tmp_path, monkeypatch):
    monkeypatch.setenv('HEDGE_BOARD_DATA_ROOT', str(tmp_path))
    folder = tmp_path/'public/v1/commodity'; folder.mkdir(parents=True)
    (folder/'analyst-views.json').write_text(json.dumps(dict(schemaVersion='1.0', status='ready',articles=[{'id':'legacy'}])))
    with pytest.raises(ResearchProviderError, match='analyst_views_unavailable'):
        analyst_page()
