# Legacy GitLab前端部署路径审计

状态：**仓库证据已确认；GitLab Runner与目标服务器状态延期核验**  
关联Issue：#136  
关联Draft PR：#139  
活动分支：`refactor/issue-136-platform-0-9-2-system-optimization`

## 结论

`platform-web/.gitlab-ci.yml`不是当前GitHub Actions体系的一部分，但它也不是可直接删除的普通脚手架文件。仓库内容表明，它曾定义一条面向固定站点的完整前端部署路径，可能依赖外部GitLab镜像仓库、专用Runner和服务器目录。

当前分类：**Legacy生产部署证据 / 外部运行状态未知 / 暂不可删除资产**。

该路径不阻塞后续GitHub内优化，但在取得外部证据前不得删除、改写或误宣称已停用。

## 仓库证据

`platform-web/.gitlab-ci.yml`定义两个Stage Job：

### `build-test`

- 使用`node:18.19.0`；
- 指定Runner标签`runner20`；
- 安装npm `9.5.0`和pnpm `8.1.0`；
- 执行`pnpm install`、`pnpm turbo run stub`和`pnpm run build:test`；
- 将`dist/*`和`node_modules`复制到`/www/wwwroot/risk-web.rta-office.com/`；
- 检查目标目录中的`index.html`和`assets`；
- 默认对非Tag流水线执行。

### `build-prod`

- 使用相同Node、npm、pnpm与Runner；
- 执行`pnpm run build`；
- 将构建结果复制到同一固定服务器目录；
- 仅在Tag匹配`risk*`时执行。

## 与当前GitHub交付线的关系

当前有效CI/CD入口位于仓库根目录`.github/workflows/`。子项目中的`.gitlab-ci.yml`不会被GitHub Actions执行，也没有证据证明当前GitHub仓库直接连接该GitLab Runner。

但仓库本身无法回答以下问题：

- 是否仍存在GitLab镜像仓库；
- `runner20`是否仍在线；
- `/www/wwwroot/risk-web.rta-office.com/`是否仍对外服务；
- 测试Job的“默认执行”规则是否仍在持续覆盖目标目录；
- 正式Tag部署是否仍被使用；
- 目标服务器是否与`deploy/`中的Nginx、Go Auth/Data和MySQL体系属于同一台主机；
- 该路径是否持有额外CI变量、SSH权限或服务器写权限。

## 当前停止规则

外部证据完成前：

- 不删除或重命名`platform-web/.gitlab-ci.yml`；
- 不修改Runner标签、目标目录、Tag规则或构建命令；
- 不在GitHub Actions中复制或激活该配置；
- 不将其视为当前受信发布流程；
- 不宣称GitLab Runner或目标站点已经停用；
- 不通过该文件触发任何部署。

## 延期的外部验收

该部分按所有者指示暂不阻塞GitHub内优化。后续取得权限时需只读确认：

1. GitLab项目、默认分支、最近Pipeline和Runner状态；
2. `runner20`的执行主机、权限与最近作业；
3. `risk-web.rta-office.com`的DNS、TLS、服务来源与最近访问；
4. 目标目录当前文件、Owner、更新时间和部署来源；
5. GitLab CI变量、Token和服务器凭据是否已经轮换；
6. 与`deploy/`旧生产链及当前Platform Web发布方式的关系；
7. 是否可以继续维护、受控迁移或确认无依赖后删除。

## GitHub内后续动作

- 将`.gitlab-ci.yml`加入Legacy生产资产永久架构门禁；
- GitHub内优化继续进行，不等待外部Runner或服务器证据；
- Draft PR #139继续保持Open、Draft、Unmerged；
- 任何删除或迁移决定仍需外部证据和所有者明确批准。
