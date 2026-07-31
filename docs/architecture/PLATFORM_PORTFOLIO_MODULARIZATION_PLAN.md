# Platform Portfolio与正式财务低风险模块化计划

状态：**P1 会员持仓纯估值层已实现，完整质量矩阵验证中**  
关联Issue：#136  
关联Draft PR：#139  
活动分支：`refactor/issue-136-platform-0-9-2-system-optimization`  
开发与验收版本：Platform `0.9.2`

## 冻结合同

Portfolio与正式财务优化不得改变：

- 会员只能读取自身持仓，管理员读取/写入权限与Human Session保证；
- Browser Session/API-Key隔离、CSRF、近期再认证和审计；
- `BEGIN IMMEDIATE`、乐观锁、写入与审计原子回滚；
- Decimal普通字符串、精度、非负/有限值和规范化输出；
- NAV缺失/陈旧/可用状态、估值时间、币种一致性和未来时间拒绝；
- market value、cumulative return、return rate及投入为0时空收益率；
- Financial Fact、Position Math、Formal Projection、PnL/NAV和Data Quality语义；
- 不可变迁移与Platform API / Execution Runtime边界。

禁止引入浮点数、重复财务计算、隐式0值、跨域状态容器或新的财务微服务。

## P0 依赖审计：完成

- [x] 会员持仓已具备Routes / Service / Repository / Schemas / Decimal五层边界；
- [x] Holding模块禁止依赖Trading Runtime和Formal Projection；
- [x] Financial Fact Normalization、Position Math和Projection已分层；
- [x] 持仓写入、权限、近期再认证、事务、审计和Repository保持原位；
- [x] 识别唯一低风险切口：已加载Fund/Holding/NAV记录的纯估值与响应构建。

## P1 会员持仓纯估值层

### 允许范围

1. 建立无数据库、无HTTP、无权限、无审计副作用的估值模块；
2. 保持全部Decimal、NAV状态、币种、时间戳和响应别名；
3. Service继续加载Fund/NAV并把估值错误映射为原`MemberHoldingServiceError`；
4. 永久架构测试冻结模块依赖与Service职责；
5. Target tests、全后端测试和九项完整矩阵全部通过；
6. 一次性写权限工具在验证后删除。

### 当前实现

- [x] 新增`platform-api/app/member_holding_valuation.py`，只接收已加载的Fund、Holding、NAV与显式时间/陈旧阈值；
- [x] 保留普通Decimal字符串、market value、cumulative return、return rate与零投入空收益率；
- [x] 保留`available`、`stale`、`unavailable`以及36小时和未来5分钟边界；
- [x] 保留基金基础币种、NAV币种一致性和全部UTC时区归一化；
- [x] `member_holding_service.py`继续拥有数据库读取、权限、近期再认证、事务、审计和服务错误映射；
- [x] 新增完整响应Golden、Decimal/时区/临界值测试和永久纯度架构测试；
- [x] 将估值Owner登记到`docs/architecture/OWNERSHIP.md`并纳入Pyright；
- [x] 删除一次性写权限Workflow和迁移脚本；
- [ ] 完整质量矩阵通过并将运行证据同步到Issue #136和Draft PR #139。

## P1停止条件

出现以下任一情况必须停止并回滚本切口：

- API字段、别名、错误码或Decimal输出发生变化；
- NAV状态或时间边界发生变化；
- Service失去权限、事务、审计或Repository编排职责；
- 估值模块依赖配置、数据库、HTTP、认证或正式投影；
- Browser E2E、视觉基线、Provider Smoke或任一安全门禁失败。

## 后续边界

P1通过后只读复核Fund catalog与NAV mutation响应。Financial Fact、Formal Projection和Position Math默认不再拆分；没有明确无状态切口时结束Portfolio后端代码修改。

Draft PR始终保持Open、Draft、Unmerged；不得修改或合并`main`。
