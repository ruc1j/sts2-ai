$ErrorActionPreference = 'Continue'
pwsh -NoProfile -File ./run_official_autoslay.ps1 -Seed FV2EVHXLCW -StopAfterAct 2 -AgentScript ./official_agent.py -AgentMaxCombats 100 -UnlockIroncladEpochs -TimeoutSeconds 600 -ResultFile ./data/act2_sim7_result.json -AgentTrace ./data/act2_sim7_visible_trace.jsonl -AgentErrorLog ./data/act2_sim7_errors.log > ./data/act2_sim7_runner.log 2>&1
Write-Output "EXIT=$LASTEXITCODE"
Write-Output '===RESULT==='
if (Test-Path ./data/act2_sim7_result.json) { Get-Content ./data/act2_sim7_result.json | Select-Object -First 30 }
Write-Output '===TRACE END==='
if (Test-Path ./data/act2_sim7_visible_trace.jsonl) { Get-Content ./data/act2_sim7_visible_trace.jsonl -Tail 3 }
