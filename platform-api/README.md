# platform-api

Variable-Global 的模块化单体业务后端。

## 当前范围

- FastAPI 应用入口。
- 环境配置。
- 健康检查。
- 后续承载 Strategy、Trading、Account、PnL 和 Risk 模块。
- 不直接导入交易所、MT5 或 CTP SDK。

## 本地运行

```bash
cd platform-api
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

检查：

```text
GET http://127.0.0.1:8000/health
GET http://127.0.0.1:8000/api/v1/system/info
```

测试：

```bash
pytest
```
