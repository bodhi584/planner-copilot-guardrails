# Runs the evaluation of eval/PROTOCOL.md on one Windows PC with an NVIDIA GPU (tested: RTX 3060 12 GB).
# Every run is resumable: stop it any time and start the same stage again.
#
#   powershell -ExecutionPolicy Bypass -File eval\run_windows.ps1 setup      # once: Ollama, JDK 17, Python env, JaamSim, models
#   powershell -ExecutionPolicy Bypass -File eval\run_windows.ps1 smoke      # 1 question per case, setup C, qwen (about 2 min)
#   powershell -ExecutionPolicy Bypass -File eval\run_windows.ps1 T1         # main: 3 models x A,B,C x 40 test questions
#   powershell -ExecutionPolicy Bypass -File eval\run_windows.ps1 T2         # repeats: qwen, temperature 0.7, seeds 1-3
#   powershell -ExecutionPolicy Bypass -File eval\run_windows.ps1 T3         # ablation: qwen, C with one check off at a time
#   powershell -ExecutionPolicy Bypass -File eval\run_windows.ps1 D4         # llama on the 80 development questions
#   powershell -ExecutionPolicy Bypass -File eval\run_windows.ps1 grade      # grade every answers file
param([Parameter(Mandatory = $true)][ValidateSet("setup", "smoke", "T1", "T2", "T3", "D4", "grade")][string]$Stage)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:A1_CACHE_ONLY = "1"   # A1 answers come from the stored runs of the four published scenarios
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Out = "eval\results\test"
$Models = @("qwen2.5:7b-instruct", "llama3.1:8b", "gemma2:9b")
$Base = "http://localhost:11434/v1"
$Test = @(Get-ChildItem cases\*\questions_test.csv | ForEach-Object { $_.FullName })
$Dev = @(Get-ChildItem cases\*\questions.csv | ForEach-Object { $_.FullName })

function Need($cmd) { return -not (Get-Command $cmd -ErrorAction SilentlyContinue) }
function Slug($m) { return ($m -replace "[:.]", "_") }
function Run([string[]]$a) { & $Py -m eval.run --base-url $Base @a; if ($LASTEXITCODE) { throw "eval.run failed" } }

switch ($Stage) {
  "setup" {
    if (Need "ollama") { winget install -e --id Ollama.Ollama --accept-source-agreements --accept-package-agreements }
    if (Need "javac") { winget install -e --id EclipseAdoptium.Temurin.17.JDK --accept-source-agreements --accept-package-agreements }
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not (Test-Path .venv)) { if (Need "uv") { python -m venv .venv } else { uv venv .venv --python 3.12 } }
    if (Need "uv") { & $Py -m pip install -q ".[all]" } else { uv pip install --python $Py -q ".[all]" }
    # JaamSim for A2 (same commit as cases/A2_sme/setup.sh)
    $J = "cases\A2_sme\jaamsim"
    if (-not (Test-Path $J)) { git clone -q https://github.com/jaamsim/jaamsim $J; git -C $J checkout -q efe404c48e938a372be1dca56ac552976776b28a }
    if (-not (Test-Path "$J\classes")) {
      Get-ChildItem "$J\src\main\java" -Recurse -Filter *.java | ForEach-Object { $_.FullName } | Set-Content "$J\srcs.txt" -Encoding ascii
      javac -nowarn -encoding UTF-8 -d "$J\classes" -cp "$J\jar\jogl-all.jar;$J\jar\gluegen-rt.jar" "@$J\srcs.txt"
    }
    foreach ($m in $Models) { ollama pull $m }
    & $Py -m pytest -q
    & $Py cases\A2_sme\reproduce.py
  }
  "smoke" {
    $q = @(foreach ($f in $Test) { $f })
    Run (@("--questions") + $q + @("--arms", "C", "--model", $Models[0], "--limit", "4", "--out", "$Out\smoke.csv"))
  }
  "T1" { foreach ($m in $Models) { Run (@("--questions") + $Test + @("--arms", "A,B,C", "--model", $m, "--out", "$Out\T1_$(Slug $m).csv")) } }
  "T2" { Run (@("--questions") + $Test + @("--arms", "A,B,C", "--model", $Models[0], "--temperature", "0.7", "--seed-base", "1", "--repeats", "3", "--out", "$Out\T2_qwen_repeats.csv")) }
  "T3" {
    foreach ($c in @("scope", "units", "validity", "adaptive_reps", "paired", "value_check")) {
      Run (@("--questions") + $Test + @("--arms", "C", "--model", $Models[0], "--off", $c, "--label", "-off_$c", "--out", "$Out\T3_qwen_ablation.csv"))
    }
  }
  "D4" { Run (@("--questions") + $Dev + @("--arms", "A,B,C", "--model", $Models[1], "--out", "eval\results\run6_llama3_1_8b_dev.csv")) }
  "grade" {
    $all = @(Get-ChildItem cases\*\questions*.csv | ForEach-Object { $_.FullName })
    foreach ($a in Get-ChildItem "$Out\*.csv", "eval\results\run6_*.csv" -Exclude "*_graded.csv") {
      & $Py eval\grade_all.py $a.FullName @all | Set-Content ($a.FullName -replace "\.csv$", "_graded.csv") -Encoding utf8
    }
    & $Py eval\analyse.py
  }
}
