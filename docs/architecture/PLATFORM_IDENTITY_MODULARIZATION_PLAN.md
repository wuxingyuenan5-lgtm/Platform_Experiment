# Platform Identity低风险模块化计划

状态：**I1 管理员响应Presenter已完成，等待清理HEAD完整矩阵收口**  
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

禁止引入新的认证框架、跨域状态容器或微服务；禁止把授权判断、事务或会话副作用移入Presenter。

## I0 Identity依赖审计：完成

- [x] 审计`user_service.py`、`user_admin_service.py`、路由、Repository、Schema与真实测试清单；
- [x] 冻结注册/首位CEO、登录/Session、自助资料、管理员生命周期四类用例；
- [x] 确认登录链和管理员写链均为高风险，不作为首刀；
- [x] 选择无状态、无授权、无写库副作用的管理员响应映射层。

## I1 管理员响应Presenter：代码完成，最终矩阵待收口

- [x] 新增`platform-api/app/user_admin_presenter.py`；
- [x] 迁移邮箱、手机号和实名脱敏；
- [x] 迁移`AdminUserRecord`到摘要/详情响应及`AdminAuditRecord`到审计响应映射；
- [x] 保持角色、申请角色、生命周期、时间戳、权限排序和Pydantic别名；
- [x] 敏感模式继续返回实名、联系方式、申请说明和拒绝原因；非敏感模式继续脱敏并隐藏说明；
- [x] `user_admin_service.py`仅通过三个别名调用Presenter；
- [x] 最后CEO、近期再认证、`BEGIN IMMEDIATE`、目标范围、角色授权、行版本和会话撤销全部留在Service；
- [x] 新增Presenter单元测试与永久架构边界测试；
- [x] Presenter纳入Pyright；
- [x] 目标Ruff、Pyright及管理员脱敏、目标范围、审计回滚、最后CEO并发和密码重置测试通过；
- [x] 一次性写权限Workflow已删除；
- [ ] 以本文档同步后的清理HEAD完成九项完整质量矩阵。

## I2 后续只读复核

I1通过后只读比较：

- Session列表与自助撤销；
- 自助资料/联系方式更新；
- 管理员读取与管理员写用例。

登录链、最后CEO、角色/状态变更、密码重置和会话撤销默认保持现状。只有形成单一无状态、无授权、无事务副作用的切口才提交代码；否则结束Identity代码修改并转入Portfolio。

每个切口必须通过Platform API、Research Provider、前端质量、两套浏览器、56张视觉基线及四项治理门禁。Draft PR始终保持Open、Draft、Unmerged；不得修改或合并`main`。
