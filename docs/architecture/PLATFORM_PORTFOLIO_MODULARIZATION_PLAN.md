# Platform Portfolio与正式财务低风险模块化计划

状态：**Portfolio后端与前端公共展示治理已收口；下一阶段进入前端热点治理**  
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

## P1 会员持仓纯估值层：完成

- [x] 新增`platform-api/app/member_holding_valuation.py`，只接收已加载的Fund、Holding、NAV与显式时间/陈旧阈值；
- [x] 使用只读Protocol输入，估值Owner不依赖Repository记录类型或持久化模块；
- [x] 保留普通Decimal字符串、market value、cumulative return、return rate与零投入空收益率；
- [x] 保留`available`、`stale`、`unavailable`以及36小时和未来5分钟边界；
- [x] 保留基金基础币种、NAV币种一致性和全部UTC时区归一化；
- [x] `member_holding_service.py`继续拥有数据库读取、权限、近期再认证、事务、审计和服务错误映射；
- [x] 新增完整响应Golden、Decimal/时区/临界值测试和永久纯度架构测试；
- [x] 将估值Owner登记到`docs/architecture/OWNERSHIP.md`、纳入Pyright并加入文档一致性守卫；
- [x] 删除一次性写权限Workflow和迁移脚本。

### P1完整矩阵证据

验证HEAD：`1697345b59517d603a30377934271ba5946d4856`

- Platform CI：`30626771566`
- Platform Directory Invariants：`30626771569`
- Version Consistency：`30626771572`
- Secret Scan：`30626771577`
- User System Browser E2E：`30626771578`
- Platform 0.9.2 Baseline Audit：`30626771579`
- Platform Visual Baseline：`30626771581`
- Hedge Board Browser E2E：`30626771582`
- Research Provider Smoke：`30626771610`

视觉Artifact：`8791768494`  
SHA-256：`74df3b5503ed41204719acd1d06203fcc3fa3c9479a18972a544acc2a81a7a32`

## P2 Fund catalog与NAV mutation响应只读复核：完成

### 审计结论

- `_fund_response`是四字段的局部映射，已由基金目录和NAV写入响应两处复用，不存在跨模块重复实现；
- `get_fund_catalog`仅负责Repository读取与列表响应组装，职责边界清晰；
- NAV mutation响应依赖事务内可能更新后的Fund、持久化后的NAV以及规范化后的估值时间，紧邻写入与审计顺序更易审计；
- 两处响应构建均无独立政策、计算、错误合同或跨业务域复用需求；
- 新建Presenter只会增加模块、Protocol和调用跳转，不能减少权限、事务、Repository或审计认知范围。

### 决策

- [x] 不抽取Fund catalog Presenter；
- [x] 不抽取NAV mutation Presenter；
- [x] 不触碰Financial Fact、Formal Projection和Position Math；
- [x] Portfolio后端低风险模块化在P1后正式收口。

## P3 Portfolio前端与公共展示：完成

### 已修复问题

1. 管理员持仓页原有独立Decimal格式化和方向判断，`0.0`会被误判为正收益并显示绿色与正号；
2. 会员持仓页在部分基金缺失NAV时，会过滤缺失值后汇总其余基金，形成容易被误读为完整账户估值的部分总额。

### 已完成实现

- [x] 会员与管理员持仓页统一使用`platform-web/src/utils/decimalDisplay.ts`；
- [x] 任意形式的零值均保持中性，不显示正号或正收益颜色；
- [x] 同币种且全部持仓具备market value与cumulative return时，才显示账户总市值和总收益；
- [x] 任一持仓缺失估值时，总市值与总收益显示不可用，不将缺失值当0，也不静默展示部分合计；
- [x] 累计投入不依赖NAV，在同币种条件下仍可独立汇总；
- [x] 保持API、权限、DOM层级、CSS布局和用户操作流程；
- [x] 新增永久架构测试，冻结共享Decimal Owner和完整估值汇总规则。

### P3完整矩阵证据

验证HEAD：`e41267cc70b5e852b3069d71a6a8d7b1092127ad`

- Platform CI：`30628817214`
- Platform Directory Invariants：`30628817269`
- Version Consistency：`30628817272`
- Secret Scan：`30628817227`
- User System Browser E2E：`30628817208`
- Platform 0.9.2 Baseline Audit：`30628817219`
- Platform Visual Baseline：`30628817239`
- Hedge Board Browser E2E：`30628817237`
- Research Provider Smoke：`30628817247`

视觉Artifact：`8792572937`  
SHA-256：`5109b685a9b0e2b9926c364f6fbadf95aae5982a6a5d77b073e5c32a6f33a7de`

## Portfolio收口决策

- [x] Portfolio后端低风险模块化完成；
- [x] Portfolio前端Decimal与汇总口径治理完成；
- [x] 不新增跨域状态、浮点计算、正式财务替代逻辑或额外Presenter；
- [x] 后续仅在出现具体缺陷或新产品需求时重新打开Portfolio域。

## 下一门禁：前端热点治理

下一阶段回到证据确认的前端热点，优先审计`platform-web/src/views/hedgeBoard/index.vue`及可复用公共展示能力。仍采用一次一个视觉职责、完整质量矩阵和56页视觉验收，不进行页面重写或微前端化。

Draft PR始终保持Open、Draft、Unmerged；不得修改或合并`main`。
