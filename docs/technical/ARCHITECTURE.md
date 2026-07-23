# 当前架构

## 一句话结构

前端 `admin-risk` 负责产品界面，`platform-backend` 负责平台业务状态和 `/api/v1`，`execution-runtime` 负责隔离外部交易接口。三者暂时保持并列目录，避免为了“好看”破坏本地运行链路。

## 模块边界

| 模块 | 职责 | 不应承担 |
|---|---|---|
| `admin-risk` | 页面、路由、交互、数据展示、前端 mock/适配 | 真实交易编排、密钥处理 |
| `platform-backend` | 策略实例、账户、标的、订单、批次、审计、平台 API | 直接连接交易所或 MT5 |
| `execution-runtime` | 外部交易适配、执行隔离、密钥解析、Runtime 日志 | 产品页面状态管理 |
| `deploy` | 环境配置和部署材料 | 本地产品逻辑 |
| `references` | 参考代码和外部材料 | 被运行时代码直接依赖 |

## 暂不移动运行目录的原因

- `admin-risk` 有 pnpm workspace、Vite、脚本和大量相对路径。
- `platform-backend` 有 SQLite 相对路径和测试路径。
- `execution-runtime` 有独立虚拟环境和 uvicorn 启动方式。
- 当前目标是先让项目可读、可维护，再考虑物理目录迁移。
