param(
    [string]$GameDir = 'E:\SteamLibrary\steamapps\common\Slay the Spire 2',
    [int]$TimeoutSeconds = 45,
    [switch]$CleanupStaleMod
)

$ErrorActionPreference = 'Stop'
$exe = Join-Path $GameDir 'SlayTheSpire2.exe'
$modRoot = Join-Path $GameDir 'mods'
$installedMod = Join-Path $modRoot 'Sts2Ai'
$builtMod = Join-Path $PSScriptRoot 'official_mod\bin\Release\net9.0\Sts2Ai.dll'
$manifestPath = Join-Path $installedMod 'Sts2Ai.json'
$resolvedGameDir = [IO.Path]::GetFullPath($GameDir).TrimEnd('\')
$resolvedInstalledMod = [IO.Path]::GetFullPath($installedMod).TrimEnd('\')
if ($CleanupStaleMod) {
    if (Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue) { throw 'Slay the Spire 2 is already running.' }
    if (-not [string]::Equals($resolvedInstalledMod, (Join-Path $resolvedGameDir 'mods\Sts2Ai'), [StringComparison]::OrdinalIgnoreCase)) { throw "refusing to clean unexpected mod path: $resolvedInstalledMod" }
    if (-not (Test-Path -LiteralPath $installedMod -PathType Container)) { throw "stale mod directory not found: $installedMod" }
    if ((Get-Item -LiteralPath $installedMod).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "refusing to clean linked mod directory: $installedMod" }
    if ((Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json).id -cne 'Sts2Ai') { throw "refusing to clean mod with unexpected manifest id: $installedMod" }
    Remove-Item -LiteralPath $installedMod -Recurse -Force
    Write-Output "Removed stale Sts2Ai mod: $installedMod"
    return
}
$settingsFiles = @(Get-ChildItem -LiteralPath (Join-Path $env:APPDATA 'SlayTheSpire2\\steam') -Recurse -File -Filter settings.save)
$originalModsEnabled = @{}
if (Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue) { throw 'Slay the Spire 2 is already running.' }
if (-not (Test-Path -LiteralPath $exe)) { throw "game not found: $exe" }
if (-not (Test-Path -LiteralPath $builtMod)) { throw 'Build the mod first with build_official_mod.ps1.' }
if (-not $settingsFiles) { throw 'Slay the Spire 2 settings.save was not found.' }
$removeInstalledMod = $false
if (Test-Path -LiteralPath $installedMod) {
    $installedDll = Join-Path $installedMod 'Sts2Ai.dll'
    if (-not (Test-Path -LiteralPath $installedDll) -or (Get-FileHash -LiteralPath $installedDll).Hash -ne (Get-FileHash -LiteralPath $builtMod).Hash) {
        throw "refusing to overwrite existing mod: $installedMod"
    }
    $removeInstalledMod = $true
}

try {
    if (-not $removeInstalledMod) {
        New-Item -ItemType Directory -Path $installedMod -Force | Out-Null
        Copy-Item -LiteralPath $builtMod -Destination (Join-Path $installedMod 'Sts2Ai.dll')
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'official_mod\Sts2Ai.json') -Destination (Join-Path $installedMod 'Sts2Ai.json')
        $removeInstalledMod = $true
    }
    foreach ($settingsFile in $settingsFiles) {
        $settings = Get-Content -LiteralPath $settingsFile.FullName -Raw | ConvertFrom-Json
        if ($settings.mod_settings.mod_list.id -contains 'Sts2Ai') { throw 'Sts2Ai is already enabled in settings.save.' }
        $originalModsEnabled[$settingsFile.FullName] = $settings.mod_settings.mods_enabled
        $settings.mod_settings.mods_enabled = $true
        $settings.mod_settings.mod_list = @($settings.mod_settings.mod_list) + [pscustomobject]@{ id = 'Sts2Ai'; is_enabled = $true; source = 'mods_directory' }
        $settings | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $settingsFile.FullName -Encoding utf8
    }
    $info = [Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $exe
    $info.WorkingDirectory = $GameDir
    $info.UseShellExecute = $false
    $info.EnvironmentVariables['SteamAppId'] = '2868840'
    $info.EnvironmentVariables['SteamGameId'] = '2868840'
    $info.ArgumentList.Add('--unlock-ironclad-epochs')
    $process = [Diagnostics.Process]::Start($info)
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        $process.Kill($true)
        throw "unlock process timed out after $TimeoutSeconds seconds"
    }
    if ($process.ExitCode) { throw "unlock process failed with exit code $($process.ExitCode)" }
    Write-Output 'Ironclad Epochs 2-7 unlocked in the normal save.'
} finally {
    foreach ($settingsFile in $settingsFiles) {
        if (Test-Path -LiteralPath $settingsFile.FullName) {
            $settings = Get-Content -LiteralPath $settingsFile.FullName -Raw | ConvertFrom-Json
            if ($settings.mod_settings.PSObject.Properties.Name -contains 'mod_list') {
                $settings.mod_settings.mod_list = @($settings.mod_settings.mod_list | Where-Object { $_.id -ne 'Sts2Ai' })
                $settings.mod_settings.mods_enabled = $originalModsEnabled[$settingsFile.FullName]
                $settings | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $settingsFile.FullName -Encoding utf8
            }
        }
    }
    if ($removeInstalledMod -and (Test-Path -LiteralPath $installedMod)) { Remove-Item -LiteralPath $installedMod -Recurse -Force }
}
