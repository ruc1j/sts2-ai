param(
    [ValidateSet('Overgrowth', 'Underdocks', 'Hive', 'Glory')]
    [string]$Act = 'Overgrowth',
    [string]$GameDir = 'E:\SteamLibrary\steamapps\common\Slay the Spire 2',
    [int]$FormationSamples = 4096,
    [string]$Output
)

$ErrorActionPreference = 'Stop'
$dataDir = Join-Path $GameDir 'data_sts2_windows_x86_64'
$assemblyPath = Join-Path $dataDir 'sts2.dll'
if (-not (Test-Path -LiteralPath $assemblyPath)) { throw "sts2.dll not found: $assemblyPath" }

[Reflection.Assembly]::LoadFrom((Join-Path $dataDir 'GodotSharp.dll')) | Out-Null
$assembly = [Reflection.Assembly]::LoadFrom($assemblyPath)
$db = $assembly.GetType('MegaCrit.Sts2.Core.Models.ModelDb', $true)
$subtypes = $assembly.GetType('MegaCrit.Sts2.Core.Models.AbstractModelSubtypes', $true).GetProperty('All').GetValue($null)
$models = $db.GetField('_contentById', [Reflection.BindingFlags]'NonPublic,Static').GetValue($null)
$getId = $db.GetMethod('GetId', [type[]]@([type]))

# ModelDb.Init also asks the live mod manager for types. Populate only the generated base-game list offline.
foreach ($type in $subtypes) {
    $id = $getId.Invoke($null, @($type))
    if (-not $models.ContainsKey($id)) { $models[$id] = [Activator]::CreateInstance($type) }
}

$actType = $assembly.GetType("MegaCrit.Sts2.Core.Models.Acts.$Act", $true)
$actModel = $models[$getId.Invoke($null, @($actType))]
$declared = [Reflection.BindingFlags]'Public,NonPublic,Instance,DeclaredOnly'
$rngType = $assembly.GetType('MegaCrit.Sts2.Core.Random.Rng', $true)
$rngConstructor = $rngType.GetConstructor([type[]]@([uint32], [int]))
$encounterRngField = $assembly.GetType('MegaCrit.Sts2.Core.Models.EncounterModel').GetField('_rng', [Reflection.BindingFlags]'NonPublic,Instance')

function Get-ScalarProperties($model) {
    $values = [ordered]@{}
    foreach ($property in $model.GetType().GetProperties($declared)) {
        if ($property.GetIndexParameters().Count -or $property.PropertyType -notin @([int], [float], [double], [decimal], [bool])) { continue }
        try { $values[$property.Name] = $property.GetValue($model) } catch {}
    }
    return $values
}

function Get-Intent($intent) {
    $result = [ordered]@{ type = $intent.GetType().Name }
    $damageProperty = $intent.GetType().GetProperty('DamageCalc', [Reflection.BindingFlags]'Public,NonPublic,Instance')
    if ($damageProperty) {
        try { $result.damage = $damageProperty.GetValue($intent).Invoke() } catch {}
        try { $result.repeats = $intent.Repeats } catch {}
    }
    return $result
}

function Get-State($state) {
    $result = [ordered]@{ id = $state.Id; type = $state.GetType().Name }
    if ($state.GetType().Name -eq 'MoveState') {
        $perform = $state.GetType().GetField('_onPerform', [Reflection.BindingFlags]'NonPublic,Instance').GetValue($state)
        $result.perform = $perform.Method.Name
        $result.intents = @($state.Intents | ForEach-Object { Get-Intent $_ })
        $result.next = if ($state.FollowUpState) { $state.FollowUpState.Id } else { $state.FollowUpStateId }
    } elseif ($state.GetType().Name -eq 'RandomBranchState') {
        $result.branches = @($state.States | ForEach-Object {
            $branch = [ordered]@{
                state = $_.stateId
                repeat = $_.repeatType.ToString()
                max_times = $_.maxTimes
                cooldown = $_.cooldown
            }
            try { $branch.weight = $_.GetWeight() } catch { $branch.weight = $null }
            $branch
        })
    } elseif ($state.GetType().Name -eq 'ConditionalBranchState') {
        $statesProperty = $state.GetType().GetProperty('States', [Reflection.BindingFlags]'NonPublic,Instance')
        $result.branches = @($statesProperty.GetValue($state) | ForEach-Object {
            $idField = $_.GetType().GetField('id', [Reflection.BindingFlags]'Public,NonPublic,Instance')
            [ordered]@{ state = $idField.GetValue($_); condition = 'runtime' }
        })
    }
    return $result
}

$monsters = foreach ($monster in @($actModel.AllMonsters) | Sort-Object { $_.Id.ToString() }) {
    $mutableMonster = $monster.ToMutable()
    $machineMethod = $mutableMonster.GetType().GetMethod('GenerateMoveStateMachine', [Reflection.BindingFlags]'NonPublic,Instance')
    $machine = $machineMethod.Invoke($mutableMonster, @())
    $initial = $machine.GetType().GetField('_initialState', [Reflection.BindingFlags]'NonPublic,Instance').GetValue($machine)
    [ordered]@{
        id = $monster.Id.ToString()
        class = $monster.GetType().Name
        values = Get-ScalarProperties $monster
        initial_state = $initial.Id
        states = @($machine.States.Values | Sort-Object Id | ForEach-Object { Get-State $_ })
    }
}

$encounters = foreach ($encounter in @($actModel.AllEncounters) | Sort-Object { $_.Id.ToString() }) {
    $formations = [ordered]@{}
    $generate = $encounter.GetType().GetMethod('GenerateMonsters', [Reflection.BindingFlags]'NonPublic,Instance')
    # ponytail: brute-force seed sampling; parse GenerateMonsters IL if an encounter exceeds this finite sample.
    foreach ($sample in 0..($FormationSamples - 1)) {
        $mutableEncounter = $encounter.ToMutable()
        $encounterRngField.SetValue($mutableEncounter, $rngConstructor.Invoke(@([uint32]$sample, 0)))
        $formation = @($generate.Invoke($mutableEncounter, @()) | ForEach-Object {
            [ordered]@{ monster = $_.Item1.Id.ToString(); slot = $_.Item2; values = Get-ScalarProperties $_.Item1 }
        })
        $signature = ($formation | ForEach-Object { "$($_.monster)@$($_.slot)@$($_.values | ConvertTo-Json -Compress)" }) -join '|'
        if (-not $formations.Contains($signature)) { $formations[$signature] = $formation }
    }
    [ordered]@{
        id = $encounter.Id.ToString()
        class = $encounter.GetType().Name
        room_type = $encounter.RoomType.ToString()
        weak = $encounter.IsWeak
        monsters = @($encounter.AllPossibleMonsters | ForEach-Object { $_.Id.ToString() })
        tags = @($encounter.Tags | ForEach-Object { $_.ToString() })
        min_gold = $encounter.MinGoldReward
        max_gold = $encounter.MaxGoldReward
        formations = @($formations.Values)
    }
}

$release = Get-Content -Raw -LiteralPath (Join-Path $GameDir 'release_info.json') | ConvertFrom-Json
$result = [ordered]@{
    game_version = $release.version
    act = $Act
    encounters = @($encounters)
    monsters = @($monsters)
}
$json = $result | ConvertTo-Json -Depth 12
if ($Output) {
    $parent = Split-Path -Parent $Output
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Set-Content -LiteralPath $Output -Value $json -Encoding utf8
} else {
    $json
}
