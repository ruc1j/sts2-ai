param(
    [string]$GameDir = 'E:\SteamLibrary\steamapps\common\Slay the Spire 2',
    [string]$Dotnet = (Join-Path $env:TEMP 'sts2-ai-dotnet\dotnet.exe')
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Dotnet)) { throw "dotnet SDK not found: $Dotnet" }
if (-not (Test-Path -LiteralPath (Join-Path $GameDir 'data_sts2_windows_x86_64\sts2.dll'))) { throw "STS2 game not found: $GameDir" }

& $Dotnet build (Join-Path $PSScriptRoot 'official_mod\Sts2Ai.csproj') -c Release -p:Sts2GameDir=$GameDir --nologo
if ($LASTEXITCODE) { exit $LASTEXITCODE }
