# Platform顶层目录命名迁移计划

状态：**Gate D1已完成并全量验证；Gate D2待实施**  
关联Issue：#136  
关联Draft PR：#139  
迁移前视觉基线HEAD：`5439a3a230641719f165b5c5b6f21bc2019b08a6`  
Gate D1已验证HEAD：`86083650c9be64278c6bcadc59eaa5751c434a55`

## 1. 目标

在不改变业务逻辑、API合同、数据库Schema、交易语义、权限模型、会计口径或前端视觉的前提下，消除两个历史模板化顶层目录名：

| 原目录 | 目标目录 | 状态 | 含义 |
|---|---|---|---|
| `admin-risk` | `platform-web` | 已完成 | Platform Web前端 |
| `platform-backend` | `platform-api` | 待实施 | Platform API模块化单体 |
| `execution-runtime` | 保持不变 | 不迁移 | 独立执行Runtime |

本阶段只处理目录身份、活动路径引用和必要的包元数据，不进行Research、Identity、Portfolio或其他业务模块重构。

## 2. 已验证前置条件

目录迁移以Platform `0.9.2`视觉门禁完成后的绿色HEAD为基线。迁移前基线已通过：

- Platform CI：Repository Safety、Platform API、Execution Runtime、Frontend完整质量门禁；
- User System Browser E2E；
- Hedge Board Browser E2E；
- 56张全平台四档视觉基线；
- Secret Scan、Version Consistency、Research Provider Smoke和Baseline Audit。

迁移前证据继续保留，用于与目录迁移后的页面、合同和测试结果做同基线比较。

## 3. 引用清单

使用以下命令生成可重复的逐文件清单：

```bash
python scripts/audit-directory-migration.py \
  --format markdown \
  --output outputs/directory-migration-inventory.md \
  --fail-on-unclassified
```

迁移前基线统计：

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

## 5. Gate D1：Platform Web——已完成

Gate D1以原子提交完成前端目录与活动引用迁移：

- 原子目录提交：`cadf4c97caa13bc1332281788370c6874a2fcc1c`；
- 最终验证HEAD：`86083650c9be64278c6bcadc59eaa5751c434a55`；
- `admin-risk/`已整体迁移为`platform-web/`；
- 旧目录不存在，`platform-web/package.json`身份为`vg-platform-web`；
- Vben来源、许可证、作者信息和`@vben/*`依赖命名空间全部保留；
- 全部活动旧路径已归零，历史与外部事实按分类保留；
- 新增永久`Platform Directory Invariants`工作流，防止旧目录或活动引用回归；
- `frontend-no-new-debt.py`改为Rename感知：仅跳过内容完全未变的`R100`路径移动，新增、修改及内容变化Rename仍严格Lint。

永久验证命令：

```bash
python scripts/audit-directory-migration.py \
  --mode post-rename \
  --target platform-web \
  --fail-on-unclassified
```

Gate D1最终质量矩阵：

- Platform CI `30597676129`；
- Platform Directory Invariants `30597676127`；
- User System Browser E2E `30597676162`；
- Hedge Board Browser E2E `30597676131`；
- Platform Visual Baseline `30597676125`；
- Secret Scan `30597676128`；
- Version Consistency `30597676138`；
- Research Provider Smoke `30597676130`；
- Platform 0.9.2 Baseline Audit `30597676139`。

全部成功。目录迁移未改变认证、权限、API、数据库、交易、会计、Runtime或页面视觉语义。

## 6. Gate D2：Platform API——待实施

Gate D2必须在独立原子提交中完成：

1. `platform-backend/`整体移动为`platform-api/`；
2. 更新全部活动`platform-backend`引用；
3. 仅更新后端包身份字段，不改变Python导入包`app`、API路径、端口、数据库路径或迁移语义；
4. 扩展永久目录守卫，同时验证`platform-web`与`platform-api`；
5. 运行：

```bash
python scripts/audit-directory-migration.py \
  --mode post-rename \
  --target platform-api \
  --fail-on-unclassified
```

6. 再次运行完整质量矩阵和56张视觉基线；
7. 最终以`--target all`执行总检查。

## 7. 原子性要求

- 不允许先复制新目录、后续提交再删除旧目录；
- 不允许提交一个CI和本地启动均不可用的中间HEAD；
- 目录树移动、活动引用修复及对应结构守卫必须位于同一提交；
- Git历史中的Rename识别由内容相似性决定，不为了显示“重命名”而改写业务文件；
- 每个Gate失败时，直接回退该Gate提交，不在破损树上继续叠加修复。

## 8. 验收标准

每个Gate必须同时满足：

- 旧目录不存在，目标目录存在；
- 对应旧名在活动CI、脚本、服务树和当前文档中为零；
- 剩余旧名仅位于已分类的历史记录、迁移治理或待确认外部依赖中；
- Repository Safety与文档一致性检查通过；
- Platform API与Execution Runtime lint/type/tests通过；
- Frontend access guard、lint、no-new-debt、两套Type Check和Build通过；
- User System与Hedge Board浏览器E2E通过；
- 56张视觉基线通过且页面级横向溢出为零；
- Secret Scan、Version Consistency、Provider Smoke、Directory Invariants和Baseline Audit通过；
- Draft PR保持Open、Draft、Unmerged，`main`不变。

## 9. 非目标

本阶段不做以下事项：

- 不拆分微服务，不引入新的分布式基础设施；
- 不重构`hedgeBoard/index.vue`或`research_providers.py`；
- 不改变Browser Session/API-Key隔离、CSRF、Origin或角色权限；
- 不改变Decimal、Financial Fact、PnL、NAV、正式会计和对账口径；
- 不改变Kill Switch、两人审批、Live Write默认关闭或Runtime执行语义；
- 不删除`projects/risk-control`；
- 不升级为`0.10.1`，不合并到`main`。
