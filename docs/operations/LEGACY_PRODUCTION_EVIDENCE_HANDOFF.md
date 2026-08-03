# Legacy Production只读证据采集交接

关联计划：`docs/architecture/PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md`  
阶段：Phase J / J0  
性质：只读采集，不停机、不改配置、不迁移数据

## 1. 执行前提

仅由拥有服务器访问权限、能够识别敏感信息的运维人员执行。

执行前不得：

- 修改systemd、Nginx或防火墙；
- 重启服务；
- 导出数据库业务行；
- 查看或复制环境变量值；
- 执行`mysqldump`、迁移或删除；
- 将证据直接提交到Git。

## 2. 获取代码

在服务器当前仓库中先确认工作区，不自动切换分支：

```bash
cd /opt/variable-global
git status --short --branch
git rev-parse HEAD
```

如果服务器仓库目录不同，记录实际路径，并通过环境变量传入：

```bash
export LEGACY_REPO_ROOT=/实际仓库路径
```

不要为了运行采集器而覆盖服务器当前代码。建议从已审核的提交单独复制以下单个脚本：

```text
scripts/collect-legacy-production-evidence.sh
```

复制时核对脚本SHA-256，并由两人确认来源。

## 3. 执行

使用普通Shell执行；脚本不会调用sudo：

```bash
bash scripts/collect-legacy-production-evidence.sh \
  /root/legacy-production-evidence
```

脚本仅采集：

- systemd启用与活动状态；
- TCP监听端口，不含进程命令行；
- 服务器仓库分支、HEAD与工作区状态；
- Auth/Data环境文件的存在性、权限、大小、修改时间、文件Hash和键名；
- Nginx语法检查；
- 在本机MySQL Socket免密只读可用时，采集`information_schema`中的表、列和索引元数据；
- 每个证据文件的SHA-256清单。

脚本不会采集：

- 环境变量值；
- JWT、数据库密码或Bybit密钥；
- 进程命令行；
- Nginx完整配置；
- 日志内容；
- 用户、账户、资产或交易业务行；
- 密码Hash或加密凭据列；
- 数据库备份。

## 4. 人工补充检查

采集器故意不覆盖以下高敏感或可能产生副作用的证据，需要运维人员在现场只读确认并仅记录结论：

1. 当前域名和TLS证书是否有效；
2. Nginx实际是否加载旧`/api/auth`与`/api/data`路由；
3. 近期访问日志中Legacy路由是否仍有请求；
4. MySQL各表准确行数和最近业务写入；
5. 是否存在有效用户、Session、交易账户和净值历史；
6. 加密凭据列是否存在非空值，但不得导出内容；
7. 是否存在cron、timer、supervisor或外部脚本写入；
8. 最新备份位置、时间、保留期和恢复演练结果；
9. 旧数据库、JWT、账户加密和管理员凭据是否已经轮换；
10. Bybit凭据文件是否存在、权限是否为最小权限、密钥是否仍有效。

## 5. 回传前审查

证据目录默认权限受`umask 077`保护。回传前必须逐文件检查：

```bash
find /root/legacy-production-evidence -type f -maxdepth 1 -print
```

重点搜索以下敏感模式：

```bash
grep -RniE \
  'password|passwd|secret|token|api[_-]?key|authorization|BEGIN .*PRIVATE KEY' \
  /root/legacy-production-evidence
```

匹配不一定代表Secret，但必须人工审阅。若发现真实值：

1. 立即删除整份证据目录；
2. 不上传、不截图、不粘贴到Issue；
3. 轮换暴露的凭据；
4. 报告采集器缺陷并停止后续操作。

## 6. 回传格式

不要把证据文件提交到代码仓库。建议通过受控内部渠道回传，并在Issue #136只记录：

- 证据包内部编号；
- 采集时间；
- 服务器别名，不记录可攻击的登录凭据；
- 采集脚本提交SHA；
- MANIFEST SHA-256；
- 每项检查的Pass/Fail/Unknown；
- 发现的阻断问题；
- 证据保管人和复核人。

## 7. J0决策

证据复核后只能形成以下结论之一：

- **Legacy Production继续维护**；
- **进入J1受控迁移**；
- **确认无依赖后进入退役计划**。

不得仅凭“服务看起来没在用”删除目录或数据库。必须同时满足服务器、数据、前端消费者、备份恢复和回滚证据。
