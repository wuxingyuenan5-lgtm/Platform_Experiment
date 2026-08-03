# Platform Identity低风险模块化计划

状态：**I2.1 Session Presenter已完成，等待清理HEAD完整矩阵收口**  
关联Issue：#136  
关联Draft PR：#139  
活动分支：`refactor/issue-136-platform-0-9-2-system-optimization`  
开发与验收版本：Platform `0.9.2`

## 冻结合同

Identity优化不得改变：

- Browser Session与API-Key隔离；
- CSRF、Origin、Cookie、安全响应头与缓存策略；
- 注册、首位CEO、登录锁定、Dummy Hash、密码重哈希、Session创建与登出；
- 角色分级、目标范围、会员隔离、最后活跃CEO保护；
- 近期再认证、行版本并发、事务原子性、审计事件和会话撤销；
- 密码重置票据、生命周期状态、公开API与Pydantic别名。

禁止引入新的认证框架、跨域状态容器或微服务；禁止把授权判断、令牌/CSRF、事务、所有权校验、撤销或审计副作用移入Presenter。

## I0 Identity依赖审计：完成

- [x] 审计`user_service.py`、`user_admin_service.py`、路由、Repository、Schema与真实测试清单；
- [x] 冻结注册/首位CEO、登录/Session、自助资料、管理员生命周期四类用例；
- [x] 登录链、资料更新链和管理员写链均为高风险，默认保持原位；
- [x] 仅选择无状态、无授权、无写库副作用的响应映射与格式化职责。

## I1 管理员响应Presenter：完成

- [x] 新增`user_admin_presenter.py`并迁移联系方式/实名脱敏、摘要、详情和审计响应映射；
- [x] 保持角色、生命周期、时间戳、权限排序、Pydantic别名与敏感字段范围；
- [x] Service只保留三个Presenter别名；
- [x] 最后CEO、近期再认证、目标范围、角色授权、`BEGIN IMMEDIATE`、行版本及会话撤销留在Service；
- [x] Presenter单元测试、永久架构边界和Pyright覆盖；
- [x] 一次性写权限Workflow已删除；
- [x] 完整矩阵通过：
  - Platform CI `30618589774`
  - Directory `30618590286`
  - User E2E `30618589131`
  - Hedge E2E `30618589207`
  - Visual `30618589846`
  - Provider Smoke `30618589505`
  - Secret `30618589425`
  - Version `30618589491`
  - Audit `30618590479`
- [x] 视觉Artifact `8788488746`，SHA-256 `1b83e559921514215aeadf5656d3bf7e0b58184e2c91b58386447f7d4df9f6f4`。

## I2.1 Session Presenter：代码完成，最终矩阵待收口

- [x] 新增`platform-api/app/user_session_presenter.py`；
- [x] 迁移IPv4/IPv6脱敏、User-Agent空白压缩/160字符截断及Session列表响应映射；
- [x] 登录和`issue_browser_session`继续复用同一User-Agent摘要规则；
- [x] 保持当前Session标记、时间戳、IP摘要、UA摘要与Pydantic别名；
- [x] `get_session_list`只委托Presenter；
- [x] Session创建、令牌/CSRF哈希、CSRF轮换、所有权校验、当前Session保护、撤销与审计全部留在Service/Repository；
- [x] 新增Presenter单元测试与永久架构边界测试；
- [x] Presenter纳入Pyright；
- [x] 目标Ruff、Pyright、浏览器流程、Session基础、登出与认证保证测试通过；
- [x] 一次性写权限Workflow已删除；
- [ ] 以本文档同步后的清理HEAD完成九项完整质量矩阵。

## Identity收口边界

I2.1矩阵通过后停止继续拆分Identity：

- 登录链同时承担锁定、Dummy Hash、重哈希、Session创建和审计；
- 自助资料更新包含近期再认证、行版本、唯一性与审计；
- 自助撤销包含所有权、当前Session保护和审计；
- 管理员写链包含最后CEO、授权、事务和会话撤销。

上述职责继续保持原位。下一阶段转入Portfolio只读审计。

每个切口必须通过Platform API、Research Provider、前端质量、两套浏览器、56张视觉基线及四项治理门禁。Draft PR始终保持Open、Draft、Unmerged；不得修改或合并`main`。
