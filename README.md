# Variable-Global 本地工作台

这是当前正在开发的交易研究与策略平台工作区。核心目标不是“堆功能”，而是把策略研究、账户资金、执行链路、风控状态和投研看板组织成一个可以长期迭代的本地平台。

## 当前权威基线

- 正式分支：`main`
- V6 基线提交：`76effbff6391533db7b9954965aaf1b09051081f`
- 当前工程重点：交易安全、可靠执行、账务正确性
- 总跟踪：GitHub Issue `#2`
- 实施计划：`docs/planning/V6-交易安全加固实施计划.md`

在交易安全计划完成前，系统只允许 Simulation / Fake Gateway，不开放真实资金 Live。

## 先看这里

| 你要做什么 | 入口 |
|---|---|
| 看当前工程计划 | `docs/planning/V6-交易安全加固实施计划.md` |
| 改前端界面 | `admin-risk/src/views` |
| 看策略平台页面 | `http://127.0.0.1:5173/index.html#/strategy/platform` |
| 看策略管理页面 | `http://127.0.0.1:5173/index.html#/strategy/management` |
| 改平台后端 | `platform-backend/app` |
| 改执行网关 | `execution-runtime/app` |
| 查产品/架构文档 | `docs/README.md` 和 `admin-risk/docs` |
| 查外部参考代码 | `C:\Users\jiuxi\Desktop\codex\平台设计其他辅助内容\平台移动文件夹，例如参考代码等\参考代码` |
| 放临时输出 | `outputs/temp` |
| 查工作区降噪规则 | `docs/operations/WORKSPACE_HYGIENE.md` |

## 当前运行口径

- 前端主入口：`5173`
- 前端标准地址：`http://127.0.0.1:5173/index.html#/strategy/platform`
- 后端主入口：`http://127.0.0.1:8000/api/v1`
- 后端健康检查：`http://127.0.0.1:8000/health`
- Runtime Gateway：`http://127.0.0.1:8100`

`4373` 只是 Vite 默认配置启动出来的另一个前端实例，后续不作为主工作入口。

## 根目录分工

| 目录 | 定位 | 当前策略 |
|---|---|---|
| `admin-risk/` | 正式前端工程 | 保持原位，避免破坏 pnpm/Vite 路径 |
| `platform-backend/` | 平台后端 | 保持原位，继续作为 `/api/v1` 来源 |
| `execution-runtime/` | 执行隔离网关 | 保持独立进程，优先治理幂等与恢复 |
| `docs/` | 根级导航和权威入口 | 只做索引、执行计划和总口径 |
| `admin-risk/docs/` | 现有详细文档库 | 暂时保留，逐步抽取权威内容 |
| `references/` | 项目内参考索引、SQL 资料、小型研究材料 | 不放大型外部仓库 |
| `tasks/` | 任务拆分与验收 | 后续每个改动单独建任务 |
| `outputs/` | 生成物、导出物、临时预览 | 不放源码 |
| `deploy/` | 部署材料 | 暂不移动 |
| `projects/` | 历史/并行服务实验 | 暂不移动 |
| `scripts/` | 根脚本 | 暂不移动 |

## 常用命令

前端：

```powershell
cd C:\Users\jiuxi\Desktop\codex\平台后端测试\admin-risk
$env:VITE_PLATFORM_API_BASE_URL="http://127.0.0.1:8000/api/v1"
pnpm vite --host 127.0.0.1 --port 5173
```

平台后端：

```powershell
cd C:\Users\jiuxi\Desktop\codex\平台后端测试\platform-backend
python -m uvicorn app.main:app --reload --port 8000
```

执行网关：

```powershell
cd C:\Users\jiuxi\Desktop\codex\平台后端测试\execution-runtime
python -m uvicorn app.main:app --reload --port 8100
```

## 稳定提交门槛

提交前至少执行：

```powershell
cd admin-risk
pnpm type:check
pnpm build

cd ..\platform-backend
python -m ruff check app tests
python -m pytest

cd ..\execution-runtime
python -m ruff check app tests
python -m pytest
```

详细要求见 `admin-risk/docs/quality/release-gate.md`。

## 整理原则

1. 先整理入口和归属，再移动运行目录。
2. 运行中的工程目录不轻易改名。
3. 参考代码、截图、SQL、导出物不能和正式源码混放。
4. 产品页面不放后端联调面板、测试按钮、实现解释。
5. 交易、权限、数据库、部署相关改动单独审批。
6. 未知账户、标的、状态或执行结果必须 fail-closed，不能默认放行。
7. 每批工程改动同步更新计划、测试、Release Gate 和 Changelog。

## Codex 降噪

根目录同时维护 `.gitignore` 和 `.ignore`：

- `.gitignore` 控制 Git 跟踪范围。
- `.ignore` 控制 `rg` / Codex 后续搜索范围。
- `node_modules/`、`.venv/`、`dist/`、`outputs/` 默认不进入扫描主路径。
- 大型外部参考代码已移出项目根目录，位置见上方入口表。
