# Platform顶层目录命名迁移计划

状态：**执行前门禁已建立，尚未实施目录重命名**  
关联Issue：#136  
关联Draft PR：#139  
验证基线HEAD：`5439a3a230641719f165b5c5b6f21bc2019b08a6`

## 1. 目标

在不改变业务逻辑、API合同、数据库Schema、交易语义、权限模型、会计口径或前端视觉的前提下，消除两个历史模板化顶层目录名：

| 当前目录 | 目标目录 | 含义 |
|---|---|---|
| `admin-risk` | `platform-web` | Platform Web前端 |
| `platform-backend` | `platform-api` | Platform API模块化单体 |
| `execution-runtime` | 保持不变 | 独立执行Runtime |

本阶段只处理目录身份、活动路径引用和必要的包元数据，不进行Research、Identity、Portfolio或其他业务模块重构。

## 2. 已验证前置条件

目录迁移以Platform `0.9.2`视觉门禁完成后的绿色HEAD为基线。该HEAD已通过：

- Platform CI：Repository Safety、Platform API、Execution Runtime、Frontend完整质量门禁；
- User System Browser E2E；
- Hedge Board Browser E2E；
- 56张全平台四档视觉基线；
- Secret Scan、Version Consistency、Research Provider Smoke和Baseline Audit。

迁移前证据必须保留，便于对目录迁移后的页面、合同和测试结果做同基线比较。

## 3. 引用清单

使用以下命令生成可重复的逐文件清单：

```bash
python scripts/audit-directory-migration.py \
  --format markdown \
  --output outputs/directory-migration-inventory.md \
  --fail-on-unclassified
```

当前基线统计：

| 旧名 | 文件数 | 引用行 | 活动合同文件 | 活动引用行 | 历史记录文件 | 外部/遗留文件 |
|---|---:|---:|---:|---:|---:|---:|
| `admin-risk` | 88 | 378 | 67 | 289 | 18 | 3 |
| `platform-backend` | 108 | 625 | 73 | 435 | 34 | 1 |

活动合同包括CI、根目录契约、服务树、开发脚本和当前文档。历史记录包括`tasks/`、`CHANGELOG.md`以及archive/audit/reviews/superseded目录。当前清单没有未分类文件。

## 4. 引用处理规则

### 4.1 必须迁移

以下类别中的旧目录名必须在对应原子迁移提交中全部消除：

- `.github/workflows/`中的路径过滤、工作目录、缓存路径和Artifact路径；
- `scripts/`与`deploy/`中的启动、测试、审计、版本、上下文和部署路径；
- `.gitignore`、`.ignore`、根README和当前工程契约；
- Playwright配置、包配置、应用路径常量及架构测试；
- `docs/codex/`、系统图、Ownership、Runbook、当前技术文档和验收文档；
- 两个服务树之间的相互引用。

### 4.2 原则上保留

历史证据不得机械全文替换：

- `tasks/`中的已完成任务包；
- `CHANGELOG.md`中的历史版本事实；
- archive、audit、reviews、superseded目录中的当时路径记录。

若历史文档仍被当前脚本或Runbook引用，则先将其升级为当前文档或增加明确兼容说明，不能在未知语义下直接替换。

### 4.3 必须人工确认

以下引用单独审查，不随主目录机械迁移：

- `projects/risk-control`及其真实服务器/MySQL/用户数据依赖；
- `references/`中的外部参考代码；
- `00-人工可读目录/`和`projects/启动说明.md`中的人工入口；
- GitHub仓库名`Platform_Experiment`与最终产品品牌。

## 5. 实施顺序

迁移拆为两个独立验证门禁，不把两个服务与业务重构混成单一大提交。

### Gate D1：Platform Web

同一个原子提交中完成：

1. `admin-risk/`整体移动为`platform-web/`；
2. 更新全部活动`admin-risk`引用；
3. 仅更新前端包的身份字段，保留Vben来源和`@vben/*`依赖命名空间；
4. 运行：

```bash
python scripts/audit-directory-migration.py \
  --mode post-rename \
  --target admin-risk \
  --fail-on-unclassified
```

5. 运行完整质量矩阵和56张视觉基线；
6. 只有全部通过，才进入Gate D2。

### Gate D2：Platform API

同一个原子提交中完成：

1. `platform-backend/`整体移动为`platform-api/`；
2. 更新全部活动`platform-backend`引用；
3. 仅更新后端包身份字段，不改变Python导入包`app`、API路径或数据库路径语义；
4. 运行：

```bash
python scripts/audit-directory-migration.py \
  --mode post-rename \
  --target platform-backend \
  --fail-on-unclassified
```

5. 再次运行完整质量矩阵和56张视觉基线。

最终再以`--target all`执行一次总检查。

## 6. 原子性要求

- 不允许先复制新目录、后续提交再删除旧目录；
- 不允许提交一个CI和本地启动均不可用的中间HEAD；
- 目录树移动、活动引用修复及对应结构守卫必须位于同一提交；
- Git历史中的Rename识别由内容相似性决定，不为了显示“重命名”而改写业务文件；
- 每个Gate失败时，直接回退该Gate提交，不在破损树上继续叠加修复。

## 7. 验收标准

每个Gate必须同时满足：

- 旧目录不存在，目标目录存在；
- 对应旧名在活动CI、脚本、服务树和当前文档中为零；
- 剩余旧名仅位于已分类的历史记录或待确认外部依赖中；
- Repository Safety与文档一致性检查通过；
- Platform API与Execution Runtime lint/type/tests通过；
- Frontend access guard、lint、no-new-debt、两套Type Check和Build通过；
- User System与Hedge Board浏览器E2E通过；
- 56张视觉基线通过且页面级横向溢出为零；
- Secret Scan、Version Consistency、Provider Smoke和Baseline Audit通过；
- Draft PR保持Open、Draft、Unmerged，`main`不变。

## 8. 非目标

本阶段不做以下事项：

- 不拆分微服务，不引入新的分布式基础设施；
- 不重构`hedgeBoard/index.vue`或`research_providers.py`；
- 不改变Browser Session/API-Key隔离、CSRF、Origin或角色权限；
- 不改变Decimal、Financial Fact、PnL、NAV、正式会计和对账口径；
- 不改变Kill Switch、两人审批、Live Write默认关闭或Runtime执行语义；
- 不删除`projects/risk-control`；
- 不升级为`0.10.1`，不合并到`main`。
