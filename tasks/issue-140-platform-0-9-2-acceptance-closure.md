# Platform 0.9.2 验收整改收口任务

Workstream: critical  
Branch: `fix/platform-0-9-2-acceptance-closure`  
整改起点：`cf44c8cca52576acc4e4070a98dcf112ebeec31c`  
冻结产品基准：`8114fce45e46e7920f316f49d03db12dc424acf1`  
目标版本：`0.9.2`

## 执行边界

- 严格按 Phase 0—Phase 6 顺序执行；每阶段一个可独立审查的 Commit。
- 不直接修改或合并 `main`，不合并 PR #139。
- 不机械替换 `rta`、`risk` 或“私募”。
- 外部生产证据完成前，不删除 `projects/risk-control`、`deploy/`、`platform-web/.gitlab-ci.yml` 或 `.env.production` 中的 Legacy 路由。
- 不引入微服务、消息队列、新数据库、服务网格、Kubernetes、Event Sourcing 或全仓 ORM 重写。
- Browser Session/API-Key、CSRF/Origin、角色与会员隔离、交易、风险、Financial Fact、PnL/NAV、正式会计、对账、不可变迁移、Kill Switch、双人审批、Live Write、幂等性、Market/FOK/PostOnly/TP-SL、Result Unknown、EOD/LKG 与 Runtime 合同均为受保护语义。

## Phase 0 — 冻结证据和整改基线

### 当前可复核基线

- `cf44...` 对应的 Platform CI、Directory、Version、Secret、User E2E、Audit、Visual、Hedge E2E、Provider Smoke 共九个工作流已通过。
- Platform API、Execution Runtime、前端 Lint、no-new-debt、两套分区 Type Check、生产 Build、User E2E、Hedge E2E 与 56 页候选截图在该提交已通过。
- 现有视觉 Artifact 仅包含候选版本截图，未检出冻结基准并逐页比较，因此不能证明展示未变化。
- 冻结基准全仓估算文本 Token：`2,014,104`；整改起点：`2,077,915`，增加 `63,811`（约 `3.2%`）。

### 七类 Context Pack Before

| Context Pack | 文件数/行数 | Before Token | 上限 | 状态 |
|---|---:|---:|---:|---|
| `hedge-style` | 现有生成结果 | 33,991 | <8,000 | 未达标 |
| `research-field` | 现有生成结果 | 17,784 | <14,000 | 未达标 |
| `identity-permission` | 现有生成结果 | 13,255 | <10,000 | 未达标 |
| `member-contract` | 现有生成结果 | 13,915 | <10,000 | 未达标 |
| `trading-display` | 现有生成结果 | 15,804 | <12,000 | 未达标 |
| `research-provider` | 现有生成结果 | 14,196 | <12,000 | 未达标 |
| `user-e2e` | 现有生成结果 | 11,748 | <12,000 | 达标 |

### 已确认阻断项

1. 当前有效入口仍存在旧版本、旧目录与模板残留名称。
2. Platform API 运行时版本仍为 `0.6.0`；Execution Runtime 仍为 `0.5.0`。
3. 两处 Live 日限额仍使用 SQLite `SUM(CAST(notional AS REAL))`。
4. Python 类型检查和前端 Full Type Check 未覆盖最终候选的全部要求。
5. `platform-web/apps/test-server` 仍属于 pnpm workspace，删除前必须完成引用、锁文件、构建与 E2E 证据。
6. Windows、旧服务器、GitLab Runner、MySQL、TLS 与真实 Venue/Broker 验收仍属于外部待办，不能由 CI 代替。

### Phase 0 结论

- 可重现证据：采用 `cf44...` 已完成的九项 CI 与其 Artifact 作为整改起点冻结证据。
- 当前结论：不通过最终验收；允许进入最小必要整改。
- 明确未改变：前端、权限、交易、会计与 Runtime 语义均未改动。
