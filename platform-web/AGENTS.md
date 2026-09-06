# Frontend Agent Rules

Scope: `platform-web/`.

- Preserve the existing navigation, visual system and user workflow unless the task explicitly changes product design.
- Use API clients under `src/api/platform/` and keep trading logic out of Vue templates where practical.
- Do not expose credentials, internal debug state or engineering explanations in product pages.
- Product-data metadata such as provider/source/actionability may exist in state and tests, but visible UI should use business language such as `暂无数据`, `数据暂不可用`, `待复核` and `权限不足`.
- Reuse existing components before introducing a new UI framework or state layer.

Select from these checks according to the root risk-based validation rule; a local low-risk edit does not require every command, while shared navigation, contracts or release-level changes require broader coverage:

```powershell
corepack pnpm exec eslint --max-warnings 0 <changed-files>
corepack pnpm type:check
corepack pnpm build
```

Package manager version is authoritative in `package.json#packageManager`.
