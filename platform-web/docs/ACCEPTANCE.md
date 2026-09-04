# Frontend Acceptance

## 自动检查

对普通前端变更至少执行：

```powershell
pnpm exec eslint --max-warnings 0 <changed-files>
pnpm type:check
pnpm build
```

涉及路由、权限、关键业务流或布局时，再执行对应 E2E、截图或专项验证脚本。

## 产品检查

- 直接 URL、菜单和操作按钮使用一致的 Capability 语义。
- loading、empty、unavailable、error、permission denied 和 stale 均有明确表现。
- `sample`、只读外部事实、Simulation 和 Live 不会混淆。
- Provider、Owner、内部 source、接口名和调试状态不会出现在普通业务页面。
- 刷新可以恢复路由表达的上下文，服务端业务事实重新查询。

## 金融与交易检查

- 数值、币种、单位、方向、符号和时间戳表达一致。
- ACK 不显示为 Fill，`result_unknown` 不显示为确定失败或可直接重试。
- 交易确认明确展示账户、策略、标的、方向、数量和模式。
- 窄视口和缩放状态下，风险提示与主要操作保持可见和可操作。

## 交付判断

构建通过只证明前端工程可构建，不证明外部 Provider、账户、部署或 Live Write 就绪。当前项目完成状态统一回填 [项目驾驶舱](../../docs/PROJECT.md)。
