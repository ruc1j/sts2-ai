param(
    [string]$GameDir = 'E:\SteamLibrary\steamapps\common\Slay the Spire 2',
    [string]$Output = (Join-Path $env:TEMP 'sts2-ai-decompiled')
)

$ErrorActionPreference = 'Stop'
$version = '9.1.0.7988'
$toolRoot = Join-Path $env:TEMP "ilspycmd-$version"
$package = Join-Path $toolRoot 'ilspycmd.nupkg'
$expanded = Join-Path $toolRoot 'package'
$tool = Join-Path $expanded 'tools\net8.0\any\ilspycmd.dll'
$assembly = Join-Path $GameDir 'data_sts2_windows_x86_64\sts2.dll'
if (-not (Test-Path -LiteralPath $assembly)) { throw "sts2.dll not found: $assembly" }

if (-not (Test-Path -LiteralPath $tool)) {
    New-Item -ItemType Directory -Force -Path $toolRoot | Out-Null
    Invoke-WebRequest "https://api.nuget.org/v3-flatcontainer/ilspycmd/$version/ilspycmd.$version.nupkg" -OutFile $package
    Copy-Item -LiteralPath $package -Destination "$package.zip" -Force
    Expand-Archive -LiteralPath "$package.zip" -DestinationPath $expanded -Force
}
if (-not (Test-Path -LiteralPath (Join-Path $Output 'sts2.csproj'))) {
    New-Item -ItemType Directory -Force -Path $Output | Out-Null
    dotnet $tool -p -o $Output -r (Split-Path $assembly) $assembly --disable-updatecheck
    if ($LASTEXITCODE) { throw "ilspycmd failed with exit code $LASTEXITCODE" }
}
$Output
