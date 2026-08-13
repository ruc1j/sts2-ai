param(
    [string]$Seed,
    [string]$GameDir = 'E:\SteamLibrary\steamapps\common\Slay the Spire 2',
    [int]$TimeoutSeconds = 300,
    [string]$LogFile = (Join-Path $PSScriptRoot 'data/official_autoslay.log'),
    [string]$ResultFile = (Join-Path $PSScriptRoot 'data/official_act1_result.json'),
    [ValidateRange(0, 3)]
    [int]$StopAfterAct = 1,
    [string]$AgentScript,
    [int]$AgentMaxCombats = 1,
    [switch]$StopAfterAgent,
    [switch]$StopAfterReward,
    [string]$AgentTrace = (Join-Path $PSScriptRoot 'data/official_agent_trace.jsonl'),
    [string]$AgentErrorLog = (Join-Path $PSScriptRoot 'data/official_agent_errors.log'),
    [string]$MapFile = (Join-Path $PSScriptRoot 'data/official_act1_map.json'),
    [int]$AgentSimulations = 1000,
    [switch]$Visible = $true,
    [switch]$UnlockIroncladEpochs
)

$ErrorActionPreference = 'Stop'
if (-not $PSBoundParameters.ContainsKey('Seed')) {
    $Seed = [guid]::NewGuid().ToString('N').Substring(0, 10).ToUpperInvariant()
}
Write-Output "Starting official autoslay with seed: $Seed"
function Resolve-ProjectPath([string]$Path) {
    if ([IO.Path]::IsPathRooted($Path)) { return [IO.Path]::GetFullPath($Path) }
    return Join-Path $PSScriptRoot $Path
}

$LogFile = Resolve-ProjectPath $LogFile
$ResultFile = Resolve-ProjectPath $ResultFile
$AgentTrace = Resolve-ProjectPath $AgentTrace
$AgentErrorLog = Resolve-ProjectPath $AgentErrorLog
$MapFile = Resolve-ProjectPath $MapFile

# The mod loader (ModManager.Initialize) scans a "mods" directory next to the actual OS
# executable (Path.GetDirectoryName(OS.GetExecutablePath())), confirmed via decompile. On
# Windows that's $GameDir itself; on macOS OS.GetExecutablePath() resolves inside the .app
# bundle, so the mods folder lives at .../SlayTheSpire2.app/Contents/MacOS/mods, not beside
# the bundle.
$exe = if ($IsMacOS) { Join-Path $GameDir 'SlayTheSpire2.app/Contents/MacOS/Slay the Spire 2' } else { Join-Path $GameDir 'SlayTheSpire2.exe' }
$exeDir = Split-Path -Parent $exe
$processName = [IO.Path]::GetFileNameWithoutExtension($exe)
$modRoot = Join-Path $exeDir 'mods'
$installedMod = Join-Path $modRoot 'Sts2Ai'
$builtMod = Join-Path $PSScriptRoot 'official_mod/bin/Release/net9.0/Sts2Ai.dll'
if (Get-Process -Name $processName -ErrorAction SilentlyContinue) { throw 'Slay the Spire 2 is already running.' }
if (-not (Test-Path -LiteralPath $exe)) { throw "game not found: $exe" }
if (-not (Test-Path -LiteralPath $builtMod)) { throw 'Build the mod first with build_official_mod.ps1.' }
if (Test-Path -LiteralPath $installedMod) { throw "refusing to overwrite existing mod: $installedMod" }

if ($IsMacOS) {
    # This build has no --user-data-dir override (checked --help), so user:// always
    # resolves to the real save under ~/Library/Application Support. Runs are NOT isolated
    # on macOS: settings.save is patched in place to enable the mod.
    $userDataRoot = Join-Path $HOME 'Library/Application Support/SlayTheSpire2'
} else {
    $isolatedAppData = Join-Path $env:TEMP ("sts2-ai-appdata-" + [guid]::NewGuid().ToString('N'))
    $sourceUserData = Join-Path $env:APPDATA 'SlayTheSpire2'
    $userDataRoot = Join-Path $isolatedAppData 'SlayTheSpire2'
}
$bridgeDir = $null
$process = $null
$agentProcess = $null
try {
    New-Item -ItemType Directory -Path $installedMod -Force | Out-Null
    Copy-Item -LiteralPath $builtMod -Destination (Join-Path $installedMod 'Sts2Ai.dll')
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'official_mod/Sts2Ai.json') -Destination (Join-Path $installedMod 'Sts2Ai.json')

    if (-not $IsMacOS) {
        New-Item -ItemType Directory -Path $isolatedAppData -Force | Out-Null
        if (Test-Path -LiteralPath $sourceUserData) { Copy-Item -LiteralPath $sourceUserData -Destination $userDataRoot -Recurse }
    }
    Get-ChildItem -LiteralPath $userDataRoot -Recurse -File -Filter settings.save -ErrorAction SilentlyContinue | ForEach-Object {
        $settings = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
        if (-not ($settings.PSObject.Properties.Name -contains 'mod_settings')) { return }
        # mod_settings is null until the player has opened the in-game modding screen once;
        # the game also separately requires PlayerAgreedToModLoading (the "mods warning" popup)
        # before it will actually load a mod, even with mods_enabled set. Add-Member -Force
        # handles both a null mod_settings and a settings.save that already has these keys.
        if ($null -eq $settings.mod_settings) { $settings.mod_settings = [PSCustomObject]@{} }
        Add-Member -InputObject $settings.mod_settings -Force -NotePropertyName mods_enabled -NotePropertyValue $true
        Add-Member -InputObject $settings.mod_settings -Force -NotePropertyName PlayerAgreedToModLoading -NotePropertyValue $true
        $mods = @()
        Get-ChildItem -LiteralPath $modRoot -Recurse -File -Filter '*.json' | ForEach-Object {
            $manifest = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
            $mods += [ordered]@{ id = $manifest.id; is_enabled = ($manifest.id -eq 'Sts2Ai'); source = 'mods_directory' }
        }
        Add-Member -InputObject $settings.mod_settings -Force -NotePropertyName mod_list -NotePropertyValue $mods
        $settings.skip_intro_logo = $true
        $settings | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $_.FullName -Encoding utf8
    }

    $logParent = Split-Path -Parent $LogFile
    if ($logParent) { New-Item -ItemType Directory -Path $logParent -Force | Out-Null }
    $info = [Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $exe
    $info.WorkingDirectory = $exeDir
    $info.UseShellExecute = $false
    if (-not $IsMacOS) { $info.EnvironmentVariables['APPDATA'] = $isolatedAppData }
    $info.EnvironmentVariables['SteamAppId'] = '2868840'
    $info.EnvironmentVariables['SteamGameId'] = '2868840'
    if (-not $Visible) { $info.ArgumentList.Add('--headless') }
    $info.ArgumentList.Add('--sts2ai-autoslay')
    $info.ArgumentList.Add("--seed=$Seed")
    $info.ArgumentList.Add("--log-file=$LogFile")
    if ($StopAfterAct) { $info.ArgumentList.Add("--stop-after-act=$StopAfterAct") }
    $info.ArgumentList.Add("--result-file=$ResultFile")
    if ($UnlockIroncladEpochs) { $info.ArgumentList.Add('--unlock-ironclad-epochs') }
    if ($AgentScript) {
        $bridgeDir = Join-Path ([IO.Path]::GetTempPath()) ("sts2-ai-bridge-" + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $bridgeDir -Force | Out-Null
        $observation = Join-Path $bridgeDir 'observation.json'
        $action = Join-Path $bridgeDir 'action.json'
        Remove-Item -LiteralPath $AgentTrace -Force -ErrorAction SilentlyContinue
        $pythonExe = (Get-Command python3 -ErrorAction SilentlyContinue).Source
        if (-not $pythonExe) { $pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source }
        $agentInfo = [Diagnostics.ProcessStartInfo]::new()
        $agentInfo.FileName = $pythonExe
        $agentInfo.WorkingDirectory = $PSScriptRoot
        $agentInfo.UseShellExecute = $false
        $agentInfo.ArgumentList.Add($AgentScript)
        $agentInfo.ArgumentList.Add($observation)
        $agentInfo.ArgumentList.Add($action)
        $agentInfo.ArgumentList.Add('--enemy-data')
        @('enemies_overgrowth.json', 'enemies_hive.json', 'enemies_glory.json') | ForEach-Object {
            $agentInfo.ArgumentList.Add((Join-Path $PSScriptRoot "data/$_"))
        }
        $agentInfo.ArgumentList.Add('--simulations')
        $agentInfo.ArgumentList.Add($AgentSimulations.ToString())
        $agentInfo.ArgumentList.Add('--error-log')
        $agentInfo.ArgumentList.Add($AgentErrorLog)
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
    $sep = [IO.Path]::DirectorySeparatorChar
    $resolvedMods = [IO.Path]::GetFullPath($modRoot).TrimEnd($sep) + $sep
    $resolvedInstalled = [IO.Path]::GetFullPath($installedMod)
    if ($resolvedInstalled.StartsWith($resolvedMods, [StringComparison]::OrdinalIgnoreCase) -and (Split-Path $resolvedInstalled -Leaf) -eq 'Sts2Ai') {
        Remove-Item -LiteralPath $resolvedInstalled -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (-not $IsMacOS -and $isolatedAppData -and (Test-Path -LiteralPath $isolatedAppData)) {
        $resolvedTemp = [IO.Path]::GetFullPath($env:TEMP).TrimEnd($sep) + $sep
        $resolvedIsolated = [IO.Path]::GetFullPath($isolatedAppData)
        if ($resolvedIsolated.StartsWith($resolvedTemp, [StringComparison]::OrdinalIgnoreCase) -and (Split-Path $resolvedIsolated -Leaf).StartsWith('sts2-ai-appdata-')) {
            Remove-Item -LiteralPath $resolvedIsolated -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    if ($bridgeDir -and (Test-Path -LiteralPath $bridgeDir)) { Remove-Item -LiteralPath $bridgeDir -Recurse -Force -ErrorAction SilentlyContinue }
}
