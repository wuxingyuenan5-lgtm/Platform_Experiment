# Platform旧生产部署体系审计与迁移门禁

状态：**Phase J / J0仓库证据与采集工具完成；外部服务器与数据库证据待验**  
关联Issue：#136  
关联Draft PR：#139  
活动分支：`refactor/issue-136-platform-0-9-2-system-optimization`  
开发与验收版本：Platform `0.9.2`

## 结论

仓库同时保留两套可运行架构：

1. 当前目标架构：Platform Web + Platform API模块化单体 + Execution Runtime；
2. 旧生产架构：Nginx + Go Auth Service + Go Data Service + MySQL。

旧体系不是Demo、空目录或可直接归档资产。仓库证据表明它仍是当前生产前端的兼容API目标，具备完整构建、systemd启动、MySQL建表、Bybit同步、备份与回滚能力，并可能持有用户、Session、交易账户密钥、仓位和净值历史。

当前分类：**活跃兼容依赖 / 潜在生产数据系统 / 暂不可删除资产**。

GitHub仓库无法证明固定服务器此刻是否仍在线，也无法证明MySQL中是否存在真实用户或交易账户。外部运行状态必须通过服务器和数据库只读检查确认，不能从文档推断为已停用。

在J0外部证据完成并取得所有者批准前，**禁止删除、重命名或自动切换**旧生产体系。

## 1. 当前目标架构

本地权威入口：`scripts/dev-platform.ps1`。

```text
platform-web        127.0.0.1:4373
    ↓ Browser Session / REST
platform-api        127.0.0.1:8000
    ↓ versioned Runtime contract
execution-runtime   127.0.0.1:8100
    ↓ Venue / Broker / MT5 / Bybit
```

安全默认值保持Simulation、Fake Gateway和双侧Live Write关闭。

## 2. 旧生产架构证据

### 2.1 前端生产依赖

`platform-web/.env.production`仍将以下客户端指向旧服务：

```text
VITE_GLOB_API_URL=/api/auth
VITE_GLOB_API_URL_PLOY=/api/auth
VITE_GLOB_API_URL_MONITOR=/api/data
VITE_GLOB_API_URL_FUTURE=/api/data
VITE_GLOB_API_URL_DATA=/api/data
VITE_GLOB_API_URL_MONITOR_WS=/api/data/ws
VITE_GLOB_API_URL_FUTURE_WS=/api/data/ws
```

`platform-web/vite.config.ts`在开发环境也保留：

- `/api/auth` → `127.0.0.1:8080`；
- `/api/data` → `127.0.0.1:8082`。

`platform-web/src/api/data/product.ts`等旧数据客户端仍被风险首页、基金、净值和账户曲线页面调用。因此仅凭Platform本地三进程验收，不能宣称旧服务已停用。

### 2.2 构建与安装

`deploy/install-native.sh`会：

- 构建`platform-web`生产静态文件；
- 编译`projects/risk-control/auth-service`；
- 编译`projects/risk-control/data-service`；
- 安装两个Go二进制到`/usr/local/lib/variable-global/`；
- 安装systemd与Nginx配置；
- 读取`/etc/variable-global/auth.env`和`data.env`；
- 启用并重启两个服务和Nginx；
- 验证8080、8082与Nginx健康端点。

### 2.3 systemd与Nginx

- `variable-global-auth.service`运行Auth Service并依赖MySQL/MariaDB；
- `variable-global-data.service`运行Data Service并依赖MySQL/MariaDB；
- 两者均使用受限系统用户、环境文件与`Restart=on-failure`；
- Nginx将`/api/auth`代理到8080、`/api/data`代理到8082；
- 当前模板仅监听HTTP 80并包含固定公网服务器地址。

`deploy/README.md`记录固定服务器、本机MySQL、`/opt/variable-global`、备份、升级、日志和Git回滚流程，并引用历史仓库来源，说明生产部署来源与当前仓库治理体系存在漂移。

## 3. 旧服务责任

### 3.1 Auth Service

- Go 1.20；
- 直接连接MySQL；
- 依赖JWT v5、bcrypt与UUID；
- 必需`DB_DSN`和`JWT_SECRET`；
- 默认监听`127.0.0.1:8080`；
- 启动时自动确保用户与Session Schema；
- 可通过环境变量创建初始管理员；
- 持有独立JWT、角色、注册审批和数据库Session模型；
- CORS允许任意Origin。

该模型不能直接等价为Platform API的Browser Session、API Key、CSRF/Origin、四角色权限和最后一名CEO保护。

### 3.2 Data Service

- Go 1.20；
- 直接连接MySQL；
- 持有真实Bybit REST Client；
- 可自动建表并默认每5分钟同步账户净值；
- 使用`ACCOUNT_ENCRYPTION_KEY`保护账户密钥；
- 可从环境变量或相邻凭据文件加载Bybit Key/Secret；
- 提供账户CRUD、同步、净值、产品占比和旧前端兼容Envelope；
- CORS允许任意Origin。

这套数据不能在没有字段、精度、来源、自然键和审计映射的情况下并入Financial Fact、正式持仓、NAV或Execution Runtime。

## 4. MySQL数据责任

### Auth表

- `users`：用户名、密码哈希、角色、部门、申请角色和审批信息；
- `user_sessions`：数据库Session、IP、User-Agent和到期时间。

### Data表

- `users`：与Auth共享表名，但当前建表字段版本不完全一致；
- `accounts`：账户类型、地址、初始资本、所有者、状态和加密API Key/Secret；
- `assets`：总资产、可用资金、Bybit仓位JSON、来源、快照类型和历史时间。

Data Repository会自动补列、创建索引、插入Bybit账户、读取加密凭据并持续写入资产快照。旧设计还规划过`orders`、`risk_rules`和`risk_logs`，是否真实存在必须以服务器Schema为准。

风险：

- 两个服务都拥有`users`运行时建表逻辑，但字段版本不同；
- Schema演进通过`CREATE/ALTER`完成，没有独立不可变迁移账本；
- 删除代码前必须确认真实表结构、行数、最后写入和数据Owner；
- `accounts`与`assets`可能包含无法从其他来源完整恢复的账户事实与净值历史。

## 5. L0-S1凭据安全事件

仓库历史项目文档曾保存固定数据库密码、数据库用户名、默认管理员弱密码和MD5示例。这些值必须视为永久泄露，即使当前服务器已停用。

当前分支已执行：

1. 净化历史项目文档与旧启动入口中的可用凭据和弱密码方案；
2. 将动态验收密码说明改为不触发固定密码传播的临时凭据表述；
3. 扩展`scripts/scan-secrets.py`，检测Markdown中文密码字段、SQL固定密码及MD5/SHA-1密码字面量；
4. 保留历史Schema与部署事实，但不再提供可复用登录信息；
5. 增强后的Secret Scan已在完整矩阵中通过。

仍必须在服务器侧完成：

- 轮换MySQL用户密码；
- 轮换JWT Secret；
- 轮换账户加密密钥；
- 轮换Bybit或其他交易所密钥；
- 禁用或重置历史默认管理员；
- 检查Git历史、备份、CI Artifact、服务器环境文件和Shell历史。

仅删除Git当前文件不能使已泄露凭据重新安全。完成轮换前，不得恢复旧服务对外使用。

## 6. 其他安全阻断

### HTTP与Origin

- Nginx模板仅监听HTTP；
- 两个Go服务CORS允许任意Origin；
- 正式登录和账户数据不得在未验证HTTPS、Origin、Cookie/Token边界的情况下恢复上线。

### 凭据文件回退

Data Service在环境变量为空时会读取相邻Bybit凭据文件。必须确认服务器上的实际路径、权限、来源和密钥有效性。

## 7. 当前停止决定

在真实证据齐备前：

- 不删除或重命名`projects/risk-control`；
- 不删除或改写`deploy/`执行链；
- 不修改`.env.production`的API路由；
- 不将MySQL数据自动导入SQLite；
- 不关闭旧systemd服务；
- 不修改固定服务器；
- 不把旧JWT、密码Hash或角色直接视为新用户系统凭据；
- 不将旧Bybit定时任务迁入Platform API；
- 不宣称旧体系为Demo或已废弃。

## 8. J0外部只读验收

所有输出必须脱敏，不得包含密码、JWT、Bybit密钥、完整DSN或可复用账户凭据。

### 服务器与进程

1. `systemctl is-enabled/is-active variable-global-auth variable-global-data nginx`；
2. Unit文件路径、权限和Hash；
3. 80、443、8080、8082和3306监听状态；
4. Nginx实际加载配置、域名与TLS证书状态；
5. 服务器仓库目录、分支、HEAD和未提交修改；
6. `/etc/variable-global/*.env`仅记录键名、权限和文件Hash；
7. crontab、systemd timers、supervisor、Docker及其他进程引用；
8. Nginx访问日志中`/api/auth`、`/api/data`和WebSocket近期请求量。

### MySQL与数据

1. 数据库、表、列、索引、外键和实际DDL；
2. 各表行数、最近写入时间和孤儿记录；
3. 用户、角色、审批和密码Hash格式；
4. 账户、加密凭据列、净值和Bybit同步数据；
5. 外部脚本或服务写入方；
6. 最新备份、恢复测试与保留期限；
7. 不导出密钥、密码Hash或敏感业务明细。

### API与消费者

1. `/api/auth`全部端点与前端调用方；
2. `/api/data`、`/api/data/ws`全部端点与前端调用方；
3. 旧JWT与新Browser Session合同差异；
4. 旧角色与CEO/Administrator/Employee/Member映射；
5. 旧账户数据与Platform正式数据合同差异；
6. 旧WebSocket与Execution Runtime/Platform API职责差异。

## 9. 资产分类

| 资产 | 当前分类 | 允许动作 |
|---|---|---|
| Auth Service | 活跃兼容依赖，运行状态待验 | 只读核验、凭据轮换、迁移规划 |
| Data Service | 活跃数据依赖，可能含交易账户事实 | 只读核验、备份、迁移规划 |
| MySQL `risk_control` | 潜在生产数据权威 | 备份、Schema/行数审计、禁止删除 |
| systemd/Nginx部署 | 可执行生产部署链 | 核验实际状态，禁止假设停用 |
| 旧前端API客户端 | 当前产品依赖 | 建立消费者清单与替代API Golden |
| 历史开发文档 | 历史证据与安全风险混合 | 净化凭据后保留或归档 |
| 未实现微服务规划 | 历史规划 | 证据确认后可归档 |

## 10. J1迁移门禁

J0完成后只能三选一：

1. **继续生产使用**：正式标记为Legacy Production并纳入维护边界；
2. **受控迁移**：建立身份映射、数据字典、可逆迁移、API切换、停机窗口与回滚；
3. **确认无依赖**：服务器、数据、消费者和回滚证据证明可安全删除。

受控迁移至少必须包含：密码重置方案、唯一数据Owner、禁止双写、备份恢复演练、TLS、监控、Secret Provider和所有者明确批准。

## 11. 仓库内J0证据工具：完成

### 服务器只读采集器

`scripts/collect-legacy-production-evidence.sh`已完成并由永久架构测试约束。它只收集：

- systemd启用和运行状态；
-相关监听端口；
- 仓库分支、HEAD和工作区状态；
- 环境文件键名、权限、大小、修改时间和文件Hash；
- systemd Unit与已安装二进制的权限和Hash；
- Nginx语法检查；
- MySQL `information_schema`元数据；
- 证据文件SHA-256清单。

采集器禁止读取环境变量值、服务环境、Journal、业务表明细、密码Hash、交易所密钥、完整远端URL或执行任何服务变更。输出目录使用`0700`，文件使用`0600`，Manifest不包含自身。

### MySQL只读聚合清单

`scripts/legacy-production-readonly-inventory.sql`已完成，并要求通过批准的只读MySQL账户运行。它使用显式只读事务，只输出：

- 服务器只读状态；
- 表、列、索引和约束；
- `users`、`user_sessions`、`accounts`和`assets`的行数与最近时间；
- 敏感列是否存在非空记录的聚合计数。

脚本禁止导出用户行、密码Hash、API Key/Secret、Bybit仓位明细，也不包含任何写DDL/DML或权限变更语句。

### 永久门禁

- `test_architecture_legacy_production_gate.py`冻结旧生产资产、生产代理、Nginx/systemd及旧HTTP/MySQL Owner；
- `test_architecture_legacy_evidence_collector.py`冻结采集器只读、最小输出和SQL聚合边界；
- 增强Secret Scan冻结历史凭据净化要求；
- 仓库层J0治理已通过Platform CI、Provider、两套Browser E2E和56页视觉矩阵。

## 下一步：外部证据执行

仓库内能够完成的J0工作已经结束。下一步必须由拥有旧服务器和MySQL只读权限的人员：

1. 先确认并取得最新备份；
2. 在服务器副本或批准目录运行只读采集器；
3. 使用批准的只读MySQL账户运行聚合清单；
4. 人工检查并脱敏全部输出；
5. 回传不含Secret值的证据包；
6. 完成已泄露凭据的服务器侧轮换；
7. 再决定进入J1的继续维护、受控迁移或确认无依赖三选一。

在外部证据回传前，Phase J保持阻断状态；Draft PR #139继续保持Open、Draft、Unmerged。