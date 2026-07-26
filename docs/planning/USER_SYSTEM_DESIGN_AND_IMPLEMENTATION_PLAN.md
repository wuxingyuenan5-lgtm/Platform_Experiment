# 用户系统设计索引与决策摘要

状态：`self-reviewed baseline / implementation not started`  
适用版本：`Platform Experiment 0.9.0`  
Issue：`#117`  
任务包：`tasks/issue-117-user-system.md`  
分支：`feature/issue-117-user-system`  
基线提交：`71603bcc6807284ef3a6da26ad3f43c541bc99c2`

## 1. 文档结构

原单一长文档已经拆分为三个权威层次，避免需求、架构和执行状态互相覆盖：

1. [用户系统产品需求与验收标准](USER_SYSTEM_REQUIREMENTS.md)
   - 定义角色、使用场景、功能、字段、权限、非功能要求和验收标准；
   - 回答“必须实现什么”。

2. [用户系统技术架构](../technical/USER_SYSTEM_TECHNICAL_ARCHITECTURE.md)
   - 定义认证保障等级、Principal、Session、CSRF、数据模型、API、前后端边界、迁移和安全控制；
   - 回答“系统如何实现并保持安全”。

3. [用户系统执行计划](USER_SYSTEM_EXECUTION_PLAN.md)
   - 定义决策门、实施批次、文件范围、直接测试、CI、回滚、停止条件和完成定义；
   - 回答“按什么顺序执行和验证”。

本文档只保留索引、关键结论和设计变化，不再重复三份正文。

## 2. 已确认的核心决策

### 2.1 单一身份权威

`platform-backend` 成为浏览器用户、密码、Session、业务角色、会员持仓和用户审计的唯一权威。旧 Go `auth-service` 暂不删除，但停止扩展且不再承载新用户系统。

### 2.2 两种凭证，一个 Principal 边界

- 浏览器用户：同源 HttpOnly Session；
- 自动化和 Live 客户端：现有 Bearer API Key；
- 两者生成统一 Principal，但使用不同认证保障等级；
- 同一请求同时携带 Cookie 和 Bearer 时拒绝歧义。

### 2.3 客户身份域 Session-only

用户、个人资料、Session、密码重置和会员持仓管理接口只接受人类 Session。API-Key `admin` 的 wildcard 不自动等同业务 CEO，不能自动读取或修改客户身份数据。

### 2.4 Live 安全不变

第一阶段浏览器 Session 不替代 API Key 调用真实交易或核心 Live 写入路由。现有 LiveTradingSession、Kill Switch、对账、绝对限额、Platform Live Write 和 Runtime Live Write 全部保留。

### 2.5 四类固定业务角色

```text
ceo
tech_lead
employee
member
```

第一阶段采用固定角色到权限点映射，不开发可视化权限编辑器或逐用户权限覆盖。

### 2.6 公开注册边界

公开注册只允许申请会员或员工。CEO 和技术负责人必须由现有 CEO 创建。技术负责人只能审批或管理会员和员工。

### 2.7 服务端 Session

浏览器不持久化长期认证 Token。Session 支持绝对/空闲有效期、CSRF、近期再认证、设备管理、最大并发数和 `auth_version` 即时失效。

### 2.8 密码重置

管理员不设置或查看临时密码。后端签发一次性、短时有效的重置凭证，只保存哈希并只返回一次。

### 2.9 账号状态与安全锁定分离

账号生命周期：

```text
pending | active | disabled | rejected
```

临时登录锁定使用：

```text
failed_login_count
locked_until
```

不再将 `locked` 作为生命周期状态。

### 2.10 会员持仓权威

会员持仓是客户报告读模型，不是申购、赎回、清算或正式会计账本。后端使用 Decimal，数据库/API 使用规范化十进制字符串；策略 NAV 不能冒充基金单位净值。

### 2.11 第一阶段不硬删除用户

用户只通过审核、拒绝、启用和停用管理。硬删除会破坏审计和引用连续性，留待未来独立设计。

## 3. 自审后主要优化

与初版相比，本次自审完成以下修正：

1. 将 1770 行混合文档拆为需求、架构、执行三层；
2. 增加可追踪需求编号 `USR-*`，可直接映射测试和批次；
3. 明确人类 Session、平台读取、模拟写入和 Live 写入的认证保障等级；
4. 解决现有“Live 全局只允许 API Key”与生产浏览器登录之间的架构冲突，同时不放宽 Live 路由；
5. 明确 API-Key `admin` 不得管理人类账号和客户持仓；
6. 增加 Cookie+Bearer 歧义拒绝；
7. 增加近期再认证、Session 空闲过期、最大 Session 数和活动时间写入节流；
8. 将临时锁定从用户生命周期状态中拆出；
9. 用一次性密码重置凭证替代管理员输入临时密码；
10. 删除 `/auth/me` 返回菜单树的重复设计，改为后端返回权限、前端单一注册表生成菜单和路由；
11. 增加 `row_version/expectedVersion` 乐观并发控制；
12. 为持仓增加 `source/as_of/updated_by/row_version`，明确数据来源和时点；
13. 将审计字段并入 Migration 5，迁移计划从三项收敛为两项；
14. 明确第一阶段不提供用户 DELETE；
15. 增加旧真实用户、持仓来源和同源部署三个实施决策门；
16. 增加结构化错误码、429、no-store、Origin 和速率限制要求；
17. 增加 API-Key wildcard、IDOR、重置凭证并发、头像炸弹和最后 CEO 并发专项测试；
18. 明确浏览器真实交易认证属于后续独立 Critical Issue。

## 4. 不可改变的安全边界

本工作不得改变：

- Market、FOK、PostOnly、TP/SL 执行语义；
- 跨所价差定价、数量、顺序、补偿和对账；
- Platform/Runtime Live Write 默认关闭；
- LiveTradingSession、Kill Switch、绝对限额和对账阻断；
- 外部未知结果不盲目重试；
- Platform Backend 不引入 Venue SDK；
- 密码、Token、API Key、完整联系方式或真实持仓不得进入 Git、日志、测试或 Markdown。

## 5. 实施前仍需核实但不需立即提问的事项

以下内容已作为执行计划的决策门，不影响当前设计冻结：

1. 旧 Go/MySQL 是否有真实用户数据；
2. 第一批会员持仓的数据来源；
3. 正式环境是否继续保持前后端同源。

默认安全假设分别是：

```text
无旧真实用户
CEO 手工维护客户报告读模型
同源 /api/v1 反向代理
```

若实施证据与默认假设冲突，必须停止对应批次并重新评审，不能静默兼容。

## 6. 当前阶段

```text
Issue: created
Critical task packet: created
Branch: created from verified main
Requirements: self-reviewed
Technical architecture: self-reviewed
Execution plan: self-reviewed
Business code: not started
PR: not created
CI: not run on PR
```

下一步只有在明确开始代码实施后，才将任务包从 `review` 调整为 `active`，重新同步最新 `main`，核实三个决策门，并进入执行计划批次 1。
