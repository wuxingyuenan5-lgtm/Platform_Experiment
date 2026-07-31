# Legacy Risk-Control部署与数据依赖审计

状态：**L0仓库证据完成；外部服务器与数据库证据待验**  
关联Issue：#136  
关联Draft PR：#139  
活动分支：`refactor/issue-136-platform-0-9-2-system-optimization`

## 结论

`projects/risk-control`不能按历史样例、死代码或可归档目录处理。

仓库证据表明它至少同时具备：

1. 当前生产前端的兼容API目标；
2. 可直接构建并由systemd启动的Go服务；
3. 本机MySQL Schema创建与数据读写能力；
4. 用户、Session、账户、加密交易所凭据、Bybit仓位和净值历史的数据责任；
5. 定时抓取真实Bybit账户数据的能力；
6. Nginx、systemd、环境文件和固定服务器部署手册。

因此当前分类为：**活跃兼容依赖 / 潜在生产数据系统 / 暂不可删除资产**。

仓库无法证明目标服务器此刻仍在线，也无法证明MySQL中是否存在真实用户或交易账户。外部运行状态必须通过服务器和数据库只读检查确认，不能从Git历史或文档推断为已停用。

## 1. 当前产品依赖

### 1.1 生产前端仍指向Legacy

`platform-web/.env.production`当前将以下客户端指向旧服务：

- 默认API与上传：`/api/auth`；
- Monitor、Future和Data：`/api/data`；
- Monitor/Future WebSocket：`/api/data/ws`。

`platform-web/vite.config.ts`在开发环境也保留：

- `/api/auth` → `127.0.0.1:8080`；
- `/api/data` → `127.0.0.1:8082`。

旧数据客户端仍被多个风险与净值页面调用。例如`platform-web/src/api/data/product.ts`通过`dataHttp`请求净值列表、产品占比、资金占比和回撤数据；风险首页净值组件仍直接调用该客户端。

结论：Platform API已成为新身份、会员和受控交易能力的权威，但旧前端页面的数据面尚未完成迁移。

## 2. 部署与进程证据

### 2.1 原生安装脚本

`deploy/install-native.sh`会：

- 构建`platform-web`；
- 编译`auth-service`与`data-service`；
- 安装两个二进制到`/usr/local/lib/variable-global/`；
- 安装systemd Unit与Nginx配置；
- 启用并重启`variable-global-auth`、`variable-global-data`与Nginx；
- 对8080、8082和Nginx健康端点执行检查。

### 2.2 systemd

两个Unit均：

- 使用系统用户`variable-global`；
- 分别读取`/etc/variable-global/auth.env`与`data.env`；
- 依赖MySQL/MariaDB和网络；
- 设置`Restart=on-failure`；
- 由`multi-user.target`启用。

### 2.3 Nginx

`deploy/nginx-variable-global.conf`将：

- `/api/data`路由到8082；
- 其他`/api/*`默认路由到8080；
- 静态前端由Nginx提供；
- 当前模板仅监听HTTP 80并包含固定公网服务器地址。

`deploy/README.md`记录了固定服务器、`/opt/variable-global`部署目录、本机MySQL、systemd验收、日志检查和Git回滚流程。

结论：这是完整的原生生产部署链，而不是开发草图。

## 3. Go服务责任

### 3.1 auth-service

- Go 1.20；
- 依赖MySQL、JWT v5、bcrypt与UUID；
- 必需环境变量：`DB_DSN`、`JWT_SECRET`；
- 默认监听`127.0.0.1:8080`；
- 启动时自动确保Schema；
- 可通过环境变量创建初始管理员；
- 持有旧JWT、用户审批与数据库Session逻辑。

### 3.2 data-service

- Go 1.20；
- 依赖MySQL与真实Bybit REST适配；
- 必需/关键配置包括`DB_DSN`、`JWT_SECRET`、`ACCOUNT_ENCRYPTION_KEY`、Bybit凭据、自动迁移和调度开关；
- 默认监听`127.0.0.1:8082`；
- 默认可自动建表；
- 可每5分钟同步账户净值；
- 可从环境变量或相邻凭据文件加载Bybit密钥；
- 提供旧前端兼容Envelope与产品净值接口。

## 4. MySQL数据责任

### 4.1 auth-service表

- `users`：用户名、密码哈希、角色、部门、申请角色、审批状态与审批信息；
- `user_sessions`：数据库Session、IP、User-Agent和到期时间。

### 4.2 data-service表

- `users`：与auth-service共享表名，但字段版本不完全一致；
- `accounts`：账户类型、地址、初始资本、所有者、状态，以及加密API Key/Secret；
- `assets`：总资产、可用资金、Bybit仓位JSON、数据来源、快照类型与历史时间。

Repository还会自动补列、创建索引、插入Bybit账户、读取加密凭据并持续写入资产快照。

### 4.3 风险

- 两个服务都拥有`users`建表逻辑，但Schema不完全一致；
- Schema演进通过运行时`CREATE/ALTER`完成，没有独立、不可变迁移账本；
- 删除Legacy代码前必须确认真实表结构，而不能仅依赖当前Go源码；
- `accounts`和`assets`可能包含仍需迁移或保留的交易账户事实与历史净值。

## 5. 安全发现

### L0-S1 明文凭据暴露

当前仓库的历史项目文档包含过真实数据库密码、数据库用户名和默认管理员弱密码。即使当前服务器已停用，这些值也必须视为永久泄露。

要求：

1. 净化当前分支中的明文值；
2. 扩展Secret Scan，覆盖中文密码字段、SQL `IDENTIFIED BY`和弱哈希示例；
3. 服务器侧轮换MySQL用户密码、JWT Secret、账户加密密钥及任何复用的管理员密码；
4. 核验Git历史、备份、CI Artifact和服务器文件中的残留；
5. 完成轮换前，不得恢复旧服务对外使用。

仅删除Git当前文件不能使已泄露凭据重新安全。

### L0-S2 HTTP与CORS

- Nginx模板只监听HTTP 80；
- 两个Go服务的CORS允许任意Origin；
- 正式登录或敏感账户数据不得在未验证HTTPS、Origin和Cookie/Token边界的情况下恢复上线。

### L0-S3 凭据文件回退

Data Service会在Bybit环境变量为空时读取相邻凭据文件。必须确认服务器上该文件的路径、权限、来源和是否仍含有效密钥。

## 6. 与当前Platform的关系

### 已迁移到Platform API

- 新浏览器用户、角色、审批、Session与会员持仓权威；
- 受控交易、Risk Gate、Financial Fact、Venue/EOD Reconciliation；
- Runtime合同与外部执行副作用。

### 尚未证明已迁移

- 旧风险首页与产品净值页面的数据API；
- MySQL历史用户和Session是否存在仍有效账户；
- MySQL账户、加密交易所凭据、Bybit仓位与净值历史；
- 旧Nginx/systemd是否仍承载线上流量；
- 服务器定时任务、外部监控或手工运维流程。

## 7. 外部只读验收清单

在服务器上只读取并保存脱敏证据：

1. `systemctl is-enabled/is-active variable-global-auth variable-global-data nginx`；
2. `systemctl cat`与Unit文件Hash；
3. `ss -lntp`确认80、443、8080、8082和3306监听；
4. Nginx实际配置与证书状态；
5. `/opt/variable-global`实际分支、HEAD、工作区状态和远端地址；
6. `/etc/variable-global/*.env`仅记录键名、文件权限和Hash，不输出值；
7. `crontab`、systemd timers、supervisor、Docker和其他进程引用；
8. MySQL数据库、表、列、索引、外键、行数与最近更新时间；
9. `users`、`user_sessions`、`accounts`、`assets`是否有真实记录；
10. 加密凭据列是否有值，但不得导出密钥明文；
11. 最新数据库备份、恢复测试与保留期限；
12. Nginx访问日志中`/api/auth`与`/api/data`的近期请求量。

## 8. 分类与处置

| 资产 | 当前分类 | 允许动作 |
|---|---|---|
| `auth-service` | 活跃兼容依赖，运行状态待验 | 只读核验、凭据轮换、迁移规划 |
| `data-service` | 活跃数据依赖，可能含交易账户事实 | 只读核验、备份、迁移规划 |
| MySQL `risk_control` | 潜在生产数据权威 | 备份、Schema/行数审计、禁止删除 |
| systemd/Nginx部署 | 可执行生产部署链 | 核验实际服务器状态，禁止假设停用 |
| `platform-web`旧data API客户端 | 当前产品依赖 | 建立消费者清单与替代API Golden |
| 旧开发方案文档 | 历史证据与安全风险混合 | 净化凭据后保留或移入历史区 |
| 未实现的finance/risk微服务规划 | 历史规划 | 可在证据确认后归档，不影响运行时 |

## 9. 停止条件

在以下条件全部满足前，不得删除、重命名、迁移或合并`projects/risk-control`：

- 外部服务器与进程状态已确认；
- MySQL已备份并通过恢复抽检；
- 表结构、行数、最近写入和数据Owner已确认；
- 所有前端消费者已映射到替代API；
- 凭据完成轮换；
- HTTPS与Origin边界明确；
- Legacy停机与回滚方案经所有者批准。

## 下一门禁

L0-S1安全处置与L1外部证据交接：先净化当前仓库、建立永久Secret守卫，并生成可在服务器执行的只读采集脚本与人工交接清单。服务器侧执行必须由拥有访问权限的人员完成。
