# Runbook

## Local Health Checks

Frontend:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:4373/index.html"
```

Platform backend:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/health"
```

Runtime gateway:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8100/health"
```

## Notes

- Prefer frontend port `4373` for current work.
- Do not use destructive cleanup commands.
- Do not change trading or deployment behavior as part of folder organization.
- If the machine feels slow, first check duplicate dev servers before deleting dependencies.
- Current expected long-running local services are frontend `4373`, platform backend `8000`, and Runtime Gateway `8100` when execution integration is needed.

## Check Running Ports

```powershell
Get-NetTCPConnection -LocalPort 4373,8000,8100 -ErrorAction SilentlyContinue |
  Select-Object LocalAddress,LocalPort,State,OwningProcess
```

## Workspace Noise

Large directories are excluded from normal search through root `.ignore`:

- `platform-web/node_modules/`
- `platform-web/dist/`
- `execution-runtime/.venv/`
- `platform-api/.venv/`
- `outputs/`

Do not delete these directories just to reduce Codex token use. The ignore rules already prevent routine scanning.

Large external reference code has been moved out of the project root:

```text
C:\Users\jiuxi\Desktop\codex\平台设计其他辅助内容\平台移动文件夹，例如参考代码等\参考代码
```
