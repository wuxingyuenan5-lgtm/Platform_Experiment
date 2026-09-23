# execution-runtime

Platform Execution Runtime是Platform的独立交易执行运行时。

## 当前范围

- 独立 FastAPI 进程。
- 最小 SubmitOrderCommand / ExecutionEvent 契约。
- Fake Gateway。
- 不处理用户权限、策略配置、PnL 或平台业务持久化。

跨所黄金的 MT5 时段由 `VG_RUNTIME_CROSS_SPREAD_MT5_TRADING_SCHEDULE`（按
MT5 服务器时区的周历窗口）、`VG_RUNTIME_CROSS_SPREAD_MT5_SCHEDULE_TIMEZONE`
和 `VG_RUNTIME_CROSS_SPREAD_MT5_SESSION_OVERRIDES`（节假日/临时维护日期覆盖）
驱动；`VG_RUNTIME_CROSS_SPREAD_AUTO_EXIT_GUARD_MINUTES` 控制开收盘前后的
自动 TP/SL 缓冲时间。缓冲期间保留人工开平能力，完整休市或未知时段 fail-closed。
Bybit MT5 默认使用 `Bybit/MT5` 时区：UTC+2，按 Bybit 公布的 3 月第二个周日
至 11 月第一个周日切换 UTC+3；不要用北京时间或 `Europe/Athens` 代替它。
规则来源：[Bybit TradFi FAQ](https://www.cbybit.com/en/help-center/article/FAQ-TradFi-MT5)。

## 本地运行

```bash
cd execution-runtime
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8100
```

检查：

```text
GET  http://127.0.0.1:8100/health
POST http://127.0.0.1:8100/commands/orders
```

测试：

```bash
pytest
```
