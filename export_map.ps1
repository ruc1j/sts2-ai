param(
    [Parameter(Mandatory = $true)]
    [string]$Seed,
    [ValidateSet('Overgrowth', 'Underdocks', 'Hive', 'Glory')]
    [string]$Act = 'Overgrowth',
    [string]$GameDir = 'E:\SteamLibrary\steamapps\common\Slay the Spire 2',
    [string]$Output
)

$ErrorActionPreference = 'Stop'
$dataDir = Join-Path $GameDir 'data_sts2_windows_x86_64'
$assemblyPath = Join-Path $dataDir 'sts2.dll'
if (-not (Test-Path -LiteralPath $assemblyPath)) {
    throw "sts2.dll not found: $assemblyPath"
}

[System.Reflection.Assembly]::LoadFrom((Join-Path $dataDir 'GodotSharp.dll')) | Out-Null
$assembly = [System.Reflection.Assembly]::LoadFrom($assemblyPath)
$rngType = $assembly.GetType('MegaCrit.Sts2.Core.Random.Rng', $true)
$actType = $assembly.GetType("MegaCrit.Sts2.Core.Models.Acts.$Act", $true)
$mapType = $assembly.GetType('MegaCrit.Sts2.Core.Map.StandardActMap', $true)
$stringHelperType = $assembly.GetType('MegaCrit.Sts2.Core.Helpers.StringHelper', $true)

# StandardActMap.CreateFor uses this named RNG for Act 1.
$hash = [int32]$stringHelperType.GetMethod('GetDeterministicHashCode').Invoke($null, @($Seed))
$numericSeed = [BitConverter]::ToUInt32([BitConverter]::GetBytes($hash), 0)
$rng = $rngType.GetConstructor([type[]]@([uint32], [string])).Invoke(@($numericSeed, 'act_1_map'))
$actModel = [Activator]::CreateInstance($actType)
$map = $mapType.GetConstructors()[0].Invoke(@($rng, $actModel, $false, $false, $false, $null, $true))

$allPoints = @($map.StartingMapPoint) + @($map.GetAllMapPoints()) + @($map.BossMapPoint)
$points = foreach ($point in $allPoints | Sort-Object { $_.coord.row }, { $_.coord.col }) {
    [ordered]@{
        id = "$($point.coord.col):$($point.coord.row)"
        col = $point.coord.col
        row = $point.coord.row
        type = $point.PointType.ToString()
        children = @($point.Children | ForEach-Object { "$($_.coord.col):$($_.coord.row)" })
    }
}

$pointIds = [Collections.Generic.HashSet[string]]::new([string[]]$points.id)
foreach ($point in $points) {
    foreach ($child in $point.children) {
        if (-not $pointIds.Contains($child)) { throw "missing child $child from $($point.id)" }
        $childRow = [int]($child -split ':')[1]
        if ($childRow -ne $point.row + 1) { throw "non-adjacent edge $($point.id) -> $child" }
    }
}

$release = Get-Content -Raw -LiteralPath (Join-Path $GameDir 'release_info.json') | ConvertFrom-Json
$result = [ordered]@{
    game_version = $release.version
    seed = $Seed
    numeric_seed = $numericSeed
    act = $Act
    rows = $map.GetRowCount() + 2
    columns = $map.GetColumnCount()
    points = $points
}
$json = $result | ConvertTo-Json -Depth 6
if ($Output) {
    $parent = Split-Path -Parent $Output
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Set-Content -LiteralPath $Output -Value $json -Encoding utf8
} else {
    $json
}
