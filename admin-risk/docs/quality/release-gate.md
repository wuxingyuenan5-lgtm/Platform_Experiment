# Platform V6 最小发布门槛

状态：`active`  
适用基线：`main / Platform V6`  
当前安全计划：`../../../docs/planning/V6-交易安全加固实施计划.md`

## 1. 目的

为以 Vibe Coding 为主的开发方式建立低成本、可重复、可审计的质量门槛。任何涉及交易、账户、持仓、PnL、Runtime、权限或部署的变更，不能只凭页面效果判断完成。

本规范是所有稳定提交和 Pull Request 的最低门槛，不等于完整生产测试体系。

## 2. 自动检查

### 2.1 前端

在 `admin-risk` 目录执行：

```bash
pnpm sync:trading-tools
pnpm type:check
pnpm build
```

要求：

- Markdown 交易工具源与生成数据一致。
- 本次范围无 TypeScript 类型错误。
- 模板、导入、路由、静态资源和正式打包无阻断错误。

### 2.2 Platform Backend

在 `platform-backend` 目录执行：

```bash
python -m ruff check app tests
python -m pytest
```

### 2.3 Execution Runtime

在 `execution-runtime` 目录执行：

```bash
python -m ruff check app tests
python -m pytest
```

### 2.4 GitHub Actions

- `main` push 必须触发 CI。
- 面向 `main` 的 Pull Request 必须触发 CI。
- 后端、Runtime、前端检查全部通过后才允许合并。
- 不允许通过强制更新 `main` 绕过失败检查。

## 3. 交易安全检查

涉及交易写路径时，必须确认：

- 未知账户 fail-closed。
- 未知标的或缺失 ContractSpecification fail-closed。
- 非 `active` 账户禁止下单。
- 数量满足最小下单量和数量步长。
- 限价满足价格步长。
- Live 账户受全局开关保护，默认关闭。
- 凭证只保存引用，不进入数据库、响应、日志和代码。
- Runtime 在任何外部副作用前原子抢占 command。
- 重复 command 不会产生第二次 Gateway 调用。
- `result_unknown` 不得被当作失败后直接重试。

任何一项无法确认，不能标记为可交易版本。

## 4. 金融正确性检查

涉及持仓、费用、PnL 或净值时，必须确认：

- 正式金额、价格和数量使用 Decimal。
- Money 带 Currency，Quantity 带 Unit。
- 合约乘数和数量换算来自 ContractSpecification。
- Stablecoin 不自动等同 USD。
- 缺失值不自动当零。
- 多账户净值按同一估值时点汇总。
- Funding、Swap、Fee、FX 与 Trading PnL 不混为一项。
- 外部订单、成交和持仓差异不会被无痕覆盖。

当前 V6 的 PnL/NAV 尚未完成上述全部口径，因此只能用于工程演示，不能作为正式投资账务。

## 5. 文档一致性

涉及以下变化时，必须同步更新 Markdown：

- 模块职责或架构边界。
- 策略能力和发布范围。
- 交易模式、Gateway 或账户安全规则。
- 状态机、幂等、恢复和对账语义。
- 损益、币种、单位、合约规格或风险口径。
- CI、部署和运行命令。

至少更新：

1. 对应实施计划。
2. `CHANGELOG.md`。
3. 本 Release Gate 或相关权威文档。
4. Pull Request 描述和验收结果。

普通样式微调和明确的无业务语义缺陷修复可以不更新需求文档，但仍应有清晰提交记录。

## 6. 变更范围检查

提交前确认：

- 没有意外修改一级架构和路由。
- 没有误改归档文档。
- 没有直接修改生成文件作为唯一修改。
- 没有因局部问题重写公共主题。
- 没有顺手删除未确认引用的文件。
- 没有将页面本地状态无理由放入全局 Store。
- 没有将真实凭证、`.env`、数据库文件或运行日志提交到仓库。
- 大规模自动生成变更有来源和验收说明。

## 7. 人工冒烟检查

执行 `smoke-checklist.md`，并额外检查：

- 后端和 Runtime 健康接口可用。
- Simulation/Fake Gateway 模式明确显示。
- 订单提交前能看到账户、标的和交易模式。
- 失败、处理中、结果未知和需要人工干预不会被展示为成功。
- 受影响页面无持续控制台错误。

本次未涉及的模块可以标记为“不适用”，但所有受影响路径必须检查。

## 8. 提交与 Pull Request 要求

一个稳定提交应当：

- 只表达一个清晰主题。
- 不混入无关重构。
- 提交信息说明改了什么。
- 代码、测试、文档在同一批次闭环。

推荐格式：

```text
feat: ...
fix: ...
test: ...
docs: ...
refactor: ...
chore: ...
```

Pull Request 必须写明：

- 基线 commit。
- 风险与影响范围。
- 自动检查结果。
- 人工验收结果。
- 回滚方式。
- 未完成和延期内容。

## 9. 阻断条件

存在以下任一情况时，不应合并或发布：

- 任一 CI Job 失败或未执行。
- 构建失败或本次范围类型检查失败。
- 未知账户、标的或状态可以继续下单。
- 相同 command 可能重复调用 Gateway。
- 主要路由无法进入。
- 策略或 section 切换失效。
- 控制台出现持续性运行错误。
- 关键页面内容为空或明显错位。
- active 文档与实现存在重大冲突。
- PnL/NAV 被误标为正式账务。
- Live 开关、凭证或回滚方案不清楚。

## 10. 后续升级

后续逐步加入：

- TradeCommand 唯一写入口。
- `result_unknown` 自动恢复测试。
- Alembic 或等价数据库迁移体系。
- Vitest 纯函数和适配器测试。
- Playwright 核心交易路径自动化。
- Bybit Demo 与 MT5 Demo 端到端测试。
- PnL、NAV 和日终对账金样本测试。
- 分支保护、CODEOWNERS 和审批规则。
