# Frontend Agent Rules

Scope: `platform-web/`.

- Preserve the existing navigation, visual system and user workflow unless the task explicitly changes product design.
- Use API clients under `src/api/platform/` and keep trading logic out of Vue templates where practical.
- Do not expose credentials, internal debug state or engineering explanations in product pages.
- Reuse existing components before introducing a new UI framework or state layer.

Checks for a Standard frontend change:

```powershell
pnpm exec eslint --max-warnings 0 <changed-files>
pnpm type:check
pnpm build
```

Package manager version is authoritative in `package.json#packageManager`.
