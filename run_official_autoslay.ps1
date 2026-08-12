param(
    [string]$Seed = 'FV2EVHXLCW',
    [string]$GameDir = 'E:\SteamLibrary\steamapps\common\Slay the Spire 2',
    [int]$TimeoutSeconds = 300,
    [string]$LogFile = (Join-Path $PSScriptRoot 'data\official_autoslay.log'),
    [string]$ResultFile = (Join-Path $PSScriptRoot 'data\official_act1_result.json'),
    [string]$AgentScript,
    [int]$AgentMaxCombats = 1,
    [switch]$StopAfterAgent,
    [switch]$StopAfterReward,
    [string]$AgentTrace = (Join-Path $PSScriptRoot 'data\official_agent_trace.jsonl'),
    [string]$MapFile = (Join-Path $PSScriptRoot 'data\official_act1_map.json'),
    [int]$AgentSimulations = 1000,
    [switch]$Visible
)

$ErrorActionPreference = 'Stop'
$exe = Join-Path $GameDir 'SlayTheSpire2.exe'
$modRoot = Join-Path $GameDir 'mods'
$installedMod = Join-Path $modRoot 'Sts2Ai'
$builtMod = Join-Path $PSScriptRoot 'official_mod\bin\Release\net9.0\Sts2Ai.dll'
if (Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue) { throw 'Slay the Spire 2 is already running.' }
if (-not (Test-Path -LiteralPath $exe)) { throw "game not found: $exe" }
if (-not (Test-Path -LiteralPath $builtMod)) { throw 'Build the mod first with build_official_mod.ps1.' }
if (Test-Path -LiteralPath $installedMod) { throw "refusing to overwrite existing mod: $installedMod" }

$isolatedAppData = Join-Path $env:TEMP ("sts2-ai-appdata-" + [guid]::NewGuid().ToString('N'))
$sourceUserData = Join-Path $env:APPDATA 'SlayTheSpire2'
$isolatedUserData = Join-Path $isolatedAppData 'SlayTheSpire2'
$process = $null
$agentProcess = $null
try {
    New-Item -ItemType Directory -Path $installedMod -Force | Out-Null
    Copy-Item -LiteralPath $builtMod -Destination (Join-Path $installedMod 'Sts2Ai.dll')
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'official_mod\Sts2Ai.json') -Destination (Join-Path $installedMod 'Sts2Ai.json')

    New-Item -ItemType Directory -Path $isolatedAppData -Force | Out-Null
    if (Test-Path -LiteralPath $sourceUserData) { Copy-Item -LiteralPath $sourceUserData -Destination $isolatedUserData -Recurse }
    Get-ChildItem -LiteralPath $isolatedUserData -Recurse -File -Filter settings.save -ErrorAction SilentlyContinue | ForEach-Object {
        $settings = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
        $settings.mod_settings.mods_enabled = $true
        $mods = @()
        Get-ChildItem -LiteralPath $modRoot -Recurse -File -Filter '*.json' | ForEach-Object {
            $manifest = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
            $mods += [ordered]@{ id = $manifest.id; is_enabled = ($manifest.id -eq 'Sts2Ai'); source = 'mods_directory' }
        }
        $settings.mod_settings.mod_list = $mods
        $settings.skip_intro_logo = $true
        $settings | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $_.FullName -Encoding utf8
    }

    $logParent = Split-Path -Parent $LogFile
    if ($logParent) { New-Item -ItemType Directory -Path $logParent -Force | Out-Null }
    $info = [Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $exe
    $info.WorkingDirectory = $GameDir
    $info.UseShellExecute = $false
    $info.EnvironmentVariables['APPDATA'] = $isolatedAppData
    $info.EnvironmentVariables['SteamAppId'] = '2868840'
    $info.EnvironmentVariables['SteamGameId'] = '2868840'
    if (-not $Visible) { $info.ArgumentList.Add('--headless') }
    $info.ArgumentList.Add('--sts2ai-autoslay')
    $info.ArgumentList.Add("--seed=$Seed")
    $info.ArgumentList.Add("--log-file=$LogFile")
    $info.ArgumentList.Add('--stop-after-act=1')
    $info.ArgumentList.Add("--result-file=$ResultFile")
    if ($AgentScript) {
        $observation = Join-Path $isolatedAppData 'observation.json'
        $action = Join-Path $isolatedAppData 'action.json'
        Remove-Item -LiteralPath $AgentTrace -Force -ErrorAction SilentlyContinue
        $agentInfo = [Diagnostics.ProcessStartInfo]::new()
        $agentInfo.FileName = 'python'
        $agentInfo.WorkingDirectory = $PSScriptRoot
        $agentInfo.UseShellExecute = $false
        $agentInfo.ArgumentList.Add($AgentScript)
        $agentInfo.ArgumentList.Add($observation)
        $agentInfo.ArgumentList.Add($action)
        $agentInfo.ArgumentList.Add('--enemy-data')
        $agentInfo.ArgumentList.Add((Join-Path $PSScriptRoot 'data\enemies_overgrowth.json'))
        $agentInfo.ArgumentList.Add('--simulations')
        $agentInfo.ArgumentList.Add($AgentSimulations.ToString())
        $agentProcess = [Diagnostics.Process]::Start($agentInfo)
        $info.ArgumentList.Add('--sts2ai-agent')
        $info.ArgumentList.Add("--agent-max-combats=$AgentMaxCombats")
        $info.ArgumentList.Add("--bridge-observation=$observation")
        $info.ArgumentList.Add("--bridge-action=$action")
        $info.ArgumentList.Add("--bridge-trace=$AgentTrace")
        $info.ArgumentList.Add("--bridge-map=$MapFile")
        if ($StopAfterAgent) { $info.ArgumentList.Add('--stop-after-agent=1') }
        if ($StopAfterReward) { $info.ArgumentList.Add('--stop-after-reward=1') }
    }
    $process = [Diagnostics.Process]::Start($info)
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        $process.Kill($true)
        $process.WaitForExit()
        throw "official simulation timed out after $TimeoutSeconds seconds; partial log: $LogFile"
    }
    if ($process.ExitCode) { throw "official simulation failed with exit code $($process.ExitCode); log: $LogFile" }
} finally {
    if ($process -and -not $process.HasExited) { $process.Kill($true); $process.WaitForExit() }
    if ($agentProcess -and -not $agentProcess.HasExited) { $agentProcess.Kill($true); $agentProcess.WaitForExit() }
    $resolvedMods = [IO.Path]::GetFullPath($modRoot).TrimEnd('\') + '\'
    $resolvedInstalled = [IO.Path]::GetFullPath($installedMod)
    if ($resolvedInstalled.StartsWith($resolvedMods, [StringComparison]::OrdinalIgnoreCase) -and (Split-Path $resolvedInstalled -Leaf) -eq 'Sts2Ai') {
        Remove-Item -LiteralPath $resolvedInstalled -Recurse -Force -ErrorAction SilentlyContinue
    }
    $resolvedTemp = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
    $resolvedIsolated = [IO.Path]::GetFullPath($isolatedAppData)
    if ($resolvedIsolated.StartsWith($resolvedTemp, [StringComparison]::OrdinalIgnoreCase) -and (Split-Path $resolvedIsolated -Leaf).StartsWith('sts2-ai-appdata-')) {
        Remove-Item -LiteralPath $resolvedIsolated -Recurse -Force -ErrorAction SilentlyContinue
    }
}
