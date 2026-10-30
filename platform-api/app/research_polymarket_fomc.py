"""Persistent FOMC event/outcome history; the browser only reads this artifact."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.research_local_data import hedge_board_data_root, write_local_json

ARTIFACT = "public/v1/macro/fomc-meetings.json"
GAMMA = "https://gamma-api.polymarket.com/events"
HISTORY = "https://clob.polymarket.com/prices-history"


def _array(value):
    return json.loads(value) if isinstance(value, str) else value


def _request(client, url, params):
    response = client.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    # Freeze source responses, including discovery and historical chunks.
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex
    write_local_json(
        f"raw/research/polymarket-fomc/{stamp}.json",
        {"url": str(response.url), "retrievedAt": datetime.now(UTC).isoformat(), "data": payload},
    )
    return payload


def meeting_from_event(event, now):
    expiry = datetime.fromisoformat(event["endDate"].replace("Z", "+00:00"))
    # Gamma closes overnight UTC; the FOMC decision belongs to the NY date.
    day = expiry.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    outcomes = []
    for market in event.get("markets", []):
        names = _array(market.get("outcomes", []))
        prices = _array(market.get("outcomePrices", []))
        tokens = _array(market.get("clobTokenIds", []))
        if "Yes" not in names or len(names) != len(prices) or len(tokens) != len(names):
            raise ValueError("invalid FOMC binary outcome")
        index = names.index("Yes")
        probability = float(prices[index]) * 100
        if not 0 <= probability <= 100:
            raise ValueError("invalid FOMC probability")
        label = market.get("groupItemTitle") or market["question"]
        outcomes.append(
            {
                "id": str(market["id"]),
                "tokenId": tokens[index],
                "label": label,
                "probability": probability,
                "history": [],
            }
        )
    if not outcomes:
        raise ValueError("FOMC meeting has no outcomes")
    return {
        "id": str(event["id"]),
        "slug": event["slug"],
        "label": f"{day} FOMC",
        "meetingDate": day,
        "expiryAt": expiry.isoformat(),
        "closed": bool(event.get("closed")),
        "sourceUrl": "https://polymarket.com/event/" + event["slug"],
        "updatedAt": now.isoformat(),
        "status": "ready",
        "outcomes": outcomes,
    }


def merge_history(previous, incoming):
    points = {point["observedAt"]: point for point in [*previous, *incoming]}
    return [points[key] for key in sorted(points)]


def refresh_fomc(*, force=False):
    now = datetime.now(UTC)
    target = hedge_board_data_root() / ARTIFACT
    old = json.loads(target.read_text(encoding="utf8")) if target.exists() else {}
    if (
        not force
        and old.get("updatedAt")
        and now - datetime.fromisoformat(old["updatedAt"]) < timedelta(minutes=5)
    ):
        return "up_to_date"
    retained = {m["id"]: m for m in old.get("meetings", [])}
    try:
        with requests.Session() as client:
            retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
            client.mount("https://", HTTPAdapter(max_retries=retry))
            events = _request(
                client,
                GAMMA,
                {"series_id": "35", "limit": 100, "active": "true", "closed": "false"},
            )
            if not isinstance(events, list) or not events:
                raise ValueError("FOMC series discovery returned no meetings")
            # Update a just-expired meeting until its final resolution is archived.
            found = {str(e["id"]) for e in events}
            for prior in retained.values():
                if not prior.get("closed") and prior["id"] not in found:
                    events.extend(_request(client, GAMMA, {"id": prior["id"]}))

            def collect(event):
                meeting = meeting_from_event(event, now)
                prior = retained.get(meeting["id"], {})
                prior_outcomes = {v["id"]: v for v in prior.get("outcomes", [])}
                partial = False
                for outcome in meeting["outcomes"]:
                    outcome_failed = False
                    previous = prior_outcomes.get(outcome["id"], {}).get("history", [])
                    start = datetime.fromisoformat(event["startDate"].replace("Z", "+00:00"))
                    # Continue at the successfully collected watermark; failed chunks are retried.
                    watermark = prior_outcomes.get(outcome["id"], {}).get("historyThrough")
                    if watermark:
                        start = datetime.fromisoformat(watermark) - timedelta(hours=1)
                    incoming = []
                    through = start
                    try:
                        while start < now:
                            end = min(start + timedelta(days=14), now)
                            result = _request(
                                client,
                                HISTORY,
                                {
                                    "market": outcome["tokenId"],
                                    "startTs": int(start.timestamp()),
                                    "endTs": int(end.timestamp()),
                                    "fidelity": 60,
                                },
                            )
                            if not isinstance(result.get("history"), list):
                                raise ValueError("missing CLOB history")
                            for row in result["history"]:
                                value = float(row["p"]) * 100
                                observed = datetime.fromtimestamp(int(row["t"]), UTC)
                                if not 0 <= value <= 100:
                                    raise ValueError("invalid CLOB point")
                                # CLOB may return an expanded cached window. Retain only
                                # actual observations within this event's lifetime.
                                if observed > now or observed < datetime.fromisoformat(
                                    event["startDate"].replace("Z", "+00:00")
                                ):
                                    continue
                                incoming.append(
                                    {"observedAt": observed.isoformat(), "probability": value}
                                )
                            through = end
                            start = end
                    except Exception:
                        partial = True
                        outcome_failed = True
                        logging.getLogger(__name__).exception(
                            "FOMC history refresh failed for %s", outcome["id"]
                        )
                    outcome["history"] = merge_history(previous, incoming)
                    # Current quotes remain separate when historical backfill fails.
                    if not outcome_failed:
                        outcome["history"] = merge_history(
                            outcome["history"],
                            [
                                {
                                    "observedAt": now.isoformat(),
                                    "probability": outcome["probability"],
                                }
                            ],
                        )
                    outcome["historyThrough"] = through.isoformat()
                meeting["status"] = "stale" if partial else "ready"
                return meeting

            failures = []

            def collect_safely(event):
                try:
                    return collect(event)
                except Exception:
                    failures.append(str(event.get("id")))
                    logging.getLogger(__name__).exception(
                        "FOMC meeting refresh failed: %s", event.get("id")
                    )
                    prior = retained.get(str(event.get("id")))
                    return {**prior, "status": "stale"} if prior else None

            with ThreadPoolExecutor(max_workers=4) as pool:
                for meeting in pool.map(collect_safely, events):
                    if meeting:
                        retained[meeting["id"]] = meeting
        status = (
            "stale"
            if failures or any(m["status"] != "ready" for m in retained.values() if not m["closed"])
            else "ready"
        )
    except Exception:
        logging.getLogger(__name__).exception("FOMC discovery refresh failed")
        status = "stale" if retained else "error"
    write_local_json(
        ARTIFACT,
        {
            "schemaVersion": "1.0",
            "status": status,
            "updatedAt": now.isoformat(),
            "meetings": sorted(retained.values(), key=lambda m: m["meetingDate"]),
        },
    )
    return status
