"""Refresh the small, curated macro-event probability feed.

The page never calls a prediction-market API.  This worker fetches a bounded set of
public Polymarket markets, applies conservative quality gates, merges a short local
history, and publishes one atomic JSON artifact consumed by ``MacroResearchProvider``.
Markets that cannot be parsed as a binary Yes/No contract or have insufficient
liquidity are intentionally omitted instead of being shown as precise probabilities.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.research_local_data import hedge_board_data_root, write_local_json
from app.research_provider_errors import ResearchProviderError

_URL = "https://gamma-api.polymarket.com/markets"
_EVENTS_URL = "https://gamma-api.polymarket.com/events"
_CLOB_HISTORY_URL = "https://clob.polymarket.com/prices-history"
_SOURCE = "Polymarket public markets (curated, read-only)"
_HISTORY_MAX_POINTS = 30 * 24 * 12  # 30 days at the five-minute refresh cadence
# The volume-ranked /markets feed is not guaranteed to contain a live Fed
# contract.  Keep this list deliberately short and fetch it through the same
# public Gamma API, so monetary-policy expectations do not disappear merely
# because election markets temporarily rank higher.
_CURATED_EVENT_SLUGS = (
    "another-fed-rate-hike-in-2026",
    "fed-decision-in-september-762",
    "fed-decisions-jun-sep",
)
_CATEGORIES: dict[str, tuple[str, ...]] = {
    "monetary_policy": ("fed", "fomc", "interest rate", "rate cut", "rate hike", "powell"),
    "macro": ("inflation", "cpi", "pce", "recession", "unemployment", "gdp", "payroll"),
    "election": ("election", "president", "senate", "congress", "governor", "referendum"),
    "geopolitics": ("war", "ceasefire", "iran", "ukraine", "taiwan", "israel", "russia"),
}
_EXCLUDED = ("sports", "nba", "nfl", "mlb", "bitcoin", "crypto", "ethereum", "movie", "oscar")

_PARTY_NAMES_ZH = {
    "New People (NL)": "新人民党（NL）",
    "Communist Party of the Russian Federation (KPRF)": "俄罗斯共产党（KPRF）",
    "the Communist Party of the Russian Federation (KPRF)": "俄罗斯共产党（KPRF）",
    "Yabloko": "亚博卢科党",
    "Rodina": "祖国党",
    "United Russia (ER)": "统一俄罗斯党（ER）",
    "Liberal Democratic Party of Russia (LDPR)": "俄罗斯自由民主党（LDPR）",
    "the Liberal Democratic Party of Russia (LDPR)": "俄罗斯自由民主党（LDPR）",
    "A Just Russia – For Truth (SRZP)": "公正俄罗斯党（SRZP）",
}


def _localize_title(title: str, category: str) -> str:
    """Return a stable Chinese display title without changing source semantics."""
    known = {
        "Another Fed rate hike in 2026?": "2026年美联储是否再次加息？",
        "Will the Fed cut rates by December 2026?": "美联储将在2026年12月前降息吗？",
        "Fed Decision in September?": "美联储9月利率决议结果？",
        "Fed decisions (Jun-Sep)": "美联储6月至9月利率决议路径？",
        "Trump out as President by September 30?": "特朗普将在9月30日前卸任总统吗？",
        "Israel closes its airspace by September 30?": "以色列将在9月30日前关闭领空吗？",
        "US x Iran ceasefire continues through September 20?": "美国与伊朗停火持续至9月20日吗？",
        "US x Iran ceasefire continues through September 25?": "美国与伊朗停火持续至9月25日吗？",
        "US x Iran ceasefire continues through September 30?": "美国与伊朗停火持续至9月30日吗？",
        "US x Iran ceasefire continues through October 31?": "美国与伊朗停火持续至10月31日吗？",
        "Israel x Iran ceasefire continues through September 30?": (
            "以色列与伊朗停火持续至9月30日吗？"
        ),
        "Israel x Iran ceasefire continues through November 30?": (
            "以色列与伊朗停火持续至11月30日吗？"
        ),
        "Will the U.S. invade Iran before 2027?": "美国将在2027年前入侵伊朗吗？",
        "NATO x Russia military clash by October 31, 2026?": (
            "北约与俄罗斯将在2026年10月31日前发生军事冲突吗？"
        ),
        "Will China invade Taiwan by end of 2026?": "中国将在2026年底前入侵台湾吗？",
    }
    if title in known:
        return known[title]

    match = re.fullmatch(
        r"Will (.+) (gain|win) the most seats in the next Russian parliamentary election\?", title
    )
    if match:
        party = _PARTY_NAMES_ZH.get(match.group(1), match.group(1))
        return f"{party}将在下一次俄罗斯议会选举中赢得最多席位吗？"
    match = re.fullmatch(r"Will (.+) win the 2026 Brazilian presidential election\?", title)
    if match:
        candidate = {"Renan Santos": "雷南·桑托斯"}.get(match.group(1), match.group(1))
        return f"{candidate}将赢得2026年巴西总统大选吗？"
    match = re.fullmatch(r"Will (.+) win the 2027 French presidential election\?", title)
    if match:
        candidate = {"François Baroin": "弗朗索瓦·巴鲁安"}.get(match.group(1), match.group(1))
        return f"{candidate}将赢得2027年法国总统大选吗？"

    # Keep unknown additions readable and Chinese rather than leaking an
    # English provider title into the product.  The original remains in the
    # separate originalLabel field for audit and source comparison.
    category_label = {
        "monetary_policy": "货币政策",
        "macro": "宏观经济",
        "geopolitics": "地缘政治",
        "election": "选举与政策",
    }[category]
    return f"{category_label}事件（市场原题见来源）"


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and 0 <= result <= 1 else None


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _category(title: str) -> str | None:
    lowered = f" {title.lower()} "
    if any(term in lowered for term in _EXCLUDED):
        return None
    def contains(term: str) -> bool:
        pattern = rf"(?<![a-z]){re.escape(term.lower())}(?![a-z])"
        return re.search(pattern, lowered) is not None

    for key, terms in _CATEGORIES.items():
        if any(contains(term) for term in terms):
            return key
    return None


def _event_from_market(row: dict[str, Any], now: datetime) -> dict[str, Any] | None:
    title = str(row.get("question") or row.get("title") or "").strip()
    category = _category(title)
    if not title or category is None:
        return None
    outcomes = _json_list(row.get("outcomes"))
    prices = _json_list(row.get("outcomePrices"))
    if len(outcomes) != len(prices) or len(outcomes) < 2:
        return None
    yes_index = next(
        (i for i, value in enumerate(outcomes) if str(value).strip().lower() in {"yes", "是"}), None
    )
    if yes_index is None:
        return None
    probability = _number(prices[yes_index])
    if probability is None:
        return None
    # Values from liquidity/volume are USD amounts, not probabilities.
    try:
        liquidity_value = float(row.get("liquidityNum") or row.get("liquidity") or 0)
        volume_value = float(row.get("volume24hr") or 0)
    except (TypeError, ValueError):
        liquidity_value = volume_value = 0
    if liquidity_value < 10_000 or volume_value <= 0:
        return None
    end_date = str(row.get("endDate") or row.get("end_date_iso") or "")
    expiry = None
    if end_date:
        try:
            expiry = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=UTC)
        except ValueError:
            expiry = None
    if expiry is not None and (expiry < now or expiry > now + timedelta(days=365)):
        return None
    outcome = str(outcomes[yes_index]).strip()
    event_id = str(row.get("id") or row.get("conditionId") or row.get("slug") or title)
    return {
        "id": event_id[:160],
        "label": _localize_title(title, category)
        if outcome.lower() == "yes"
        else f"{_localize_title(title, category)} · {outcome}",
        "originalLabel": title if outcome.lower() == "yes" else f"{title} · {outcome}",
        "category": category,
        "probability": round(probability * 100, 2),
        # Gamma returns a market slug for each Yes/No leg, but the public UI
        # page is the parent event.  Linking the leg at /market/<slug> can
        # render an empty shell; use the parent event slug when available and
        # retain the market route only as a last-resort fallback.
        "sourceUrl": _source_url(row),
        "expiryAt": expiry.isoformat() if expiry else None,
    }


def _source_url(row: dict[str, Any]) -> str | None:
    events = row.get("events")
    if isinstance(events, list):
        for event in events:
            if isinstance(event, dict) and event.get("slug"):
                return f"https://polymarket.com/event/{event['slug']}"
    slug = row.get("slug")
    return f"https://polymarket.com/market/{slug}" if slug else None


def _yes_token_id(row: dict[str, Any]) -> str | None:
    outcomes = _json_list(row.get("outcomes"))
    token_ids = _json_list(row.get("clobTokenIds"))
    if len(outcomes) != len(token_ids):
        return None
    yes_index = next(
        (i for i, value in enumerate(outcomes) if str(value).strip().lower() in {"yes", "是"}),
        None,
    )
    if yes_index is None:
        return None
    token = str(token_ids[yes_index]).strip()
    return token or None


def _fetch_historical_points(client: httpx.Client, row: dict[str, Any]) -> list[dict[str, Any]]:
    """Backfill the Yes-leg price history used by the local probability chart."""
    token = _yes_token_id(row)
    if token is None:
        return []
    try:
        response = client.get(
            _CLOB_HISTORY_URL,
            params={"market": token, "interval": "all", "fidelity": 5},
            headers={"User-Agent": "Platform-API macro-expectations"},
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return []
    raw_points = payload.get("history") if isinstance(payload, dict) else None
    if not isinstance(raw_points, list):
        return []
    points: list[dict[str, Any]] = []
    for point in raw_points:
        if not isinstance(point, dict):
            continue
        try:
            timestamp = datetime.fromtimestamp(float(point["t"]), tz=UTC)
            probability = float(point["p"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if not 0 <= probability <= 1:
            continue
        points.append(
            {
                "observedAt": timestamp.isoformat(),
                "probability": round(probability * 100, 2),
            }
        )
    return points[-_HISTORY_MAX_POINTS:]


def fetch_macro_expectations(
    *, timeout_seconds: float = 15.0, limit: int = 200
) -> list[dict[str, Any]]:
    historical_points_by_market: dict[str, list[dict[str, Any]]] = {}
    try:
        # Use the deployment-provided proxy/trust settings; the application
        # never hard-codes a local proxy address.
        with httpx.Client(timeout=timeout_seconds, trust_env=True, follow_redirects=True) as client:
            response = client.get(
                _URL,
                params={
                    "active": "true",
                    "closed": "false",
                    "limit": min(limit, 200),
                    "order": "volume24hr",
                    "ascending": "false",
                },
                headers={"User-Agent": "Platform-API macro-expectations"},
            )
            response.raise_for_status()
            payload = response.json()
            curated_rows: list[dict[str, Any]] = []
            for slug in _CURATED_EVENT_SLUGS:
                try:
                    event_response = client.get(
                        _EVENTS_URL,
                        params={"slug": slug, "active": "true", "closed": "false"},
                        headers={"User-Agent": "Platform-API macro-expectations"},
                    )
                    event_response.raise_for_status()
                    event_payload = event_response.json()
                except Exception:
                    continue
                if not isinstance(event_payload, list):
                    continue
                for event in event_payload:
                    if not isinstance(event, dict):
                        continue
                    for market in event.get("markets", []):
                        if not isinstance(market, dict):
                            continue
                        market = dict(market)
                        market["events"] = [{"slug": event.get("slug")}]
                        curated_rows.append(market)
            payload = [*payload, *curated_rows]
            # Backfill while the shared client is still open. The parsed event
            # list is assembled below after the transport scope closes.
            for row in payload:
                if not isinstance(row, dict):
                    continue
                title = str(row.get("question") or row.get("title") or "").strip()
                if _category(title) != "monetary_policy":
                    continue
                market_id = str(row.get("id") or row.get("conditionId") or row.get("slug") or title)
                historical_points_by_market[market_id] = _fetch_historical_points(client, row)
    except Exception as exc:
        raise ResearchProviderError(
            f"macro_expectation_upstream_unavailable:{type(exc).__name__}"
        ) from exc
    now = datetime.now(UTC)
    parsed_events: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        event = _event_from_market(row, now)
        if event is None:
            continue
        if event["category"] == "monetary_policy":
            market_id = str(
                row.get("id") or row.get("conditionId") or row.get("slug") or event["label"]
            )
            event["_historicalPoints"] = historical_points_by_market.get(market_id, [])
        parsed_events.append(event)
    # The same market can appear in the ranked feed and the curated event
    # lookup. Preserve the first parsed observation and avoid duplicate cards.
    events_by_id = {str(event["id"]): event for event in parsed_events}
    events = list(events_by_id.values())
    events.sort(key=lambda event: (event["category"], -float(event["probability"])))
    return events[:24]


def refresh_macro_expectations(*, force: bool = False) -> str:
    """Atomically publish the feed: ready, up_to_date, stale or error."""
    target = hedge_board_data_root() / "public" / "v1" / "macro" / "expectations.json"
    if not force and target.exists():
        try:
            previous = json.loads(target.read_text(encoding="utf-8"))
            updated = datetime.fromisoformat(
                str(previous.get("updatedAt", "")).replace("Z", "+00:00")
            )
            if datetime.now(UTC) - updated < timedelta(minutes=5):
                return "up_to_date"
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    try:
        events = fetch_macro_expectations()
    except ResearchProviderError:
        # Keep the last valid observations visible, but make the upstream
        # failure explicit so the provider/UI can label the card stale.
        try:
            previous = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(previous, dict) and previous.get("events"):
                previous["status"] = "stale"
                write_local_json("public/v1/macro/expectations.json", previous)
                return "stale"
        except (OSError, ValueError, json.JSONDecodeError, ResearchProviderError):
            pass
        return "error"
    now = datetime.now(UTC)
    old_events: dict[str, dict[str, Any]] = {}
    try:
        previous = json.loads(target.read_text(encoding="utf-8"))
        old_events = {
            str(item.get("id")): item
            for item in previous.get("events", [])
            if isinstance(item, dict)
        }
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    for event in events:
        prior = old_events.get(event["id"], {})
        historical_points = event.pop("_historicalPoints", [])
        history = [point for point in prior.get("history", []) if isinstance(point, dict)]
        history.extend(point for point in historical_points if isinstance(point, dict))
        history.append({"observedAt": now.isoformat(), "probability": event["probability"]})
        deduped = {
            str(point.get("observedAt")): point
            for point in history
            if point.get("observedAt") and point.get("probability") is not None
        }
        event["history"] = [
            deduped[key]
            for key in sorted(deduped)
        ][-_HISTORY_MAX_POINTS:]
    write_local_json(
        "public/v1/macro/expectations.json",
        {
            "schemaVersion": "1.0",
            "status": "ready" if events else "no_data",
            "source": _SOURCE,
            "sourceUrl": "https://polymarket.com/markets",
            "updatedAt": now.isoformat(),
            "events": events,
        },
    )
    return "ready" if events else "no_data"
