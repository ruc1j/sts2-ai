param(
    [Parameter(Mandatory = $true)]
    [string]$GameDir,
    [string]$Plan = (Join-Path $PSScriptRoot '.dsh/bosslab_plan.json'),
    [string]$OutDir = '',
    [string]$AgentScript = (Join-Path $PSScriptRoot 'official_agent.py'),
    [int]$AgentSimulations = 100,
    [int]$TimeoutSeconds = 300,
    [int]$From = 0,
    [int]$To = -1,
    [switch]$Visible = $true,
    [switch]$ContinueOnFailure
)

# Runs one Act 2 boss trial per game launch, in the order the plan lists them.
#
# One trial per process is a deliberate v1 choice: the boss fight's ending (reward screens on a win,
# the game over screen on a loss) is not driven by the lab, so the trial writes its result line as
# soon as the combat stops and quits (official_mod/BossLab.cs). Launching costs about 20-30 s per
# trial, which is still far cheaper than a 6.5-minute full run, and the entry state (deck, HP, relics,
# potions, seed, floors walked) comes from the plan instead of a played route, so arms are comparable.
#
# The heavy lifting (game exe discovery, mod install/cleanup, headless flag, the Python agent
# sidecar, timeouts) is reused from run_official_autoslay.ps1 via its -BossLab and -ExtraGameArgs
# switches, which are inert unless passed.

$ErrorActionPreference = 'Stop'
function Resolve-Path2([string]$Path) {
    if ([IO.Path]::IsPathRooted($Path)) { return [IO.Path]::GetFullPath($Path) }
    return [IO.Path]::GetFullPath((Join-Path $PSScriptRoot $Path))
}

$PlanAbs = Resolve-Path2 $Plan
if (-not (Test-Path -LiteralPath $PlanAbs)) { throw "plan not found: $PlanAbs" }
if (-not $OutDir) {
    $stamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
    $OutDir = Join-Path $PSScriptRoot "data/bosslab_$stamp"
}
$OutDir = Resolve-Path2 $OutDir
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$OutFile = Join-Path $OutDir 'lab_results.jsonl'
$LogAll = Join-Path $OutDir 'runner.log'

$builtMod = Join-Path $PSScriptRoot 'official_mod/bin/Release/net9.0/Sts2Ai.dll'
if (-not (Test-Path -LiteralPath $builtMod)) {
    throw "mod not built: $builtMod (run build_official_mod.ps1 -GameDir '$GameDir' first)"
}

# Never launch beside another run, and refuse a stale mod install left by a killed run.
$running = if ($IsMacOS -or $IsLinux) {
    (Get-Process -Name 'SlayTheSpire2' -ErrorAction SilentlyContinue | Measure-Object).Count
} else {
    (Get-Process -Name 'SlayTheSpire2' -ErrorAction SilentlyContinue | Measure-Object).Count
}
if ($running -gt 0) { throw "ANOMALY: a game is already running ($running process); only one at a time" }
$installedMod = Join-Path $GameDir 'mods/Sts2Ai'
if ($IsMacOS) { $installedMod = Join-Path $GameDir 'SlayTheSpire2.app/Contents/MacOS/mods/Sts2Ai' }
if (Test-Path -LiteralPath $installedMod) { throw "ANOMALY: stale mod install $installedMod" }

$planJson = Get-Content -LiteralPath $PlanAbs -Raw | ConvertFrom-Json
$trialCount = [int]$planJson.trials.Count
if ($To -lt 0 -or $To -gt $trialCount) { $To = $trialCount }
if ($From -ge $To) { throw "nothing to run (From $From, To $To, trials $trialCount)" }

$commit = (& git -C $PSScriptRoot rev-parse HEAD).Trim()
function Sha256([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
$metaPath = Join-Path $OutDir 'lab_meta.json'
Set-Content -LiteralPath $metaPath -Value ((ConvertTo-Json -Depth 4 ([ordered]@{
    started = (Get-Date).ToString('s')
    plan = $PlanAbs
    plan_sha256 = Sha256 $PlanAbs
    mod_dll_sha256 = Sha256 $builtMod
    agent_script = $AgentScript
    agent_script_sha256 = Sha256 (Resolve-Path2 $AgentScript)
    runner_sha256 = Sha256 (Resolve-Path2 ($PSCommandPath))
    source_commit = $commit
    game_dir = $GameDir
    agent_simulations = $AgentSimulations
    trials_planned = $To - $From
})) + "`n")

Write-Output "BOSSLAB START trials $From..$($To - 1) out=$OutDir commit=$($commit.Substring(0, 7))"
$failures = @()
for ($i = $From; $i -lt $To; $i++) {
    $prefix = Join-Path $OutDir ('trial_{0:d4}' -f $i)
    $startLines = if (Test-Path -LiteralPath $OutFile) { (Get-Content -LiteralPath $OutFile | Measure-Object -Line).Lines } else { 0 }
    $seed = ('LAB' + ('{0:d7}' -f $i)).Substring(0, 10).ToUpperInvariant()
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $code = 0
    try {
        & (Join-Path $PSScriptRoot 'run_official_autoslay.ps1') `
            -GameDir $GameDir -Seed $seed -StopAfterAct 0 -BossLab `
            -AgentScript $AgentScript -AgentMaxCombats 1 -AgentSimulations $AgentSimulations `
            -TimeoutSeconds $TimeoutSeconds -Visible:$Visible `
            -LogFile "$prefix`_mod.log" -ResultFile "$prefix`_result.json" `
            -AgentTrace "$prefix`_agent.jsonl" -AgentErrorLog "$prefix`_agent.err" `
            -MapFile "$prefix`_map.json" `
            -ExtraGameArgs @("--bosslab-plan=$PlanAbs", "--bosslab-trial=$i", "--bosslab-out=$OutFile")
    } catch {
        $code = 1
        $failures += , "trial $i : $_"
        Write-Output "TRIAL $i wrapper failed: $_"
    }
    $sw.Stop()
    $endLines = if (Test-Path -LiteralPath $OutFile) { (Get-Content -LiteralPath $OutFile | Measure-Object -Line).Lines } else { 0 }
    $line = if ($endLines -gt $startLines) { Get-Content -LiteralPath $OutFile | Select-Object -Last 1 } else { '' }
    if ($endLines -le $startLines) {
        $code = 2
        $failures += , "trial $i wrote no result line (exit $code); partial logs at $prefix"
    }
    Write-Output ("RESULT trial={0} exit={1} secs={2} {3}" -f $i, $code, [int]$sw.Elapsed.TotalSeconds, $line)
    if ($code -ne 0 -and -not $ContinueOnFailure) { break }
}

Write-Output "BOSSLAB DONE out=$OutDir lines=$(if (Test-Path -LiteralPath $OutFile) { (Get-Content -LiteralPath $OutFile | Measure-Object -Line).Lines } else { 0 }) failures=$($failures.Count)"
foreach ($failure in $failures) { Write-Output "FAIL $failure" }
Set-Content -LiteralPath (Join-Path $OutDir 'failures.txt') -Value (($failures -join "`n") + "`n")
if ($failures.Count) { exit 1 }
exit 0
