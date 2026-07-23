# Variable-Global 本地工作台

这是面向内部投研、策略执行、风险控制和账务核对的交易平台工程。

当前目标：建立可靠的交易基础设施，包括执行安全、风险控制、正式账务和生产门禁，再扩展策略与产品能力。

## 快速入口

| 主题 | 文档 |
|---|---|
| 总体路线 | `docs/planning/V6-交易安全加固实施计划.md` |
| 系统架构 | `docs/architecture/` |
| Codex 工作方式 | `docs/codex/` |
| API 规范 | `docs/technical/API_SPEC.md` |
| 正式账务 | `docs/technical/FINANCIAL_FACTS.md` |
| 实盘运营 | `docs/operations/` |
| 发布门槛 | `admin-risk/docs/quality/release-gate.md` |
| 前端入口 | `admin-risk/docs/START-HERE.md` |

## 当前工程状态

- Phase 1–4D：已完成。
- Production Gate 持续建设中。
- 实盘方向优先采用真实账户、小资金、最小仓位验收。
- Platform 与 Runtime Live Write 默认关闭。

## 服务入口

| 服务 | 地址 | 职责 |
|---|---|---|
| Frontend | `http://127.0.0.1:5173` | 产品交互 |
| Platform Backend | `http://127.0.0.1:8000` | 业务、权限、账务、风险 |
| Execution Runtime | `http://127.0.0.1:8100` | 执行、Gateway、外部副作用 |

## 默认模式

```text
TradingMode=simulation
Gateway=fake
Platform Live Write=false
Runtime Live Write=false
```

## 目录结构

```text
admin-risk/          前端应用
platform-backend/    平台后端
execution-runtime/   执行网关
docs/                架构、设计、运营和计划文档
tests/               测试
tasks/               工作任务
outputs/             临时产物
```

## 开发规则

- 永久规则见 `AGENTS.md`。
- 架构决策见 `docs/architecture/` 和 `docs/decisions/`。
- 具体模块修改只加载对应模块文档，不默认扫描整个仓库。
- 不提交密钥、Token 或 `.env`。
- 未通过测试和 CI 的改动不得进入正式分支。

## 常用命令

前端：

```powershell
cd admin-risk
pnpm type:check
pnpm build
```

后端：

```powershell
cd platform-backend
python -m pytest
```

Runtime：

```powershell
cd execution-runtime
python -m pytest
```
