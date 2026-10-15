import json
import pytest
from app.research_gold import analyst_page, read_gold
from app.research_provider_errors import ResearchProviderError


def test_filter_pagination_and_missing_stance(tmp_path, monkeypatch):
    monkeypatch.setenv('HEDGE_BOARD_DATA_ROOT', str(tmp_path))
    folder = tmp_path / 'public/v1/commodity'; folder.mkdir(parents=True)
    document = dict(schemaVersion='1.0', status='ready', retrievedAt='2020-01-01T00:00:00Z', analysts=[], articles=[
        dict(id=1, analystId='a', title='Gold outlook', views=[dict(stance='bull', assetName='Gold')]),
        dict(id=2, analystId='b', title='Silver', views=[]),
        dict(id=3, analystId='a', title='Gold risk', views=[dict(stance='bear', assetName='Gold')]),
    ])
    (folder/'analyst-views.json').write_text(json.dumps(document), encoding='utf-8')
    assert analyst_page(author='a', query='gold outlook')['total'] == 1
    assert analyst_page(stance='unspecified')['articles'][0]['id'] == 2
    assert analyst_page(stance='neutral')['total'] == 0
    assert analyst_page(page=2, page_size=2)['articles'][0]['id'] == 3
    assert read_gold('analyst-views')['status'] == 'stale'
    with pytest.raises(ResearchProviderError): read_gold('../invalid')


def test_initial_unavailable_analysts_are_not_empty_search_results(tmp_path, monkeypatch):
    monkeypatch.setenv('HEDGE_BOARD_DATA_ROOT', str(tmp_path))
    folder = tmp_path/'public/v1/commodity'; folder.mkdir(parents=True)
    (folder/'analyst-views.json').write_text(json.dumps(dict(schemaVersion='1.0', status='unavailable')))
    with pytest.raises(ResearchProviderError, match='analyst_views_unavailable'):
        analyst_page()
