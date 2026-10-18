"""Read-only gold research artifacts and bounded analyst pagination."""
from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
import json

from app.research_local_data import hedge_board_data_root
from app.research_provider_errors import ResearchProviderError


@lru_cache(maxsize=6)
def _load(path: str, modified: int):
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("schemaVersion") != "1.0":
        raise ResearchProviderError("gold_research_schema_mismatch")
    return payload


def read_gold(name: str):
    if name not in ("gold-positioning", "gold-report", "analyst-views"):
        raise ResearchProviderError("unknown_gold_artifact")
    try:
        path = hedge_board_data_root() / "public/v1/commodity" / f"{name}.json"
        payload = _load(str(path), path.stat().st_mtime_ns)
        result = dict(payload)
        retrieved = payload.get("retrievedAt")
        if retrieved and (datetime.now(UTC)-datetime.fromisoformat(retrieved.replace("Z", "+00:00"))).total_seconds() > 36*3600:
            result["status"] = "stale"
        return result
    except (OSError, ValueError, TypeError) as exc:
        raise ResearchProviderError("gold_research_unavailable") from exc


def analyst_page(*, author="", stance="", query="", page=1, page_size=12):
    import sqlite3
    path = hedge_board_data_root() / 'research/analyst_views.sqlite3'
    if not path.exists():
        raise ResearchProviderError('analyst_views_unavailable')
    clauses, args = [], []
    if author:
        clauses.append('analyst_id=?'); args.append(author)
    if stance:
        clauses.append("(','||stances||',') LIKE ?"); args.append('%,'+stance+',%')
    for term in query.casefold().split():
        clauses.append("search_text LIKE ? ESCAPE '\\'")
        args.append('%'+term.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%')
    where = ' WHERE '+' AND '.join(clauses) if clauses else ''
    page=max(1,page); page_size=max(1,min(page_size,100))
    try:
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=3) as db:
            db.row_factory=sqlite3.Row
            db.execute('BEGIN')
            if not db.execute('SELECT 1 FROM articles LIMIT 1').fetchone():
                raise ResearchProviderError('analyst_views_unavailable')
            total=db.execute('SELECT count(*) FROM articles'+where,args).fetchone()[0]
            rows=db.execute('SELECT payload_json FROM articles'+where+' ORDER BY published_at DESC,id LIMIT ? OFFSET ?',
                            [*args,page_size,(page-1)*page_size]).fetchall()
            analysts=[json.loads(r[0]) for r in db.execute('SELECT payload_json FROM analysts ORDER BY rowid')]
            sources=[dict(r) for r in db.execute('SELECT analyst_id,last_success,last_attempt,error FROM sources')]
            successful=[r['last_success'] for r in sources if r['last_success']]
            retrieved=max(successful,default=None)
            stale=not retrieved or (datetime.now(UTC)-datetime.fromisoformat(retrieved)).total_seconds()>36*3600
            return dict(schemaVersion='1.0',source='平台独立采集整理',retrievedAt=retrieved,
                status='stale' if stale else 'partial' if any(r['error'] for r in sources) else 'ready',
                methodology='independent_public_author_v1',analysts=analysts,
                articles=[json.loads(r[0]) for r in rows],total=total,page=page,pageSize=page_size)
    except (sqlite3.Error,ValueError,TypeError) as exc:
        raise ResearchProviderError('analyst_views_unavailable') from exc
