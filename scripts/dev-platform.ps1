[CmdletBinding()]
param(
  [switch]$SkipInstall,
  [switch]$ForceInstall,
  [switch]$SkipFrontend,
  [switch]$WithLegacyFrontend,
  [string]$LegacyFrontendPath = $env:VG_LEGACY_FRONTEND_PATH,
  [int]$HealthTimeoutSeconds = 90
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$RuntimePath = Join-Path $RepoRoot 'execution-runtime'
$BackendPath = Join-Path $RepoRoot 'platform-api'
$FrontendPath = Join-Path $RepoRoot 'platform-web'
$StateDir = Join-Path $RepoRoot '.codex\dev-platform'
$StatePath = Join-Path $StateDir 'platform-dev-state.json'
$LogDir = Join-Path $StateDir 'logs'
$FrontendPort = 4373
$BackendPort = 8000
$RuntimePort = 8100
$LegacyFrontendPort = 5273
$GeneratedDemoPasswordShown = $false

New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

function Invoke-CheckedNative {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $true)][string[]]$Arguments
  )

  & $FilePath @Arguments | Out-Host
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
  }
}

function Test-CommandAvailable {
  param([Parameter(Mandatory = $true)][string]$Name)

  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "$Name was not found. Install it before starting the platform."
  }
}

function New-TemporaryDemoPassword {
  $Bytes = New-Object byte[] 24
  $Rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try {
    $Rng.GetBytes($Bytes)
  }
  finally {
    if ($null -ne $Rng) {
      $Rng.Dispose()
    }
  }
  return [Convert]::ToBase64String($Bytes).TrimEnd('=').Replace('+', 'A').Replace('/', 'b') + '!9'
}

function Get-DemoPassword {
  if ($env:PLATFORM_DEMO_PASSWORD) {
    return $env:PLATFORM_DEMO_PASSWORD
  }

  $Password = New-TemporaryDemoPassword
  if (-not $script:GeneratedDemoPasswordShown) {
    Write-Host 'Generated temporary demo account password for this startup only:' -ForegroundColor Yellow
    Write-Host $Password -ForegroundColor Yellow
    Write-Host 'Set PLATFORM_DEMO_PASSWORD to reuse a known local demo password.' -ForegroundColor DarkYellow
    $script:GeneratedDemoPasswordShown = $true
  }
  return $Password
}

function Initialize-PythonProject {
  param(
    [Parameter(Mandatory = $true)][string]$ProjectPath,
    [string]$Extras = 'dev'
  )

  $VenvPath = Join-Path $ProjectPath '.venv'
  $PythonPath = Join-Path $VenvPath 'Scripts\python.exe'
  $InstallMarker = Join-Path $VenvPath '.platform-installed'
  $Created = $false

  if (-not (Test-Path $PythonPath)) {
    Write-Host "Creating Python 3.12 environment: $ProjectPath" -ForegroundColor Cyan
    if (Get-Command py -ErrorAction SilentlyContinue) {
      Invoke-CheckedNative -FilePath 'py' -Arguments @('-3.12', '-m', 'venv', $VenvPath)
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
      Invoke-CheckedNative -FilePath 'python' -Arguments @('-m', 'venv', $VenvPath)
    }
    else {
      throw 'Python was not found. Install Python 3.12 first.'
    }
    $Created = $true
  }

  $NeedsInstall = -not $SkipInstall -and ($ForceInstall -or $Created -or -not (Test-Path $InstallMarker))
  if ($NeedsInstall) {
    Write-Host "Installing Python dependencies: $ProjectPath" -ForegroundColor Cyan
    Push-Location $ProjectPath
    try {
      Invoke-CheckedNative -FilePath $PythonPath -Arguments @('-m', 'pip', 'install', '--upgrade', 'pip')
      Invoke-CheckedNative -FilePath $PythonPath -Arguments @('-m', 'pip', 'install', '-e', ".[${Extras}]")
      New-Item -ItemType File -Path $InstallMarker -Force | Out-Null
    }
    finally {
      Pop-Location
    }
  }

  return $PythonPath
}

function Get-PortListener {
  param([Parameter(Mandatory = $true)][int]$Port)

  $Connection = Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if (-not $Connection) {
    $Connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
      Select-Object -First 1
  }
  return $Connection
}

function Get-ProcessIdentity {
  param([Parameter(Mandatory = $true)][int]$ProcessId)

  $Cim = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
  if ($Cim) {
    return [pscustomobject]@{
      pid = [int]$Cim.ProcessId
      name = [string]$Cim.Name
      executablePath = [string]$Cim.ExecutablePath
      commandLine = [string]$Cim.CommandLine
    }
  }

  $Proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
  if ($Proc) {
    return [pscustomobject]@{
      pid = [int]$Proc.Id
      name = [string]$Proc.ProcessName
      executablePath = [string]$Proc.Path
      commandLine = ''
    }
  }

  return $null
}

function Test-ProcessMatchesProject {
  param(
    [Parameter(Mandatory = $true)][int]$ProcessId,
    [Parameter(Mandatory = $true)][string]$ExpectedPath
  )

  if ($ProcessId -le 0) {
    return $false
  }
  $Identity = Get-ProcessIdentity -ProcessId $Pid
  if (-not $Identity) {
    return $false
  }

  $Expected = $ExpectedPath.ToLowerInvariant()
  $Repo = $RepoRoot.ToLowerInvariant()
  $Executable = ([string]$Identity.executablePath).ToLowerInvariant()
  $CommandLine = ([string]$Identity.commandLine).ToLowerInvariant()
  return ($Executable.Contains($Expected) -or $CommandLine.Contains($Expected) -or $Executable.Contains($Repo) -or $CommandLine.Contains($Repo))
}

function Test-JsonHealth {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][string]$ServiceName
  )

  try {
    $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    if ([int]$Response.StatusCode -ne 200) {
      return $false
    }
    $Body = $Response.Content | ConvertFrom-Json
    return ([string]$Body.service -eq $ServiceName -and [string]$Body.status -eq 'ok')
  }
  catch {
    return $false
  }
}

function Test-FrontendHealth {
  param([Parameter(Mandatory = $true)][string]$Url)

  try {
    $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    if ([int]$Response.StatusCode -ne 200) {
      return $false
    }
    $Content = [string]$Response.Content
    return ($Content.Contains('id="htmlRoot"') -or $Content.Contains('/src/main') -or $Content.Contains('vite'))
  }
  catch {
    return $false
  }
}

function Test-ServiceHealth {
  param(
    [Parameter(Mandatory = $true)][string]$Kind,
    [Parameter(Mandatory = $true)][string]$Url
  )

  if ($Kind -eq 'runtime') {
    return Test-JsonHealth -Url $Url -ServiceName 'execution-runtime'
  }
  if ($Kind -eq 'api') {
    return Test-JsonHealth -Url $Url -ServiceName 'platform-api'
  }
  return Test-FrontendHealth -Url $Url
}

function Read-PlatformState {
  if (-not (Test-Path $StatePath)) {
    return @()
  }
  try {
    $State = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
    if ($State.services) {
      return @($State.services | Where-Object { $null -ne $_ })
    }
  }
  catch {
    Write-Host "Ignoring unreadable dev state file: $StatePath" -ForegroundColor Yellow
  }
  return @()
}

function Write-PlatformState {
  param([AllowNull()][object[]]$Services)

  $CleanServices = @($Services | Where-Object { $null -ne $_ })
  @{
    repoRoot = $RepoRoot
    updatedAt = (Get-Date).ToString('o')
    services = @($CleanServices)
  } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $StatePath -Encoding UTF8
}

function Set-ServiceState {
  param(
    [AllowNull()][object[]]$Services,
    [Parameter(Mandatory = $true)][object]$Service
  )

  $Next = @($Services | Where-Object { $null -ne $_ -and $_.name -ne $Service.name })
  $Next += $Service
  return ,@($Next | Where-Object { $null -ne $_ })
}

function New-ServiceState {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Kind,
    [Parameter(Mandatory = $true)][int]$Port,
    [Parameter(Mandatory = $true)][string]$HealthUrl,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory,
    [Parameter(Mandatory = $true)][string]$Ownership,
    [int]$LauncherPid = 0,
    [int]$ListenerPid = 0,
    [string]$Stdout = '',
    [string]$Stderr = '',
    [string]$StartedAt = ''
  )

  if (-not $StartedAt) {
    $StartedAt = (Get-Date).ToString('o')
  }

  return [pscustomobject]@{
    name = $Name
    kind = $Kind
    ownership = $Ownership
    port = $Port
    healthUrl = $HealthUrl
    workingDirectory = $WorkingDirectory
    launcherPid = $LauncherPid
    listenerPid = $ListenerPid
    stdout = $Stdout
    stderr = $Stderr
    startedAt = $StartedAt
    lastVerifiedAt = (Get-Date).ToString('o')
  }
}

function Start-OrReuseService {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Kind,
    [Parameter(Mandatory = $true)][int]$Port,
    [Parameter(Mandatory = $true)][string]$HealthUrl,
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $true)][string[]]$Arguments,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory,
    [AllowNull()][object[]]$Services
  )

  $Services = @($Services | Where-Object { $null -ne $_ })
  $Listener = Get-PortListener -Port $Port
  if ($Listener) {
    $ListenerPid = [int]$Listener.OwningProcess
    if (-not (Test-ServiceHealth -Kind $Kind -Url $HealthUrl)) {
      throw "$Name port $Port is occupied by PID $ListenerPid, but the exact health signature at $HealthUrl did not match. Refusing to reuse it."
    }

    $Existing = $Services | Where-Object { $_.name -eq $Name } | Select-Object -First 1
    if ($Existing -and $Existing.ownership -eq 'managed' -and [int]$Existing.listenerPid -eq $ListenerPid) {
      if (Test-ProcessMatchesProject -ProcessId $ListenerPid -ExpectedPath $WorkingDirectory) {
        Write-Host "$Name already managed on port $Port (listener PID $ListenerPid)." -ForegroundColor DarkGray
        $Existing.lastVerifiedAt = (Get-Date).ToString('o')
        return Set-ServiceState -Services $Services -Service $Existing
      }
      throw "$Name recorded listener PID $ListenerPid is managed, but its process identity could not be verified. Refusing to reuse."
    }

    Write-Host "$Name is already running on port $Port as an external exact-match service (listener PID $ListenerPid)." -ForegroundColor DarkGray
    $External = New-ServiceState -Name $Name -Kind $Kind -Port $Port -HealthUrl $HealthUrl -WorkingDirectory $WorkingDirectory -Ownership 'external' -LauncherPid 0 -ListenerPid $ListenerPid
    return Set-ServiceState -Services $Services -Service $External
  }

  $SafeName = ($Name -replace '[^A-Za-z0-9_-]', '-').ToLowerInvariant()
  $Stdout = Join-Path $LogDir "$SafeName.out.log"
  $Stderr = Join-Path $LogDir "$SafeName.err.log"
  Write-Host "Starting $Name on port $Port. Logs: $Stdout ; $Stderr" -ForegroundColor Cyan
  $Process = Start-Process `
    -FilePath $FilePath `
    -ArgumentList $Arguments `
    -WorkingDirectory $WorkingDirectory `
    -RedirectStandardOutput $Stdout `
    -RedirectStandardError $Stderr `
    -WindowStyle Hidden `
    -PassThru

  Wait-ForService -Name $Name -Kind $Kind -Url $HealthUrl -TimeoutSeconds $HealthTimeoutSeconds
  $NewListener = Get-PortListener -Port $Port
  if (-not $NewListener) {
    throw "$Name became healthy but no TCP listener was found on port $Port."
  }

  $Managed = New-ServiceState -Name $Name -Kind $Kind -Port $Port -HealthUrl $HealthUrl -WorkingDirectory $WorkingDirectory -Ownership 'managed' -LauncherPid ([int]$Process.Id) -ListenerPid ([int]$NewListener.OwningProcess) -Stdout $Stdout -Stderr $Stderr
  return Set-ServiceState -Services $Services -Service $Managed
}

function Wait-ForService {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Kind,
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][int]$TimeoutSeconds
  )

  $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    if (Test-ServiceHealth -Kind $Kind -Url $Url) {
      Write-Host "$Name ready: $Url" -ForegroundColor Green
      return
    }
    Start-Sleep -Seconds 1
  } while ((Get-Date) -lt $Deadline)

  $Service = (Read-PlatformState | Where-Object { $_.name -eq $Name } | Select-Object -First 1)
  if ($Service) {
    throw "$Name did not pass exact health checks within $TimeoutSeconds seconds: $Url. Logs: $($Service.stdout) ; $($Service.stderr)"
  }
  throw "$Name did not pass exact health checks within $TimeoutSeconds seconds: $Url"
}

function Initialize-DemoAccounts {
  param([Parameter(Mandatory = $true)][string]$PythonPath)

  Write-Host 'Initializing reusable demo accounts...' -ForegroundColor Cyan
  Push-Location $BackendPath
  $OldSeed = $env:USER_SYSTEM_DEMO_SEED
  $OldPassword = $env:USER_SYSTEM_DEMO_PASSWORD
  $OldPrefix = $env:USER_SYSTEM_DEMO_PREFIX
  $OldRefresh = $env:USER_SYSTEM_DEMO_REFRESH
  try {
    $env:USER_SYSTEM_DEMO_SEED = '1'
    $env:USER_SYSTEM_DEMO_PASSWORD = Get-DemoPassword
    $env:USER_SYSTEM_DEMO_PREFIX = 'demo'
    $env:USER_SYSTEM_DEMO_REFRESH = '1'
    Invoke-CheckedNative -FilePath $PythonPath -Arguments @('scripts\seed_user_system_demo.py')
  }
  finally {
    $env:USER_SYSTEM_DEMO_SEED = $OldSeed
    $env:USER_SYSTEM_DEMO_PASSWORD = $OldPassword
    $env:USER_SYSTEM_DEMO_PREFIX = $OldPrefix
    $env:USER_SYSTEM_DEMO_REFRESH = $OldRefresh
    Pop-Location
  }
}

function Initialize-FrontendProject {
  param([Parameter(Mandatory = $true)][string]$ProjectPath)

  Test-CommandAvailable -Name 'node'
  Test-CommandAvailable -Name 'npx'

  $PackagePath = Join-Path $ProjectPath 'package.json'
  if (-not (Test-Path $PackagePath)) {
    throw "Frontend package.json was not found: $PackagePath"
  }
  $Package = Get-Content $PackagePath -Raw | ConvertFrom-Json
  $PackageManager = if ($Package.packageManager) { [string]$Package.packageManager } else { 'pnpm@9.15.9' }
  if ($PackageManager -notmatch '^pnpm@') {
    throw "Expected pnpm packageManager in $PackagePath, found '$PackageManager'."
  }

  $NodeVersion = (& node --version)
  Write-Host "Node detected: $NodeVersion" -ForegroundColor DarkGray
  Write-Host "pnpm requested: $PackageManager" -ForegroundColor DarkGray

  $NodeModules = Join-Path $ProjectPath 'node_modules'
  if (-not $SkipInstall -and ($ForceInstall -or -not (Test-Path $NodeModules))) {
    Push-Location $ProjectPath
    try {
      Invoke-CheckedNative -FilePath 'npx' -Arguments @($PackageManager, 'install', '--frozen-lockfile')
    }
    finally {
      Pop-Location
    }
  }

  $VitePath = Join-Path $ProjectPath 'node_modules\.bin\vite.cmd'
  if (-not (Test-Path $VitePath)) {
    throw "Vite executable was not found: $VitePath. Run without -SkipInstall first."
  }
  return $VitePath
}

function Resolve-LegacyFrontendPath {
  if ($LegacyFrontendPath) {
    return $LegacyFrontendPath
  }
  throw 'Legacy frontend path was not provided. Pass -LegacyFrontendPath or set VG_LEGACY_FRONTEND_PATH.'
}

if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw 'Python was not found. Install Python 3.12 first.'
}

$RuntimePython = Initialize-PythonProject -ProjectPath $RuntimePath -Extras 'dev,crypto'
$BackendPython = Initialize-PythonProject -ProjectPath $BackendPath -Extras 'dev'

$BackendEnv = Join-Path $BackendPath '.env'
$BackendEnvExample = Join-Path $BackendPath '.env.example'
if (-not (Test-Path $BackendEnv) -and (Test-Path $BackendEnvExample)) {
  Copy-Item $BackendEnvExample $BackendEnv
  Write-Host 'Created platform-api/.env from .env.example.' -ForegroundColor DarkGray
}

$Services = Read-PlatformState
$Services = Start-OrReuseService `
  -Name 'Platform Execution Runtime' `
  -Kind 'runtime' `
  -Port $RuntimePort `
  -HealthUrl "http://127.0.0.1:$RuntimePort/health" `
  -FilePath $RuntimePython `
  -Arguments @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$RuntimePort") `
  -WorkingDirectory $RuntimePath `
  -Services $Services
Write-PlatformState -Services $Services

$Services = Start-OrReuseService `
  -Name 'Platform API' `
  -Kind 'api' `
  -Port $BackendPort `
  -HealthUrl "http://127.0.0.1:$BackendPort/health" `
  -FilePath $BackendPython `
  -Arguments @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$BackendPort") `
  -WorkingDirectory $BackendPath `
  -Services $Services
Write-PlatformState -Services $Services

Wait-ForService -Name 'Platform Execution Runtime' -Kind 'runtime' -Url "http://127.0.0.1:$RuntimePort/health" -TimeoutSeconds $HealthTimeoutSeconds
Wait-ForService -Name 'Platform API' -Kind 'api' -Url "http://127.0.0.1:$BackendPort/health" -TimeoutSeconds $HealthTimeoutSeconds
Initialize-DemoAccounts -PythonPath $BackendPython

if (-not $SkipFrontend) {
  $FrontendEnv = Join-Path $FrontendPath '.env.local'
  $FrontendEnvExample = Join-Path $FrontendPath '.env.platform.example'
  if (-not (Test-Path $FrontendEnv) -and (Test-Path $FrontendEnvExample)) {
    Copy-Item $FrontendEnvExample $FrontendEnv
    Write-Host 'Created platform-web/.env.local from .env.platform.example.' -ForegroundColor DarkGray
  }

  $VitePath = Initialize-FrontendProject -ProjectPath $FrontendPath
  $Services = Start-OrReuseService `
    -Name 'Platform Web' `
    -Kind 'web' `
    -Port $FrontendPort `
    -HealthUrl "http://127.0.0.1:$FrontendPort/index.html" `
    -FilePath $VitePath `
    -Arguments @('--host', '127.0.0.1', '--port', "$FrontendPort") `
    -WorkingDirectory $FrontendPath `
    -Services $Services
  Write-PlatformState -Services $Services
  Wait-ForService -Name 'Platform Web' -Kind 'web' -Url "http://127.0.0.1:$FrontendPort/index.html" -TimeoutSeconds $HealthTimeoutSeconds
}

if ($WithLegacyFrontend) {
  $ResolvedLegacyFrontendPath = Resolve-LegacyFrontendPath
  if (-not (Test-Path $ResolvedLegacyFrontendPath)) {
    throw "Legacy frontend path was not found: $ResolvedLegacyFrontendPath. Pass -LegacyFrontendPath or set VG_LEGACY_FRONTEND_PATH."
  }
  $LegacyVitePath = Initialize-FrontendProject -ProjectPath $ResolvedLegacyFrontendPath
  $Services = Start-OrReuseService `
    -Name 'Legacy Reference Web' `
    -Kind 'legacy-web' `
    -Port $LegacyFrontendPort `
    -HealthUrl "http://127.0.0.1:$LegacyFrontendPort/index.html" `
    -FilePath $LegacyVitePath `
    -Arguments @('--host', '127.0.0.1', '--port', "$LegacyFrontendPort") `
    -WorkingDirectory $ResolvedLegacyFrontendPath `
    -Services $Services
  Write-PlatformState -Services $Services
  Wait-ForService -Name 'Legacy Reference Web' -Kind 'legacy-web' -Url "http://127.0.0.1:$LegacyFrontendPort/index.html" -TimeoutSeconds $HealthTimeoutSeconds
}

Write-Host ''
Write-Host 'Platform local services are ready.' -ForegroundColor Green
Write-Host "Platform Execution Runtime: http://127.0.0.1:$RuntimePort/health"
Write-Host "Platform API:               http://127.0.0.1:$BackendPort/health"
if (-not $SkipFrontend) {
  Write-Host "Platform Web:               http://127.0.0.1:$FrontendPort/index.html"
}
if ($WithLegacyFrontend) {
  Write-Host "Legacy Reference Web:       http://127.0.0.1:$LegacyFrontendPort/index.html"
}
Write-Host "State file:                 $StatePath"
Write-Host "Logs:                       $LogDir"
Write-Host 'Safety defaults remain Simulation + Fake Gateway + Live Write disabled.' -ForegroundColor Yellow
