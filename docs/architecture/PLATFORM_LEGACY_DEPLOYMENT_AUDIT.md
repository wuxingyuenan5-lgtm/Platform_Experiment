# Platform旧生产部署体系审计与迁移门禁

状态：**Phase J / J0只读盘点进行中；禁止删除、重命名或自动切换**  
关联Issue：#136  
关联Draft PR：#139  
活动分支：`refactor/issue-136-platform-0-9-2-system-optimization`  
开发与验收版本：Platform `0.9.2`

## 审计目标

仓库当前同时保留两套可运行架构。J0阶段只建立事实、依赖和迁移边界，不执行生产切换：

1. 当前目标架构：Platform Web + Platform API模块化单体 + Execution Runtime；
2. 旧生产架构：Nginx + Go Auth Service + Go Data Service + MySQL。

旧体系不是普通Demo或未引用目录。仓库内仍存在完整构建脚本、systemd服务、Nginx路由、固定服务器操作手册、MySQL备份/回滚流程及前端生产API配置。在缺少服务器和数据证据前，不得删除或隔离到不可执行位置。

## 当前目标架构

本地权威入口：`scripts/dev-platform.ps1`。

```text
platform-web        127.0.0.1:4373
    ↓ Browser Session / REST
platform-api        127.0.0.1:8000
    ↓ versioned Runtime contract
execution-runtime   127.0.0.1:8100
    ↓ Venue / Broker / MT5 / Bybit
```

该入口创建独立Python环境，启动Platform API和Execution Runtime，并使用前端`.env.platform.example`中的`VITE_PLATFORM_API_BASE_URL`连接Platform API。安全默认值保持Simulation、Fake Gateway和双侧Live Write关闭。

## 旧生产架构证据

### 构建与安装

`deploy/install-native.sh`会：

- 构建`platform-web`生产静态文件；
- 编译`projects/risk-control/auth-service`；
- 编译`projects/risk-control/data-service`；
- 安装两个Go二进制到`/usr/local/lib/variable-global/`；
- 安装systemd与Nginx配置；
- 读取`/etc/variable-global/auth.env`和`data.env`；
- 验证8080、8082和Nginx健康端点。

### 服务器与数据库

`deploy/README.md`明确描述固定服务器`65.49.234.98`、本机MySQL数据库`risk_control`、MySQL用户`risk_app`、生产备份、升级和回滚步骤。该文档还引用历史仓库`Lucasmingyu/Variable-Global`，说明部署来源与当前仓库治理体系存在漂移。

### systemd与Nginx

- `variable-global-auth.service`运行Auth Service并依赖MySQL/MariaDB；
- `variable-global-data.service`运行Data Service并依赖MySQL/MariaDB；
- Nginx将`/api/auth`代理到`127.0.0.1:8080`；
- Nginx将`/api/data`代理到`127.0.0.1:8082`；
- Nginx配置仍包含固定公网IP。

### 前端生产依赖

`platform-web/.env.production`当前仍将生产请求指向旧服务：

```text
VITE_GLOB_API_URL=/api/auth
VITE_GLOB_API_URL_PLOY=/api/auth
VITE_GLOB_API_URL_MONITOR=/api/data
VITE_GLOB_API_URL_FUTURE=/api/data
VITE_GLOB_API_URL_DATA=/api/data
VITE_GLOB_API_URL_MONITOR_WS=/api/data/ws
VITE_GLOB_API_URL_FUTURE_WS=/api/data/ws
```

因此，当前前端生产构建并未默认切换到Platform API / Execution Runtime。仅凭本地三进程验收，不能宣称旧生产体系已停用。

## 独立安全与数据模型

### 旧Auth Service

旧Auth Service：

- 直接连接MySQL；
- 自行维护用户Schema；
- 自行签发JWT；
- 支持初始化管理员；
- 使用独立角色字段；
- 当前CORS实现允许`Access-Control-Allow-Origin: *`。

这套模型不能直接等价为Platform API的Browser Session、API Key、CSRF/Origin、四角色权限和最后一名CEO保护。

### 旧Data Service

旧Data Service：

- 直接连接MySQL；
- 可自动创建Schema；
- 持有Bybit Client；
- 可启用账户净值定时同步；
- 当前CORS实现允许`Access-Control-Allow-Origin: *`。

这套数据不能在没有字段、精度、来源、自然键和审计映射的情况下并入Financial Fact、正式持仓、NAV或Execution Runtime。

## 当前停止决定

在以下证据齐备前：

- 不删除`projects/risk-control`；
- 不删除或改写`deploy/`；
- 不修改`.env.production`的API路由；
- 不将MySQL数据自动导入SQLite；
- 不关闭旧systemd服务；
- 不修改固定服务器；
- 不把旧JWT或密码Hash直接视为新用户系统凭据；
- 不将旧Bybit定时任务迁入Platform API；
- 不宣称旧体系为Demo或已废弃。

## J0必须取得的真实环境证据

### 服务器运行状态

在不暴露密钥值的前提下确认：

- `systemctl status variable-global-auth variable-global-data nginx`；
- 8080、8082、80/443实际监听进程；
- 当前Nginx已加载配置；
- 服务器仓库目录、分支、HEAD及是否存在未提交修改；
- `/etc/variable-global/auth.env`和`data.env`是否存在及权限；
- 生产域名、TLS证书和公网入口实际状态。

### MySQL与业务数据

先备份，再只读取：

- 数据库、表、索引和约束清单；
- 用户、角色、审批和密码Hash格式；
- 账户、凭据、净值和同步任务表；
- 数据量、最后更新时间和孤儿记录；
- 是否有外部脚本或服务写入；
- 是否存在无法从其他来源恢复的数据。

任何输出不得包含密码、JWT密钥、Bybit密钥、完整DSN或可复用账户凭据。

### API与前端消费者

冻结并对比：

- `/api/auth`全部端点及前端调用方；
- `/api/data`与`/api/data/ws`全部端点及前端调用方；
- 旧JWT登录状态与新Browser Session合同差异；
- 旧角色与新CEO/Administrator/Employee/Member映射；
- 旧账户数据与Platform API正式数据合同差异；
- 旧WebSocket与Execution Runtime/Platform API职责差异。

## 后续迁移门禁

只有完成J0证据后，才可制定J1迁移方案。J1至少必须包含：

1. 身份与权限迁移映射；
2. MySQL到目标持久化层的数据字典和可逆迁移；
3. 密码不可迁移时的重置或重新激活方案；
4. 前端API路由和同源代理切换；
5. 旧Bybit同步职责的保留、替代或停止决定；
6. 双写禁止与唯一数据Owner；
7. 灰度验证、停机窗口和回滚点；
8. 备份恢复演练；
9. TLS、日志、监控和Secret Provider验收；
10. 所有者明确批准。

## 完成定义

Phase J不是以“删除旧目录”为完成标准，而是以以下结果之一为准：

1. **继续生产使用**：旧体系被正式标记为Legacy Production并纳入维护边界；
2. **受控迁移**：真实数据与消费者完成可逆切换，旧体系进入只读退役窗口；
3. **确认无依赖**：服务器、数据、调用方和回滚证据证明可安全删除。

无论采用哪种结果，均必须通过完整自动化矩阵和真实环境验收；Draft PR #139继续保持Open、Draft、Unmerged。