# 人工阅读入口

状态：`active`  
产品基线：Platform V6  
适用分支：`main`  
当前实施：Production Gate 5C——凭证 Provider、轮换元数据与敏感信息脱敏  
跟踪：Issue `#24`、PR `#25`

## 1. 优先阅读

1. `../../docs/planning/V6-交易安全加固实施计划.md`
2. `../../docs/planning/V6-Production-Gate-密钥托管与脱敏.md`
3. `../../docs/technical/SECRET_PROVIDER_AND_REDACTION.md`
4. `../../docs/technical/AUTH_RBAC_LIVE_SESSIONS.md`
5. `../../docs/operations/V6-小资金实盘验收手册.md`
6. `quality/release-gate.md`

## 2. 当前状态

```text
Phase 1–3：交易安全、恢复与正式账务，已完成
+
Phase 4A–4D：执行风险、Venue Query、Live Adapter 与 EOD，已完成工程验收
+
Production Gate 5A/5B：认证、RBAC、双人 LiveTradingSession，已完成
+
Production Gate 5C：Provider、Rotation Metadata、Redaction，正在验收
+
Production Gate 5D：监控、告警、调度、备份与恢复，待实施
```

真实账户验收采用小资金和最小允许仓位。Platform 与 Runtime 写入开关默认关闭；生产门禁和连续清洁 EOD 未完成前，不得扩大实盘。

## 3. 身份与会话底线

- Live 环境只允许生产认证。
- 最小角色：viewer、researcher、trader、risk_officer、operations、admin。
- 权限默认拒绝。
- 操作人来自认证上下文。
- Applicant 与 Approver 必须不同。
- Live Command 必须认领唯一有效的 `LiveTradingSession`。
- Kill Switch、历史差异、不合格 EOD、超限和会话重叠阻断批准。

## 4. Provider 底线

正式引用：

```text
secret://environment/<name>
secret://windows-credential-manager/<name>
```

- 旧格式只做迁移兼容。
- 未知 Provider 不允许回退。
- Windows Provider 在不支持的平台或依赖缺失时 fail-closed。
- Inspection 只返回 Provider、Version、字段存在性和缺失字段。
- Resolve 仅在 Runtime Gateway 内部调用。

## 5. Rotation 与脱敏

```http
POST /api/v1/security/credential-rotations
GET  /api/v1/security/credential-rotations
```

Rotation 只记录 Reference、Provider、Version、时间、操作人和原因，不保存凭证内容。

Backend 与 Runtime Redactor 覆盖嵌套结构、授权头、令牌、口令、私钥块、URL 中的认证信息和异常文本，统一替换为 `[REDACTED]`。

## 6. 交易与运营底线

- 正式写入口只有 TradeCommand 和 ExecutionBatch。
- Platform 与 Runtime Live Gate 独立且默认关闭。
- Account、Strategy、Symbol allowlist 和单笔/单日限额同时生效。
- Query 与 Command 分离；ACK 不等于 Fill。
- `result_unknown` 只查询恢复，不重下。
- 外部差异形成 Reconciliation Difference。
- 每个真实测试日必须形成 EOD Report。
- 测试结束后撤销 Session，并复位临时 allowlist、limit 和 Runtime Write Gate。

## 7. 当前工程优先级

| 顺序 | 主题 | 状态 |
|---|---|---|
| 1 | Environment / Windows Provider | 已实现，PR #25 验收中 |
| 2 | Rotation Metadata 与 RBAC | 已实现，PR #25 验收中 |
| 3 | Backend / Runtime Redaction | 已实现，PR #25 验收中 |
| 4 | Repository Scan 与全量 CI | 已纳入 |
| 5 | 监控、告警、调度、备份、恢复 | Production Gate 5D |
| 6 | 真实账户小资金运营验收 | 待受控主机人工执行 |
| 7 | 新策略和金融AI | 暂缓 |

## 8. 文档治理

每个阶段同步 Issue、分支、PR、代码、测试、CI、实施计划、技术合同、API Spec、Release Gate、README、START-HERE 和 Changelog。敏感信息不得进入工程留痕材料。