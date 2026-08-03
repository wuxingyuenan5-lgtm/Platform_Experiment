# Platform顶层目录命名迁移计划

状态：**Gate D1与Gate D2均已完成并通过全量验证**  
关联Issue：#136  
关联Draft PR：#139  
迁移前视觉基线HEAD：`5439a3a230641719f165b5c5b6f21bc2019b08a6`  
Gate D1已验证HEAD：`86083650c9be64278c6bcadc59eaa5751c434a55`  
Gate D2已验证HEAD：`ea516aeaa387d780bfcbac3d5322845ebd2b527e`

## 1. 结果

在不改变业务逻辑、API合同、数据库Schema、交易语义、权限模型、会计口径或页面视觉的前提下，两个历史模板化顶层目录已完成治理：

| 原目录 | 最终目录 | 状态 | 含义 |
|---|---|---|---|
| `admin-risk` | `platform-web` | 已完成 | Platform Web前端 |
| `platform-backend` | `platform-api` | 已完成 | Platform API模块化单体 |
| `execution-runtime` | 保持不变 | 不迁移 | 独立执行Runtime |

目录迁移与Research、Identity、Portfolio及其他业务重构保持隔离。

## 2. 引用治理规则

迁移审计工具：

```bash
python scripts/audit-directory-migration.py \
  --format markdown \
  --output outputs/directory-migration-inventory.md \
  --fail-on-unclassified
```

活动CI、根目录契约、服务树、开发脚本与当前文档中的旧路径必须归零。已完成任务包、CHANGELOG及archive/audit/reviews/superseded中的历史事实不机械改写；`projects/risk-control`、外部参考代码和人工入口继续单独审查。

永久总检查：

```bash
python scripts/audit-directory-migration.py \
  --mode post-rename \
  --target all \
  --fail-on-unclassified
```

## 3. Gate D1：Platform Web——完成

- 原子目录提交：`cadf4c97caa13bc1332281788370c6874a2fcc1c`；
- 最终验证HEAD：`86083650c9be64278c6bcadc59eaa5751c434a55`；
- `platform-web/package.json`身份为`vg-platform-web`；
- Vben来源、许可证、作者信息和`@vben/*`依赖命名空间全部保留；
- 新增永久`Platform Directory Invariants`工作流；
- `frontend-no-new-debt.py`改为Rename感知，仅跳过内容完全未变的`R100`路径移动。

D1质量矩阵：

- Platform CI `30597676129`；
- Platform Directory Invariants `30597676127`；
- User System Browser E2E `30597676162`；
- Hedge Board Browser E2E `30597676131`；
- Platform Visual Baseline `30597676125`；
- Secret Scan `30597676128`；
- Version Consistency `30597676138`；
- Research Provider Smoke `30597676130`；
- Platform 0.9.2 Baseline Audit `30597676139`。

## 4. Gate D2：Platform API——完成

- 原子目录提交：`ea516aeaa387d780bfcbac3d5322845ebd2b527e`；
- `platform-api/pyproject.toml`身份为`variable-global-platform-api`；
- Python导入包继续为`app`；
- API路径、端口、数据库路径、Schema迁移、Runtime合同与业务语义均未改变；
- 旧`platform-backend/`不存在；
- 6个正式Workflow全部切换到`platform-api`；
- 永久目录守卫同时验证`platform-web`、`platform-api`和`all`；
- 一次性执行器、迁移Workflow与临时证据目录均已从最终树清除。

D2质量矩阵：

- Platform CI `30598389676`；
- Platform Directory Invariants `30598389694`；
- User System Browser E2E `30598389687`；
- Hedge Board Browser E2E `30598389680`；
- Platform Visual Baseline `30598389717`；
- Secret Scan `30598389712`；
- Version Consistency `30598389691`；
- Research Provider Smoke `30598389678`；
- Platform 0.9.2 Baseline Audit `30598389689`。

最终视觉Artifact：

- Artifact ID：`8781039663`；
- SHA-256：`38531ac47f5fdd7d949e40d25f9e2c1b1fc8aaed4e48c883d6e4c54e48ec54bf`。

## 5. 结论

两个目录Gate均满足：

- 旧目录不存在，目标目录存在；
- 活动旧路径归零，未分类引用为零；
- Repository Safety、Platform API、Execution Runtime、Frontend、两套浏览器E2E和56张视觉基线全部通过；
- Secret Scan、Version Consistency、Provider Smoke、Directory Invariants和Baseline Audit全部通过；
- Draft PR保持Open、Draft、Unmerged，`main`未修改。

目录治理没有改变Browser Session/API-Key隔离、CSRF/Origin、角色权限、会员数据隔离、Decimal、Financial Fact、PnL/NAV、正式会计/对账、数据库迁移不可变性、Kill Switch、两人审批、Live Write默认关闭、幂等性、Market/FOK/PostOnly/TP-SL、Result Unknown、EOD、Last Known Good或TLS边界。

## 6. 下一门禁

目录治理完成后，进入低风险模块化试点，顺序为：

1. Research；
2. Identity；
3. Portfolio。

交易、风险、正式会计、对账和Execution Runtime后置且保守。首个Research门禁应先拆分结构性热点并保持API合同、Provider状态语义和现有页面视觉不变。

## 7. 非目标

- 不拆分微服务，不引入新的分布式基础设施；
- 不删除或机械迁移`projects/risk-control`；
- 不自动修改GitHub仓库名`Platform_Experiment`或最终产品品牌；
- 不升级为`0.10.1`，不合并到`main`。
