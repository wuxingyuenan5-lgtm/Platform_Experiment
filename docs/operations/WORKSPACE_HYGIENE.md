# Workspace Hygiene

状态：**Phase J / J2 GitHub仓库减负进行中**  
关联Issue：#136  
关联Draft PR：#139

## 目标

仓库同时包含产品代码、测试、架构文档、生成依赖、本地运行状态和受保护的Legacy生产资产。仓库卫生治理的目标是：

- 让GitHub、Codex和命令行搜索聚焦可维护交付面；
- 防止截图、目录快照、构建输出和上游托管模板进入版本控制；
- 保留仍可能承担生产责任的Legacy资产，避免把“旧”误判成“可删除”；
- 不依赖某一台开发机的绝对路径、容量或文件数量作为长期规则。

## 1. 受维护代码面

当前受维护的一级代码目录：

- `platform-web/`
- `platform-api/`
- `execution-runtime/`

GitHub Actions只允许存在于仓库根目录：

```text
.github/workflows/
```

子项目中的`.github/workflows/`不会成为本仓库有效Workflow，且容易把上游模板、旧Token名称和错误发布目标重新带入项目，因此禁止保留。

## 2. 禁止提交的本地产物

以下类型不得进入Git：

- `node_modules/`、`dist/`、`.cache/`、`.turbo/`；
- Python虚拟环境和缓存；
- Playwright本地报告与截图；
- 临时首页检查截图，例如`home-*-check.png`；
- 手工生成的目录树快照，例如`src/file_structure.txt`；
- 指向上游项目域名的`CNAME`；
- 未被当前交付体系使用的Gitpod配置；
- 一次性修复、抓图、迁移或写权限Workflow。

`platform-web/.gitignore`必须持续忽略本地首页检查截图和目录快照。

## 3. Legacy生产资产例外

以下资产虽然不属于目标三进程架构，但外部运行状态尚未验证，不能按普通脚手架残留删除：

- `platform-web/.gitlab-ci.yml`；
- `platform-web/.env.production`中的Legacy API路由；
- `deploy/`；
- `projects/risk-control/`；
- Legacy Nginx、systemd、Go Auth/Data和MySQL相关文档与采集工具。

其中`.gitlab-ci.yml`定义了固定站点和专用Runner部署路径，权威审计见：

- `docs/architecture/PLATFORM_LEGACY_GITLAB_DEPLOYMENT_AUDIT.md`

其余旧生产体系见：

- `docs/architecture/PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md`

这些外部验收按所有者指示延期，不阻塞GitHub内优化，但也不得被自动删除、重命名或迁移。

## 4. 本地生成目录策略

以下路径通常很大，但属于可再生依赖或本地运行状态：

- `platform-web/node_modules/`
- `platform-web/dist/`
- `platform-api/.venv/`
- `execution-runtime/.venv/`
- Playwright报告、缓存和临时数据库

默认策略是通过`.gitignore`和`.ignore`排除，而不是由自动化脚本删除。

## 5. 禁止自动清理的状态

未经明确任务和备份确认，不得自动删除：

- `platform-api/data/`
- `execution-runtime/data/`
- 本地数据库和迁移账本；
- 审计、对账和恢复证据；
- Legacy生产资产；
- 用户上传或运行时生成的不可恢复内容。

## 6. 永久门禁

以下架构测试负责阻止已清理债务重新进入仓库：

- `platform-api/tests/test_architecture_frontend_repository_hygiene.py`
- `platform-api/tests/test_architecture_legacy_production_gate.py`

第一项禁止本地检查产物、上游CNAME、Gitpod配置和前端子目录Workflow回归；第二项冻结仍待外部核验的Legacy生产资产。

## 7. 安全搜索示例

```powershell
rg -n "StrategyBackendSnapshot" platform-web/src
rg -n "createExecutionBatch" platform-web/src platform-api/app execution-runtime/app
rg --files platform-web/src platform-api/app execution-runtime/app
```

跨仓库审计应优先使用`docs/codex/context-map.md`中定义的最小上下文包，避免默认读取整个仓库。
