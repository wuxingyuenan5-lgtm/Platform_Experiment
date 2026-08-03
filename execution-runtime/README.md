# execution-runtime

Platform Execution Runtime是Platform的独立交易执行运行时。

## 当前范围

- 独立 FastAPI 进程。
- 最小 SubmitOrderCommand / ExecutionEvent 契约。
- Fake Gateway。
- 不处理用户权限、策略配置、PnL 或平台业务持久化。

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
