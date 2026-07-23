# Project Agent Rules

## Safety

- 禁止批量删除文件或目录。
- 不要使用 `del /s`, `rd /s`, `rmdir /s`, `Remove-Item -Recurse`, or `rm -rf`.
- 需要删除文件时，只能一次删除一个明确路径的文件。
- 不得提交真实密钥、密码、Token 或 `.env` 内容。
- 不得自行修改交易、权限、部署、数据库结构等高风险逻辑。

## Working Project

- Main project root: `C:\Users\jiuxi\Desktop\codex\平台后端测试`
- Preferred frontend URL: `http://127.0.0.1:5173/index.html#/strategy/platform`
- Preferred backend API: `http://127.0.0.1:8000/api/v1`

## Path Ownership

- `admin-risk/`: frontend application. Do not move in Phase 1.
- `platform-backend/`: platform backend. Do not move in Phase 1.
- `execution-runtime/`: execution gateway. Do not move in Phase 1.
- `references/`: external material and imported reference code.
- `outputs/`: generated deliverables and temporary artifacts.
- `tasks/`: scoped work packets.

## Search Hygiene

- Prefer `rg` for project search.
- Do not search `node_modules`, `.venv`, `dist`, or `outputs` unless the user explicitly asks for dependency/generated-output inspection.
- Large external reference code now lives outside the project root at `C:\Users\jiuxi\Desktop\codex\平台设计其他辅助内容\平台移动文件夹，例如参考代码等\参考代码`; inspect only explicit subprojects when requested.
- Use `5173` as the frontend reference port unless the user asks about another running instance.

## UI Policy

- Do not add backend test panels, debug dashboards, or implementation-explanation cards to production-facing pages unless explicitly requested.
- Product screens should prioritize dense, operational workflows over decorative marketing layouts.
