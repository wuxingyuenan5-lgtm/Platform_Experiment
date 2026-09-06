from __future__ import annotations

# RSS source definitions and upstream JSON payloads stay compact in this adapter.
# ruff: noqa: E501
import asyncio
import hashlib
import hmac
import importlib.util
import json
import os
import re
import shutil
import time
import xml.etree.ElementTree as element_tree
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path as FilePath

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, HttpUrl, SecretStr, model_validator

from app.auth import Principal, require_permission
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix=f"{settings.api_prefix}/financial-ai", tags=["financial-ai"])
_principal = Depends(require_permission("platform:read"))
_connection_manager = Depends(require_permission("settings.write"))
_SYSTEM = """你是全球变量平台的金融研究助手。只基于提供的事实底稿进行归纳和推演。严格区分已确认事实、模型推断与待验证假设。不要给出买卖建议、目标价格、收益承诺或交易指令。结论应列出关键观察、反方证据和下一步验证项。"""
_SOURCES = (
    ("macro", "Financial Times", "https://www.ft.com/rss/home"),
    ("macro", "Federal Reserve", "https://www.federalreserve.gov/feeds/press_all.xml"),
    ("ai", "OpenAI", "https://openai.com/news/rss.xml"),
    ("ai", "Google Research", "https://research.google/blog/rss/"),
    ("semi", "SemiAnalysis", "https://semianalysis.substack.com/feed"),
    ("energy", "CleanTechnica", "https://cleantechnica.com/feed/"),
    ("bio", "STAT News", "https://www.statnews.com/feed/"),
    ("tech", "TechCrunch", "https://techcrunch.com/feed/"),
    ("robot", "The Robot Report", "https://www.therobotreport.com/feed/"),
    ("auto", "Electrek", "https://electrek.co/feed/"),
    ("space", "SpaceNews", "https://spacenews.com/feed/"),
    ("security", "The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
    ("consumer", "Engadget", "https://www.engadget.com/rss.xml"),
    ("science", "Nature News", "https://www.nature.com/nature.rss"),
)
_GROUPS = (
    ("macro", "财经 / 宏观", "#a87800"),
    ("ai", "AI / 大模型", "#2f6fed"),
    ("semi", "半导体 / 芯片", "#0f766e"),
    ("energy", "能源 / 新能源", "#4d7c0f"),
    ("bio", "生物医药 / 健康", "#be185d"),
    ("tech", "科技 / 互联网", "#6d28d9"),
    ("robot", "机器人 / 自动化", "#14b8a6"),
    ("auto", "汽车 / 新能源车", "#fb7185"),
    ("space", "航天 / 太空", "#8b5cf6"),
    ("security", "网络安全", "#ef4444"),
    ("consumer", "消费电子 / 数码", "#a855f7"),
    ("science", "科学 / 前沿", "#38bdf8"),
)
_radar_cache: tuple[float, dict[str, object]] | None = None
_CONNECTION_PATH = FilePath(settings.database_path).parent / "financial_ai_connection.json"


def _require_gateway_key(x_financial_ai_access_key: str | None = Header(default=None)) -> None:
    expected = settings.financial_ai_access_key_sha256.strip().lower()
    if not expected:
        return
    actual = hashlib.sha256((x_financial_ai_access_key or "").encode()).hexdigest()
    if not hmac.compare_digest(actual, expected):
        raise HTTPException(status_code=401, detail="金融 AI 后端访问密钥无效")


_gateway = Depends(_require_gateway_key)


_CLI = {
    "claude": (["claude", "openclaude"], ["-p", "--disallowedTools", "Bash,Write,Edit"]),
    "qwen": (["qwen"], ["--yolo"]),
    "deepseek": (["deepseek", "codewhale"], ["exec", "--auto"]),
    "codex": (["codex"], ["exec", "--skip-git-repo-check", "-"]),
}


class AiConnection(BaseModel):
    mode: str = "api"
    cli: str = "codex"

    @model_validator(mode="after")
    def valid_mode(self) -> AiConnection:
        if self.mode == "subscription":
            if self.cli not in _CLI:
                raise ValueError("不支持的订阅 CLI")
            return self
        if self.mode != "api":
            raise ValueError("仅支持 API 或订阅 CLI")
        return self


class AiConnectionSave(BaseModel):
    provider: str = Field(default="deepseek", min_length=1, max_length=80)
    base_url: HttpUrl
    api_key: SecretStr | None = None
    model: str = Field(min_length=1, max_length=160)


class AiChatRequest(BaseModel):
    connection: AiConnection
    prompt: str = Field(min_length=1, max_length=12_000)
    context: str = Field(min_length=1, max_length=48_000)


def _event(payload: dict[str, object]) -> bytes:
    return f"{json.dumps(payload, ensure_ascii=False)}\n".encode()


def _completion_url(base_url: HttpUrl) -> str:
    base = str(base_url).rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if not base.endswith(("/v1", "/v3", "/api/v3")):
        base = f"{base}/v1"
    return f"{base}/chat/completions"


def _read_local_connection() -> dict[str, str] | None:
    try:
        payload = json.loads(_CONNECTION_PATH.read_text(encoding="utf-8"))
        if all(str(payload.get(key, "")).strip() for key in ("baseUrl", "apiKey", "model")):
            return {
                key: str(payload.get(key, "")) for key in ("provider", "baseUrl", "apiKey", "model")
            }
    except (OSError, ValueError, TypeError):
        return None
    return None


def _write_local_connection(payload: dict[str, str]) -> None:
    _CONNECTION_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = _CONNECTION_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    temporary.replace(_CONNECTION_PATH)


def _deployment_configuration() -> tuple[HttpUrl, str, str] | None:
    local = _read_local_connection()
    if local:
        return HttpUrl(local["baseUrl"]), local["apiKey"], local["model"]
    return None


def _deployment_status() -> dict[str, object]:
    local = _read_local_connection()
    configured = local is not None or _deployment_configuration() is not None
    return {
        "configured": configured,
        "provider": local["provider"] if local else settings.financial_ai_provider,
        "baseUrl": local["baseUrl"] if local else str(settings.financial_ai_base_url),
        "model": local["model"] if local else settings.financial_ai_model,
        "hasApiKey": configured,
        "message": "本机 AI 配置已保存。" if configured else "尚未保存本机 AI 配置。",
    }


async def _chat_stream(request: AiChatRequest) -> AsyncIterator[bytes]:
    if request.connection.mode == "subscription":
        async for event in _cli_stream(request):
            yield event
        return
    deployment = _deployment_configuration()
    if not deployment:
        yield _event(
            {
                "type": "error",
                "message": "尚未配置 API Key，请先在“接入AI”页面保存。",
            }
        )
        return
    base_url, api_key, model = deployment
    url = _completion_url(base_url)
    body = {
        "model": model,
        "stream": True,
        "temperature": 0.25,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"任务：{request.prompt}\n\n事实底稿：\n{request.context}"},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(90.0, connect=15.0), trust_env=False
        ) as client:
            async with client.stream("POST", url, json=body, headers=headers) as response:
                if response.status_code >= 400:
                    yield _event(
                        {"type": "error", "message": f"模型接口 HTTP {response.status_code}"}
                    )
                    return
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        yield _event({"type": "done"})
                        return
                    try:
                        text = json.loads(raw)["choices"][0].get("delta", {}).get("content")
                    except (IndexError, KeyError, TypeError, json.JSONDecodeError):
                        continue
                    if text:
                        yield _event({"type": "delta", "text": text})
        yield _event({"type": "done"})
    except httpx.HTTPError as exc:
        yield _event({"type": "error", "message": f"模型服务不可用：{exc}"})


def _cli_executable(cli: str) -> str | None:
    definition = _CLI.get(cli)
    return (
        next((path for name in definition[0] if (path := shutil.which(name))), None)
        if definition
        else None
    )


async def _cli_stream(request: AiChatRequest) -> AsyncIterator[bytes]:
    executable = _cli_executable(request.connection.cli)
    if not executable:
        yield _event(
            {
                "type": "error",
                "message": f"本机未检测到 {request.connection.cli} CLI，或尚未登录订阅账号。",
            }
        )
        return
    prompt = f"{_SYSTEM}\n\n任务：{request.prompt}\n\n事实底稿：\n{request.context}"
    args = [executable, *_CLI[request.connection.cli][1]]
    if request.connection.cli != "codex":
        args.append(prompt)
    process = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE if request.connection.cli == "codex" else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        if process.stdin:
            process.stdin.write(prompt.encode("utf-8"))
            await process.stdin.drain()
            process.stdin.close()
        assert process.stdout
        while chunk := await asyncio.wait_for(process.stdout.read(1024), timeout=300):
            yield _event({"type": "delta", "text": chunk.decode("utf-8", errors="replace")})
        return_code = await process.wait()
        if return_code:
            detail = (
                (await process.stderr.read()).decode("utf-8", errors="replace")[-800:]
                if process.stderr
                else ""
            )
            yield _event({"type": "error", "message": detail or f"CLI 退出码 {return_code}"})
            return
        yield _event({"type": "done"})
    except TimeoutError:
        process.kill()
        yield _event({"type": "error", "message": "CLI 运行超过 300 秒，已停止。"})


@router.post("/chat")
async def chat(
    request: AiChatRequest, _: Principal = _principal, __: None = _gateway
) -> StreamingResponse:
    return StreamingResponse(_chat_stream(request), media_type="application/x-ndjson")


@router.get("/connection")
async def connection_status(_: Principal = _principal) -> dict[str, object]:
    return _deployment_status()


@router.put("/connection")
async def save_connection(
    request: AiConnectionSave, _: Principal = _connection_manager
) -> dict[str, object]:
    previous = _read_local_connection()
    api_key = request.api_key.get_secret_value().strip() if request.api_key else ""
    if not api_key and previous:
        api_key = previous["apiKey"]
    if not api_key:
        raise HTTPException(status_code=422, detail="首次保存必须填写 API Key")
    _write_local_connection(
        {
            "provider": request.provider,
            "baseUrl": str(request.base_url).rstrip("/"),
            "apiKey": api_key,
            "model": request.model,
        }
    )
    return _deployment_status()


@router.delete("/connection")
async def clear_connection(_: Principal = _connection_manager) -> dict[str, object]:
    try:
        _CONNECTION_PATH.unlink(missing_ok=True)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="本机 AI 配置清除失败") from exc
    return _deployment_status()


@router.post("/test-connection")
async def test_connection(
    connection: AiConnection, _: Principal = _principal, __: None = _gateway
) -> dict[str, object]:
    if connection.mode == "subscription":
        available = _cli_executable(connection.cli) is not None
        return {
            "ok": available,
            "message": "CLI 已安装，可用于订阅调用。"
            if available
            else "未检测到 CLI，请先安装并在本机完成登录。",
        }
    deployment = _deployment_configuration()
    if not deployment:
        return {
            "ok": False,
            "message": "尚未配置 API Key，请先在“接入AI”页面保存。",
        }
    base_url, api_key, model = deployment
    url = _completion_url(base_url)
    try:
        async with httpx.AsyncClient(timeout=20.0, trust_env=False) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "stream": False,
                    "temperature": 0.3,
                    "messages": [{"role": "user", "content": "只回复 OK"}],
                },
            )
        if response.status_code < 400:
            return {"ok": True, "message": "API 连接正常。"}
        try:
            payload = response.json()
            provider_message = str(
                (payload.get("error") or {}).get("message") or payload.get("message") or ""
            )[:300]
        except (ValueError, AttributeError):
            provider_message = ""
        if response.status_code in {401, 403}:
            message = "API Key 无效，或当前账号没有所选模型的访问权限。"
        elif response.status_code == 404:
            message = "模型端点或模型名称不存在，请检查 Base URL 与 Model。"
        else:
            message = provider_message or f"模型接口 HTTP {response.status_code}"
        return {"ok": False, "message": message}
    except httpx.HTTPError as exc:
        return {"ok": False, "message": f"连接失败：{exc}"}


async def _provider_probe(key: str, name: str, url: str) -> dict[str, object]:
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True, trust_env=False) as client:
            response = await client.get(url, headers={"User-Agent": "VariableGlobal health probe"})
        latency = round((time.perf_counter() - started) * 1000)
        return {
            "key": key,
            "name": name,
            "available": response.status_code < 500,
            "status": "正常" if response.status_code < 500 else f"HTTP {response.status_code}",
            "latencyMs": latency,
        }
    except httpx.HTTPError:
        return {"key": key, "name": name, "available": False, "status": "当前探测不可用"}


@router.get("/capabilities")
async def capabilities(_: Principal = _principal, __: None = _gateway) -> dict[str, object]:
    cli = [
        {
            "key": key,
            "name": key.title(),
            "available": _cli_executable(key) is not None,
            "status": "已安装" if _cli_executable(key) else "未检测到",
        }
        for key in _CLI
    ]
    providers = await asyncio.gather(
        _provider_probe("tencent", "Tencent", "https://qt.gtimg.cn/q=sh000001"),
        _provider_probe(
            "eastmoney", "Eastmoney", "https://push2.eastmoney.com/api/qt/stock/get?secid=1.000001"
        ),
    )
    providers.append(
        {
            "key": "akshare",
            "name": "AkShare",
            "available": importlib.util.find_spec("akshare") is not None,
            "status": "已安装" if importlib.util.find_spec("akshare") else "未安装",
        }
    )
    return {"cli": cli, "providers": providers, "deployment": _deployment_status()}


@router.get("/global-stock/{symbol}")
async def global_stock(
    symbol: str = Path(min_length=1, max_length=24),
    period: str = Query(default="day", pattern="^(60m|day|week|month)$"),
    _: Principal = _principal,
    __: None = _gateway,
) -> dict[str, object]:
    normalized = symbol.strip().upper()
    if not re.fullmatch(r"[A-Z0-9.^-]+", normalized):
        raise HTTPException(status_code=422, detail="证券代码格式无效")
    if normalized.isdigit() and len(normalized) == 5:
        normalized = f"{normalized.lstrip('0') or '0'}.HK"
    elif normalized.isdigit() and len(normalized) == 6:
        normalized = f"{normalized}.{'SS' if normalized.startswith(('5', '6', '9')) else 'SZ'}"
    eastmoney: dict[str, object] = {}
    if not normalized.endswith((".SS", ".SZ")):
        query = normalized.split(".", 1)[0]
        try:
            async with httpx.AsyncClient(timeout=12.0, trust_env=False) as em_client:
                search = await em_client.get(
                    "https://searchapi.eastmoney.com/api/suggest/get",
                    params={
                        "input": query,
                        "type": 14,
                        "token": "D43BF722C8E33BDC906FB84D85E326E8",
                        "count": 10,
                    },
                    headers={"User-Agent": "Mozilla/5.0 VariableGlobal"},
                )
                search.raise_for_status()
                candidates = (search.json().get("QuotationCodeTable") or {}).get("Data") or []
                supported = {105: ".O", 106: ".N", 107: ".O", 116: ".HK", 177: ".KS"}
                matches = [
                    row
                    for row in candidates
                    if int(row.get("MktNum") or -1) in supported
                    and str(row.get("Code") or "").upper() == query
                ]
                if matches:
                    match = matches[0]
                    market_number = int(match["MktNum"])
                    code = str(match["Code"])
                    quote_response = await em_client.get(
                        "https://push2delay.eastmoney.com/api/qt/stock/get",
                        params={
                            "secid": f"{market_number}.{code}",
                            "fields": "f43,f44,f45,f46,f48,f57,f58,f59,f60,f116,f170",
                        },
                        headers={"User-Agent": "Mozilla/5.0 VariableGlobal"},
                    )
                    quote_response.raise_for_status()
                    quote_data = quote_response.json().get("data") or {}
                    decimals = quote_data.get("f59")
                    divisor = 10 ** (decimals if isinstance(decimals, int) else 2)

                    def em_price(field: str) -> float | None:
                        value = quote_data.get(field)
                        return value / divisor if isinstance(value, (int, float)) else None

                    eastmoney = {
                        "name": match.get("Name") or quote_data.get("f58"),
                        "previousClose": em_price("f60"),
                        "open": em_price("f46"),
                        "dayHigh": em_price("f44"),
                        "dayLow": em_price("f45"),
                        "amount": quote_data.get("f48"),
                        "marketCap": quote_data.get("f116"),
                        "changePct": (
                            quote_data["f170"] / 100
                            if isinstance(quote_data.get("f170"), (int, float))
                            else None
                        ),
                    }
                    if market_number != 177:
                        report = (
                            "RPT_HKF10_FN_GMAININDICATOR"
                            if market_number == 116
                            else "RPT_USF10_FN_GMAININDICATOR"
                        )
                        suffix = supported[market_number]
                        metrics_response = await em_client.get(
                            "https://datacenter-web.eastmoney.com/api/data/v1/get",
                            params={
                                "reportName": report,
                                "columns": "ALL",
                                "filter": f'(SECUCODE="{code}{suffix}")',
                                "pageNumber": 1,
                                "pageSize": 1,
                                "sortColumns": "REPORT_DATE",
                                "sortTypes": "-1",
                            },
                            headers={"User-Agent": "Mozilla/5.0 VariableGlobal"},
                        )
                        metrics_rows = (metrics_response.json().get("result") or {}).get(
                            "data"
                        ) or []
                        if metrics_rows:
                            row = metrics_rows[0]
                            eastmoney["metrics"] = {
                                "reportDate": str(row.get("REPORT_DATE") or "")[:10],
                                "revenue": row.get("OPERATE_INCOME"),
                                "revenueYoy": row.get("OPERATE_INCOME_YOY"),
                                "netProfit": row.get("PARENT_HOLDER_NETPROFIT")
                                or row.get("HOLDER_PROFIT"),
                                "eps": row.get("BASIC_EPS"),
                                "roe": row.get("ROE_AVG"),
                                "grossMargin": row.get("GROSS_PROFIT_RATIO"),
                                "netMargin": row.get("NET_PROFIT_RATIO"),
                                "debtRatio": row.get("DEBT_ASSET_RATIO"),
                            }
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            eastmoney = {}
    urls = (
        f"https://query2.finance.yahoo.com/v8/finance/chart/{normalized}",
        f"https://query1.finance.yahoo.com/v8/finance/chart/{normalized}",
    )
    period_params = {
        "60m": {"range": "1mo", "interval": "60m"},
        "day": {"range": "6mo", "interval": "1d"},
        "week": {"range": "2y", "interval": "1wk"},
        "month": {"range": "5y", "interval": "1mo"},
    }[period]
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, trust_env=True) as client:
            response: httpx.Response | None = None
            last_error: Exception | None = None
            for url in urls:
                try:
                    candidate = await client.get(
                        url,
                        params=period_params,
                        headers={"User-Agent": "Mozilla/5.0 VariableGlobal"},
                    )
                    candidate.raise_for_status()
                    response = candidate
                    break
                except httpx.HTTPError as exc:
                    last_error = exc
            if response is None:
                raise last_error or httpx.RequestError("全球证券行情无可用上游")
        result = response.json()["chart"]["result"][0]
        meta = result["meta"]
        timestamps = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        closes = quote.get("close") or []
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        volumes = quote.get("volume") or []
        chart = [
            {
                "time": datetime.fromtimestamp(ts, UTC).date().isoformat(),
                "open": open_value,
                "high": high_value,
                "low": low_value,
                "close": close,
                "volume": volume,
            }
            for ts, open_value, high_value, low_value, close, volume in zip(
                timestamps, opens, highs, lows, closes, volumes, strict=False
            )
            if close is not None
        ]
        latest_bar = chart[-1] if chart else {}
        previous_bar = chart[-2] if len(chart) > 1 else {}
        price = meta.get("regularMarketPrice") or latest_bar.get("close")
        previous = (
            eastmoney.get("previousClose")
            or meta.get("regularMarketPreviousClose")
            or previous_bar.get("close")
            or meta.get("previousClose")
            or meta.get("chartPreviousClose")
        )
        change_pct = (
            ((price - previous) / previous * 100)
            if isinstance(price, (int, float)) and isinstance(previous, (int, float)) and previous
            else None
        )
        return {
            "symbol": symbol.upper(),
            "sourceSymbol": normalized,
            "name": meta.get("longName")
            or meta.get("shortName")
            or eastmoney.get("name")
            or normalized,
            "market": meta.get("exchangeName") or meta.get("fullExchangeName"),
            "currency": meta.get("currency"),
            "price": price,
            "previousClose": previous,
            "changePct": eastmoney.get("changePct")
            if eastmoney.get("changePct") is not None
            else change_pct,
            "open": eastmoney.get("open")
            or meta.get("regularMarketOpen")
            or latest_bar.get("open"),
            "dayHigh": eastmoney.get("dayHigh")
            or meta.get("regularMarketDayHigh")
            or latest_bar.get("high"),
            "dayLow": eastmoney.get("dayLow")
            or meta.get("regularMarketDayLow")
            or latest_bar.get("low"),
            "volume": meta.get("regularMarketVolume") or latest_bar.get("volume"),
            "amount": eastmoney.get("amount"),
            "marketCap": eastmoney.get("marketCap") or meta.get("marketCap"),
            "metrics": eastmoney.get("metrics"),
            "fiftyTwoWeekHigh": meta.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": meta.get("fiftyTwoWeekLow"),
            "chart": chart,
            "source": "Yahoo Finance",
            "sourceUrl": f"https://finance.yahoo.com/quote/{normalized}",
            "period": period,
        }
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"全球证券行情暂不可用：{exc}") from exc


def _tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


async def _feed(
    client: httpx.AsyncClient, group: str, source: str, url: str
) -> tuple[str, list[dict[str, object]], dict[str, str] | None]:
    try:
        response = await client.get(url, headers={"User-Agent": "VariableGlobal research radar"})
        response.raise_for_status()
        root = element_tree.fromstring(response.content)
    except (httpx.HTTPError, element_tree.ParseError) as exc:
        return group, [], {"group": group, "source": source, "message": type(exc).__name__}
    result: list[dict[str, object]] = []
    for node in root.iter():
        if _tag_name(node.tag) not in {"item", "entry"} or len(result) >= 8:
            continue
        fields = {_tag_name(child.tag): child for child in node}
        title = re.sub(
            r"\s+",
            " ",
            re.sub(r"<[^>]+>", "", fields.get("title", element_tree.Element("x")).text or ""),
        ).strip()
        link_node = fields.get("link", element_tree.Element("x"))
        link = link_node.attrib.get("href") or (link_node.text or "")
        date_node = next(
            (fields[key] for key in ("pubDate", "published", "updated") if key in fields), None
        )
        try:
            date = parsedate_to_datetime(date_node.text if date_node is not None else "")
            timestamp = int(date.timestamp()) if date else 0
            shown = date.astimezone().strftime("%m-%d %H:%M") if date else "—"
        except (TypeError, ValueError):
            timestamp, shown = 0, "—"
        if title:
            result.append(
                {
                    "title": title,
                    "url": link,
                    "source": source,
                    "publishedAt": shown,
                    "timestamp": timestamp,
                }
            )
    return group, result, None


@router.get("/news-radar")
async def news_radar(
    refresh: bool = Query(default=False),
    _: Principal = _principal,
    __: None = _gateway,
) -> dict[str, object]:
    global _radar_cache  # noqa: PLW0603 - bounded process cache owned by this adapter
    if not refresh and _radar_cache and time.monotonic() - _radar_cache[0] < 300:
        return _radar_cache[1]
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, trust_env=False) as client:
        loaded = await asyncio.gather(*(_feed(client, *item) for item in _SOURCES))
    grouped: dict[str, list[dict[str, object]]] = {key: [] for key, _, _ in _GROUPS}
    failures = []
    for key, items, failure in loaded:
        grouped[key].extend(items)
        if failure:
            failures.append(failure)
    payload = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "partialFailures": failures,
        "industries": [
            {
                "key": key,
                "name": name,
                "accent": accent,
                "items": sorted(
                    grouped[key], key=lambda item: int(item["timestamp"]), reverse=True
                )[:20],
            }
            for key, name, accent in _GROUPS
        ],
    }
    _radar_cache = (time.monotonic(), payload)
    return payload


__all__ = ["router"]
