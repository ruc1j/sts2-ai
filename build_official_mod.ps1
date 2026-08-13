param(
    [string]$GameDir = 'E:\SteamLibrary\steamapps\common\Slay the Spire 2',
    [string]$Dotnet
)

$ErrorActionPreference = 'Stop'
if (-not $Dotnet) {
    $Dotnet = if ($IsMacOS) { (Get-Command dotnet -ErrorAction SilentlyContinue).Source } else { Join-Path $env:TEMP 'sts2-ai-dotnet/dotnet.exe' }
}
if (-not $Dotnet -or -not (Test-Path -LiteralPath $Dotnet)) { throw "dotnet SDK not found: $Dotnet" }

# On macOS the platform DLLs live inside the .app bundle, not directly under $GameDir.
if ($IsMacOS) {
    $dataRoot = Join-Path $GameDir 'SlayTheSpire2.app/Contents/Resources'
    $dataDirName = 'data_sts2_macos_arm64'
} else {
    $dataRoot = $GameDir
    $dataDirName = 'data_sts2_windows_x86_64'
}
if (-not (Test-Path -LiteralPath (Join-Path (Join-Path $dataRoot $dataDirName) 'sts2.dll'))) { throw "STS2 game not found: $GameDir" }

& $Dotnet build (Join-Path $PSScriptRoot 'official_mod/Sts2Ai.csproj') -c Release -p:Sts2GameDir=$dataRoot --nologo
if ($LASTEXITCODE) { exit $LASTEXITCODE }
