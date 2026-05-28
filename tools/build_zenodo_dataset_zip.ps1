param(
    [string]$DatasetVersion = "1.1.1",

    [string]$OutputZip = "$env:TEMP\evbayiro_irr_benchmark_dataset_v1.1.1.zip"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$releaseRoot = Join-Path $env:TEMP "evbayiro_irr_benchmark_dataset_v$DatasetVersion"

if (Test-Path -LiteralPath $releaseRoot) {
    Remove-Item -LiteralPath $releaseRoot -Recurse -Force
}
if (Test-Path -LiteralPath $OutputZip) {
    Remove-Item -LiteralPath $OutputZip -Force
}

New-Item -ItemType Directory -Path $releaseRoot | Out-Null
New-Item -ItemType Directory -Path (Join-Path $releaseRoot "benchmarks") | Out-Null
New-Item -ItemType Directory -Path (Join-Path $releaseRoot "benchmarks\results") | Out-Null

$rootFiles = @(
    "README.md",
    "LICENSE",
    "pyproject.toml"
)

$benchmarkFiles = @(
    "DATASET_README.md",
    "DATA_DICTIONARY.md",
    "requirements.txt",
    "sourced_cases.csv",
    "company_proxy_cases.csv",
    "paper_benchmark.py",
    "sourced_benchmark.py",
    "expanded_benchmark.py",
    "company_proxy_cases.py",
    "summarize_expanded_results.py",
    "compare_solvers.py"
)

$resultFiles = @(
    "sourced_benchmark_expanded_methods.csv",
    "sourced_benchmark_expanded_methods_summary.csv",
    "expanded_benchmark.csv",
    "expanded_benchmark_summary.csv",
    "expanded_benchmark_group_summary.csv",
    "expanded_benchmark_case_mix.csv"
)

foreach ($file in $rootFiles) {
    Copy-Item -LiteralPath (Join-Path $repoRoot $file) -Destination $releaseRoot
}

foreach ($file in $benchmarkFiles) {
    Copy-Item -LiteralPath (Join-Path $repoRoot "benchmarks\$file") -Destination (Join-Path $releaseRoot "benchmarks")
}

foreach ($file in $resultFiles) {
    Copy-Item -LiteralPath (Join-Path $repoRoot "benchmarks\results\$file") -Destination (Join-Path $releaseRoot "benchmarks\results")
}

Compress-Archive -Path (Join-Path $releaseRoot "*") -DestinationPath $OutputZip -Force

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($OutputZip)
try {
    $entryCount = $zip.Entries.Count
    $resultCsvCount = @($zip.Entries | Where-Object { $_.FullName -like "benchmarks\results\*.csv" }).Count
    $oldResultCount = @(
        $zip.Entries | Where-Object {
            $_.FullName -in @(
                "benchmarks\results\paper_benchmark.csv",
                "benchmarks\results\paper_benchmark_summary.csv",
                "benchmarks\results\sourced_benchmark.csv",
                "benchmarks\results\sourced_benchmark_summary.csv"
            )
        }
    ).Count
} finally {
    $zip.Dispose()
}

Write-Host "Built dataset ZIP: $OutputZip"
Write-Host "Entries: $entryCount"
Write-Host "Current result CSVs: $resultCsvCount"
Write-Host "Superseded result CSVs: $oldResultCount"
