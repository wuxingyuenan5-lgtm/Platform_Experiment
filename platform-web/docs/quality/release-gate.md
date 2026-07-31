# Platform V6 最小发布门槛

状态：`active`  
适用基线：`main / Platform V6`  
总体计划：`../../../docs/planning/V6-交易安全加固实施计划.md`  
当前阶段：`../../../docs/planning/V6-Production-Gate-密钥托管与脱敏.md`

## 1. 原则

必须区分：

- 工程验收：代码、离线 Provider Tests、金样本、CI 和 Markdown。
- 运营验收：受控主机配置、真实账户只读、双人批准、最小仓位、轮换、Kill Switch 和多个清洁 EOD。

工程验收通过不自动开启 Live Write，不允许提高资金、仓位、品种或自动化频率。

## 2. 自动检查

```bash
python scripts/scan-secrets.py

cd platform-backend
python -m ruff check app tests
python -m pytest

cd ../execution-runtime
python -m ruff check app tests
python -m pytest

cd ../platform-web
pnpm type:check
pnpm build
```

GitHub Actions 必须覆盖 Repository Safety、Platform Backend、Execution Runtime 和 Frontend。任一 Job 失败或未执行，不得合并。

## 3. Authentication 与 RBAC

- Live 环境只允许 Production Authentication。
- 匿名、无效 Credential、停用 Credential 和 development identity 全部拒绝。
- Role 和 Permission 默认拒绝。
- actor/reviewer 等字段必须匹配认证 Principal。
- Applicant 与 Approver 必须不同。
- admin 不能自批。
- Audit 和 Credential Metadata 不是普通 viewer 权限。

## 4. LiveTradingSession

会话必须固定：

- StrategyInstance、Account。
- Symbol、Side、Order Type。
- Starts At、Ends At。
- Max Order Notional、Max Daily Notional。
- Applicant、Approver、Reason、Evidence Reference、Payload Hash。

必须阻断：

- Kill Switch 开启。
- Open/Accepted Difference。
- 不合格 EOD。
- 重叠 Approved Session。
- 超过平台绝对限额。
- 无唯一有效会话。
- 并发命令合计穿透日限额。

Session Claim 必须在 Order Insert 和 Runtime Call 之前完成，并使用 Command ID 幂等。

## 5. Secret Reference

正式格式：

```text
secret://environment/<name>
secret://windows-credential-manager/<name>
```

- 新配置不得使用隐式 Provider。
- Unknown Provider 不得回退 Environment。
- Secret Name 为空、非法路径和字段缺失全部拒绝。
- Windows Provider 在非 Windows 或依赖缺失时 fail-closed。
- Legacy Reference 必须明确标记为迁移兼容。

## 6. Provider Inspection 与 Resolution

Inspection 只允许返回：

- Reference。
- Provider。
- Secret Name。
- Version。
- configured。
- availableFields。
- missingFields。
- legacyReference。
- Environment Provider 的 envPrefix。

不得返回值、长度、摘要、前后缀或其他可推断信息。

Resolution：

- 只允许 Runtime Gateway 内部调用。
- Required Fields 必须由 Adapter 明确声明。
- 返回值不得进入 API、日志、异常、AuditEvent、数据库或测试快照。
- Provider 不可用时不得自动回退。

## 7. Rotation Metadata

```http
POST /api/v1/security/credential-rotations
GET  /api/v1/security/credential-rotations
```

必须确认：

- POST 需要 admin。
- GET 需要 audit 权限。
- Actor 来自认证 Principal。
- Provider 与 Reference 一致。
- `rotatedAt` 含时区。
- 同一 Idempotency Key 或同一 Reference/Provider/Version 只允许相同载荷重放。
- 载荷冲突返回 409。
- 表结构、响应和 AuditEvent 不包含旧值或新值。
- Rotation Record 不等于外部 Provider 写入成功；运营步骤必须单独完成。

## 8. Redaction

Backend 与 Runtime 必须覆盖：

- 嵌套 dict、list、tuple、set。
- authorization、token、api key、api secret、secret、password、passphrase、private key。
- Bearer Token。
- 私钥块。
- URL 中的认证信息。
- 受控字段赋值。
- Exception Message。

统一替换为 `[REDACTED]`。非敏感业务上下文应保留，便于对账和排障。

## 9. Repository Secret Scan

必须阻断：

- 私钥块。
- 常见平台 Token。
- 高熵明文 Secret Assignment。
- 未审核 tracked `.env*`。

审核过的 Vite 环境文件只允许公开 `VITE_*` 配置，但仍接受已知 Token 和高熵扫描。Scanner 只能跳过自身 Regex 源文件，不能整体排除源码、测试或文档。

## 10. 交易与 Runtime

- 正式写入口只有 TradeCommand 和 ExecutionBatch。
- Platform 与 Runtime Live Gate 独立且默认关闭。
- Runtime 在 Gateway 副作用前原子抢占 Command。
- Account、Strategy、Symbol allowlist 和单笔/单日限额必须全部满足。
- Query 与 Command 分离。
- ACK 不等于 Fill。
- `result_unknown` 不得直接重下。
- Unknown Provider 或 Provider Failure 不得回退 Fake Gateway。
- 每条 Batch Leg 必须通过 TradeCommand 与 Live Session Claim。

## 11. Venue 与账务

- Bybit、MT5 查询失败不得表示为空仓或零余额。
- 外部 Order、Fill/Deal、Position、Balance、Funding、Swap、Fee 使用稳定身份。
- 重复导入不得重复记账。
- 外部与本地冲突形成 Difference。
- Open 与 Accepted Difference 均阻断批准和扩大实盘。
- FinancialFact 不可变。
- Formal Position/PnL 可以重建。
- NAV 使用统一估值时点并显式报告缺失账户。

## 12. EOD

- Business Date、Timezone、Valuation Time、Due At 明确。
- 覆盖业务日期订单和历史未终结订单。
- 覆盖 Order、Fill/Deal、Position、Balance、Funding、Swap、Fee、Formal PnL/NAV。
- 外部错误进入 errors，不生成虚假 complete。
- Skipped Event、Missing Account、Incomplete PnL、Open/Accepted Difference 阻断 Scale Gate。
- Review 不自动提高限额或开启 Live Write。

## 13. 文档一致性

变更身份、权限、会话、Provider、Rotation、Redaction、交易、风险、账务、API 或部署时，必须同步：

- 实施计划。
- 技术合同。
- API Spec。
- README。
- START-HERE。
- Release Gate。
- Changelog。
- Issue 与 PR。

## 14. 阻断条件

任一存在，不得合并或开启 Live Write：

- CI 或 Secret Scan 失败/未执行。
- Live 匿名、development auth 或权限绕过。
- Applicant 自批。
- 无会话或会话超范围下单。
- 并发额度穿透。
- Unknown Provider 自动回退。
- Inspection/Rotation/Audit/Exception 泄漏凭证内容。
- Rotation 表保存旧值或新值。
- Query Failure 被解释为空仓、零余额或 clean EOD。
- `result_unknown` 被重下。
- Difference 被无痕覆盖。
- active Markdown 与实现不一致。

## 15. 运营验收

- 受控 Windows 主机建立 Credential Manager 项目。
- Provider Inspection 只显示元数据。
- Bybit/MT5 只读连接通过。
- 完成一次 Version Rotation 和 Runtime Restart。
- trader 申请、独立 risk_officer 批准最小仓位窗口。
- 完成最小仓位、撤单、查询、事实导入和 EOD。
- 测试结束后撤销 Session、清空临时 allowlist/limit、关闭 Runtime Write Gate。
- Production Gate 5D 完成前不扩大实盘。
