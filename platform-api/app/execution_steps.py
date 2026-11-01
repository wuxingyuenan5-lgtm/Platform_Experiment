"""Append-only execution step timeline.

Every order attempt (including the ones that never become an order because a
safety gate rejected them) writes one row per stage into ``execution_steps``.
The recorder is deliberately fail-open: a timeline write must never change the
outcome of a trade.  Reads are served by ``list_execution_steps`` which returns
the ordered timeline for one trace, batch or order.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import monotonic
from typing import Any, Iterator, Sequence
from uuid import uuid4

from fastapi import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.database import connection

logger = logging.getLogger(__name__)

PASSED = "passed"
BLOCKED = "blocked"
FAILED = "failed"
INFO = "info"

TERMINAL_STATUSES = {BLOCKED, FAILED}

# Stage identifiers are the stable contract between the recorder and the UI.
# Keep them ordered as the real execution advances so the timeline reads
# top-to-bottom even when two legs interleave.
STAGE_LABELS: dict[str, str] = {
    "BATCH_REQUEST_VALIDATED": "批次请求校验",
    "BATCH_IDEMPOTENCY_CHECKED": "幂等键检查",
    "BATCH_RISK_PREFLIGHT": "策略风险准入",
    "BATCH_ACCOUNT_AUTHORIZED": "账户交易授权",
    "BATCH_RESOURCES_CLAIMED": "资金与资源占用",
    "BATCH_LEG_DEADLINE": "执行腿截止时间",
    "BATCH_LEG_SUBMITTING": "执行腿提交",
    "BATCH_LEG_RESULT": "执行腿成交结果",
    "BATCH_HEDGE_RESIZED": "对冲手数重算",
    "BATCH_RISK_SETTLED": "残余敞口结算",
    "BATCH_FINAL": "批次终态",
    "ORDER_REQUEST_VALIDATED": "订单请求校验",
    "ORDER_LOCAL_CREATED": "本地建单",
    "GATE_ACCOUNT_LOOKUP": "账户存在性",
    "GATE_ACCOUNT_ELIGIBLE": "账户可交易状态",
    "GATE_CREDENTIAL_REFERENCE": "凭据引用安全",
    "GATE_INSTRUMENT_LOOKUP": "合约存在性",
    "GATE_CONTRACT_SPEC": "合约规格有效性",
    "GATE_LIVE_SWITCH": "实盘总开关",
    "GATE_LIVE_SWITCH_FINAL": "实盘总开关（最终校验）",
    "GATE_NATIVE_SPEC": "交易所原生规格校验",
    "GATE_MIN_QUANTITY": "最小下单量",
    "GATE_QUANTITY_STEP": "数量步长对齐",
    "GATE_PRICE_TICK": "价格最小变动对齐",
    "GATE_LIVE_IDENTITY": "实盘身份边界",
    "GATE_STRATEGY_BINDING": "策略账户绑定",
    "GATE_RESIDUAL_EXPOSURE": "风险敞口策略",
    "GATE_RECONCILIATION": "对账差异",
    "ORDER_DISPATCH_STARTED": "提交执行运行时",
    "ORDER_DISPATCH_REJECTED": "运行时拒单",
    "ORDER_EVENTS_APPLIED": "成交事件回写",
    "ORDER_FINAL": "订单终态",
}

# Reason codes never carry free-text only; the detail keeps the original
# upstream message so nothing is lost.
REASON_LABELS: dict[str, str] = {
    "ACCOUNT_NOT_FOUND": "账户不存在",
    "ACCOUNT_NOT_ELIGIBLE": "账户状态不可下单",
    "CREDENTIAL_REFERENCE_UNSAFE": "凭据引用不合规",
    "INSTRUMENT_NOT_FOUND": "合约不存在",
    "CONTRACT_SPEC_MISSING": "合约缺少生效规格",
    "LIVE_TRADING_DISABLED": "实盘总开关未开启",
    "NATIVE_SPEC_UNAVAILABLE": "交易所原生规格不可用",
    "QUANTITY_BELOW_MINIMUM": "数量低于最小下单量",
    "QUANTITY_STEP_MISALIGNED": "数量未对齐步长",
    "PRICE_TICK_MISALIGNED": "价格未对齐最小变动",
    "LIVE_IDENTITY_MISSING": "缺少策略或指令身份",
    "STRATEGY_BINDING_MISSING": "账户无有效策略交易绑定",
    "RESIDUAL_EXPOSURE_BLOCKED": "风险敞口策略拦截",
    "RECONCILIATION_BLOCKING": "存在未处理的对账差异",
    "LIMIT_ORDER_REQUIRES_PRICE": "限价单缺少价格",
    "POSITION_TARGET_REQUIRES_REDUCE_ONLY": "平仓目标必须只减仓",
    "EXECUTION_POLICY_REQUIRES_LIMIT": "执行策略要求限价单",
    "RUNTIME_REJECTED": "执行运行时拒绝",
    "RUNTIME_UNAVAILABLE": "执行运行时不可达",
    "RESULT_UNKNOWN": "执行结果未知",
    "BATCH_BLOCKED_BY_ACTIVE_BATCH": "存在阻塞中的执行批次",
    "LEG_DEADLINE_EXCEEDED": "执行腿超时",
    "LEG_STATUS_INCOMPLETE": "执行腿未完全成交",
    "HEDGE_RESIZE_REJECTED": "对冲手数重算被拒",
    "RISK_RESIDUAL_UNRESOLVED": "残余敞口未清零",
    "EVENT_PROJECTION_FAILED": "成交事件回写失败",
    "OK": "通过",
}


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def new_trace_id() -> str:
    return f"trc_{uuid4().hex}"


def stage_label(stage: str) -> str:
    return STAGE_LABELS.get(stage, stage)


def reason_label(reason_code: str | None) -> str | None:
    if reason_code is None:
        return None
    return REASON_LABELS.get(reason_code, reason_code)


def _safe_payload(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)
    if not cleaned:
        return None
    return json.dumps(cleaned, ensure_ascii=False, sort_keys=True)


@dataclass
class StepRecorder:
    """Writes one row per execution stage for a single trace."""

    trace_id: str = field(default_factory=new_trace_id)
    batch_id: str | None = None
    order_id: str | None = None
    command_id: str | None = None
    enabled: bool = True
    _sequence: int | None = field(default=None, init=False, repr=False)
    _warned: bool = field(default=False, init=False, repr=False)

    def bind(
        self,
        *,
        batch_id: str | None = None,
        order_id: str | None = None,
        command_id: str | None = None,
    ) -> None:
        if batch_id is not None:
            self.batch_id = batch_id
        if order_id is not None:
            self.order_id = order_id
        if command_id is not None:
            self.command_id = command_id

    def child(self, *, order_id: str | None = None, command_id: str | None = None) -> "StepRecorder":
        """Same trace, different order/command boundary (one execution leg)."""

        return StepRecorder(
            trace_id=self.trace_id,
            batch_id=self.batch_id,
            order_id=order_id,
            command_id=command_id,
            enabled=self.enabled,
        )

    def _next_sequence(self) -> int:
        # Read the current maximum every time: a trace can be written by several
        # leg recorders (one per order) and they must never reuse a sequence.
        with connection() as db:
            row = db.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM execution_steps WHERE trace_id = ?",
                (self.trace_id,),
            ).fetchone()
        return (int(row[0]) if row is not None else 0) + 1

    def record(
        self,
        stage: str,
        status: str = PASSED,
        *,
        reason_code: str | None = None,
        reason_detail: str | None = None,
        status_code: int | None = None,
        duration_ms: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Append one step. Never raises: timeline writes must not gate trading."""

        if not self.enabled:
            return
        try:
            sequence = self._next_sequence()
            with connection() as db:
                db.execute(
                    """
                    INSERT INTO execution_steps (
                        id, trace_id, batch_id, order_id, command_id, sequence,
                        stage, status, reason_code, reason_detail, status_code,
                        duration_ms, payload_json, occurred_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        self.trace_id,
                        self.batch_id,
                        self.order_id,
                        self.command_id,
                        sequence,
                        stage,
                        status,
                        reason_code,
                        reason_detail,
                        status_code,
                        duration_ms,
                        _safe_payload(payload),
                        utc_now_iso(),
                    ),
                )
        except sqlite3.Error as exc:
            self._sequence = None
            if not self._warned:
                self._warned = True
                logger.warning("execution step write skipped: %s", exc)

    def step(
        self,
        stage: str,
        *,
        payload: dict[str, Any] | None = None,
        status: str = PASSED,
    ) -> "StepContext":
        return StepContext(self, stage, payload=payload, status=status)

    def block(
        self,
        stage: str,
        *,
        reason_code: str,
        detail: str,
        status_code: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.record(
            stage,
            BLOCKED,
            reason_code=reason_code,
            reason_detail=detail,
            status_code=status_code,
            payload=payload,
        )

    def fail(
        self,
        stage: str,
        *,
        reason_code: str,
        detail: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.record(
            stage,
            FAILED,
            reason_code=reason_code,
            reason_detail=detail,
            payload=payload,
        )


class StepContext:
    """Context manager that records passed/blocked/failed with a duration."""

    def __init__(
        self,
        recorder: StepRecorder,
        stage: str,
        *,
        payload: dict[str, Any] | None = None,
        status: str = PASSED,
    ) -> None:
        self._recorder = recorder
        self._stage = stage
        self._status = status
        self._payload = dict(payload or {})
        self._started = 0.0

    def __enter__(self) -> "StepContext":
        self._started = monotonic()
        return self

    def note(self, **values: Any) -> None:
        self._payload.update(values)

    def _elapsed(self) -> int:
        return max(0, int((monotonic() - self._started) * 1000))

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is None:
            self._recorder.record(
                self._stage,
                self._status,
                duration_ms=self._elapsed(),
                payload=self._payload,
            )
            return False

        detail = str(exc.detail) if isinstance(exc, HTTPException) else str(exc)
        status_code = getattr(exc, "status_code", None)
        reason_code = self._reason_code(exc, detail)
        status = BLOCKED if isinstance(exc, HTTPException) else FAILED
        self._recorder.record(
            self._stage,
            status,
            reason_code=reason_code,
            reason_detail=detail,
            status_code=status_code if isinstance(status_code, int) else None,
            duration_ms=self._elapsed(),
            payload=self._payload,
        )
        return False

    def _reason_code(self, exc: BaseException, detail: str) -> str:
        explicit = getattr(exc, "execution_reason_code", None)
        if isinstance(explicit, str) and explicit:
            return explicit
        mapped = REASON_FROM_DETAIL.get(detail.strip())
        if mapped is not None:
            return mapped
        if isinstance(exc, HTTPException):
            return f"HTTP_{exc.status_code}"
        return exc.__class__.__name__.upper()


# The safety gates raise plain HTTPException with human readable messages.  The
# mapping keeps the code stable without rewriting every call site.
REASON_FROM_DETAIL: dict[str, str] = {
    "Account not found": "ACCOUNT_NOT_FOUND",
    "Account is not active": "ACCOUNT_NOT_ELIGIBLE",
    "Account credential reference is unsafe": "CREDENTIAL_REFERENCE_UNSAFE",
    "Instrument not found": "INSTRUMENT_NOT_FOUND",
    "Instrument has no active contract specification": "CONTRACT_SPEC_MISSING",
    "Live trading is disabled by global safety switch": "LIVE_TRADING_DISABLED",
    "Native order specification is unavailable": "NATIVE_SPEC_UNAVAILABLE",
    "Order quantity is below minimum": "QUANTITY_BELOW_MINIMUM",
    "Order quantity is not aligned to quantity step": "QUANTITY_STEP_MISALIGNED",
    "Order price is not aligned to price tick": "PRICE_TICK_MISALIGNED",
    "Live order lacks a strategy and command identity boundary": "LIVE_IDENTITY_MISSING",
    "Account has no active strategy trading binding": "STRATEGY_BINDING_MISSING",
    "Outstanding open or accepted reconciliation differences exist": "RECONCILIATION_BLOCKING",
    "Limit orders require price": "LIMIT_ORDER_REQUIRES_PRICE",
    "A close position target requires reduce-only execution": "POSITION_TARGET_REQUIRES_REDUCE_ONLY",
    "FOK and PostOnly Chase policies require a limit order": "EXECUTION_POLICY_REQUIRES_LIMIT",
}

# Shared no-op recorder: gates can always call ``.step()`` without a branch.
DISABLED_RECORDER = StepRecorder(enabled=False)

# One recorder per HTTP request. A middleware binds it so every entry point
# (batch, trade command, funding instruction, legacy order) shares one trace
# without threading the object through four service layers.
_ACTIVE_RECORDER: ContextVar[StepRecorder | None] = ContextVar(
    "execution_step_recorder", default=None
)


def active_recorder() -> StepRecorder | None:
    return _ACTIVE_RECORDER.get()


class ExecutionTraceMiddleware:
    """Bind one recorder per request and echo its trace id in the response."""

    header_name = b"x-execution-trace-id"

    def __init__(self, app: "ASGIApp") -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        raw = dict(scope.get("headers") or []).get(self.header_name)
        trace_id = ""
        if raw:
            try:
                trace_id = raw.decode("latin-1").strip()
            except (UnicodeDecodeError, AttributeError):
                trace_id = ""
        recorder = StepRecorder(trace_id=trace_id) if 0 < len(trace_id) <= 128 else StepRecorder()
        token = _ACTIVE_RECORDER.set(recorder)

        async def send_with_trace(message: Message) -> None:
            if message["type"] == "http.response.start":
                message = {
                    **message,
                    "headers": [
                        *(message.get("headers") or []),
                        (self.header_name, recorder.trace_id.encode("latin-1")),
                    ],
                }
            await send(message)

        try:
            await self.app(scope, receive, send_with_trace)
        finally:
            _ACTIVE_RECORDER.reset(token)


@contextmanager
def optional_step(
    recorder: StepRecorder | None,
    stage: str,
    *,
    payload: dict[str, Any] | None = None,
) -> Iterator[StepContext | None]:
    """Run ``stage`` under a recorder when one exists."""

    if recorder is None:
        yield None
        return
    with recorder.step(stage, payload=payload) as step:
        yield step


def list_execution_steps(
    *,
    trace_id: str | None = None,
    batch_id: str | None = None,
    order_id: str | None = None,
    command_ids: Sequence[str] | None = None,
    order_ids: Sequence[str] | None = None,
    limit: int = 500,
) -> dict[str, Any]:
    """Return the ordered timeline plus a compact summary of the failure point."""

    command_scope = [str(item) for item in (command_ids or []) if item]
    order_scope = [str(item) for item in (order_ids or []) if item]

    if not any((trace_id, batch_id, order_id, command_scope, order_scope)):
        raise HTTPException(
            status_code=422,
            detail="execution steps require traceId, batchId or orderId",
        )

    clauses: list[str] = []
    params: list[Any] = []
    matched_by = "traceId"
    if trace_id:
        clauses.append("trace_id = ?")
        params.append(trace_id)
    elif batch_id:
        clauses.append("batch_id = ?")
        params.append(batch_id)
        matched_by = "batchId"
    elif command_scope or order_scope:
        # A batch is dispatched leg by leg. Each leg opens its own trace, so the
        # batch timeline has to be the union across the legs. command_id is the
        # only key present on every dispatched step, so it leads the match.
        scope_clauses: list[str] = []
        if command_scope:
            scope_clauses.append(
                "command_id IN (" + ",".join("?" for _ in command_scope) + ")"
            )
            params.extend(command_scope)
        if order_scope:
            scope_clauses.append("order_id IN (" + ",".join("?" for _ in order_scope) + ")")
            params.extend(order_scope)
        clauses.append("(" + " OR ".join(scope_clauses) + ")")
        matched_by = "commandId"
    else:
        clauses.append("order_id = ?")
        params.append(order_id)
        matched_by = "orderId"

    bounded = max(1, min(int(limit), 2000))
    with connection() as db:
        rows = db.execute(
            f"""
            SELECT id, trace_id, batch_id, order_id, command_id, sequence,
                   stage, status, reason_code, reason_detail, status_code,
                   duration_ms, payload_json, occurred_at
            FROM execution_steps
            WHERE {' AND '.join(clauses)}
            ORDER BY occurred_at ASC, sequence ASC
            LIMIT ?
            """,
            (*params, bounded),
        ).fetchall()

    steps: list[dict[str, Any]] = []
    for row in rows:
        payload_raw = row["payload_json"]
        try:
            payload = json.loads(payload_raw) if payload_raw else None
        except ValueError:
            payload = None
        steps.append(
            {
                "id": row["id"],
                "traceId": row["trace_id"],
                "batchId": row["batch_id"],
                "orderId": row["order_id"],
                "commandId": row["command_id"],
                "sequence": int(row["sequence"]),
                "stage": row["stage"],
                "stageLabel": stage_label(row["stage"]),
                "status": row["status"],
                "reasonCode": row["reason_code"],
                "reasonLabel": reason_label(row["reason_code"]),
                "reasonDetail": row["reason_detail"],
                "statusCode": row["status_code"],
                "durationMs": row["duration_ms"],
                "payload": payload,
                "occurredAt": row["occurred_at"],
            }
        )

    resolved_trace = trace_id or (steps[0]["traceId"] if steps else None)
    blocked = next((item for item in steps if item["status"] in TERMINAL_STATUSES), None)
    final = next(
        (
            item
            for item in reversed(steps)
            if item["stage"] in {"ORDER_FINAL", "BATCH_FINAL"}
        ),
        None,
    )
    if final is not None:
        outcome = final["status"]
    elif blocked is not None:
        outcome = blocked["status"]
    elif steps:
        outcome = "in_progress"
    else:
        outcome = "not_found"

    return {
        "traceId": resolved_trace,
        "matchedBy": matched_by,
        "summary": {
            "outcome": outcome,
            "stepCount": len(steps),
            "startedAt": steps[0]["occurredAt"] if steps else None,
            "finishedAt": steps[-1]["occurredAt"] if steps else None,
            "blockedStage": blocked["stage"] if blocked else None,
            "blockedStageLabel": blocked["stageLabel"] if blocked else None,
            "blockedReasonCode": blocked["reasonCode"] if blocked else None,
            "blockedReasonLabel": blocked["reasonLabel"] if blocked else None,
            "blockedReasonDetail": blocked["reasonDetail"] if blocked else None,
            "totalDurationMs": sum(
                item["durationMs"] for item in steps if isinstance(item["durationMs"], int)
            ),
        },
        "steps": steps,
    }


__all__ = [
    "BLOCKED",
    "DISABLED_RECORDER",
    "FAILED",
    "INFO",
    "PASSED",
    "STAGE_LABELS",
    "StepRecorder",
    "list_execution_steps",
    "new_trace_id",
    "optional_step",
    "reason_label",
    "stage_label",
]
