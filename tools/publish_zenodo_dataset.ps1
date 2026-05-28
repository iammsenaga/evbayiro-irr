param(
    [Parameter(Mandatory = $true)]
    [string]$DatasetZip,

    [Parameter(Mandatory = $true)]
    [string]$OutputJson,

    [string]$ExistingDepositionId = "20435350",

    [string]$DatasetVersion = "1.1.1"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $DatasetZip)) {
    throw "Dataset ZIP not found: $DatasetZip"
}

Write-Host "Zenodo dataset publisher for Evbayiro-IRR"
Write-Host ""
Write-Host "Paste a Zenodo personal access token with deposit:write and deposit:actions scopes."
Write-Host "The token will be used only in this local PowerShell session."
Write-Host ""

$secureToken = Read-Host "Zenodo token" -AsSecureString
$tokenPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
try {
    $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPtr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPtr)
}

if ([string]::IsNullOrWhiteSpace($token)) {
    throw "No token was provided."
}

$headers = @{
    Authorization = "Bearer $token"
}

$description = @"
Benchmark dataset for comparing Evbayiro-IRR 0.1.1 with capital budgeting IRR interfaces and root-finding methods. Version $DatasetVersion expands the archived evidence by adding an Excel-style default-guess proxy, numpy_financial.irr, pyxirr.irr, and SEC Companyfacts firm-level free-cash-flow proxy cases. The dataset includes 49 public online sourced cases as primary external evidence, 50 SEC public-company proxy sequences as supplementary public-company evidence, and generated/manuscript-derived stress cases for reproducibility. It includes case metadata, solver outputs, convergence statuses, root-relation labels, decision-match fields, timing summaries, and regeneration scripts. SEC company proxy cases are firm-level accounting sequences, not disclosed project appraisal cash flows.
"@

$metadata = @{
    metadata = @{
        title = "Evbayiro-IRR Benchmark Dataset for Capital Budgeting Algorithm Comparison"
        upload_type = "dataset"
        description = $description
        creators = @(
            @{
                name = "Evbayiro, Osasenaga David"
            }
        )
        access_right = "open"
        license = "cc-by-4.0"
        publication_date = "2026-05-28"
        version = $DatasetVersion
        keywords = @(
            "Evbayiro-IRR",
            "IRR",
            "NPV",
            "capital budgeting",
            "required rate of return",
            "non-conventional cash flows",
            "multiple IRR",
            "Newton-Raphson",
            "Secant method",
            "benchmark dataset",
            "numpy-financial",
            "PyXIRR",
            "SEC Companyfacts"
        )
        related_identifiers = @(
            @{
                identifier = "10.5281/zenodo.20428636"
                relation = "isSupplementTo"
                scheme = "doi"
            }
        )
    }
}

Write-Host ""
if ([string]::IsNullOrWhiteSpace($ExistingDepositionId)) {
    Write-Host "Creating new Zenodo deposition..."
    $deposition = Invoke-RestMethod `
        -Method Post `
        -Uri "https://zenodo.org/api/deposit/depositions" `
        -Headers $headers `
        -ContentType "application/json" `
        -Body "{}"
} else {
    Write-Host "Creating new version from Zenodo deposition $ExistingDepositionId..."
    $newVersion = Invoke-RestMethod `
        -Method Post `
        -Uri "https://zenodo.org/api/deposit/depositions/$ExistingDepositionId/actions/newversion" `
        -Headers $headers

    if ($newVersion.links.latest_draft) {
        $deposition = Invoke-RestMethod `
            -Method Get `
            -Uri $newVersion.links.latest_draft `
            -Headers $headers
    } else {
        $deposition = $newVersion
    }

    if ($deposition.files) {
        Write-Host "Removing copied files from draft version..."
        foreach ($file in $deposition.files) {
            $deleteUri = $file.links.self
            if (-not $deleteUri -and $file.id) {
                $deleteUri = "https://zenodo.org/api/deposit/depositions/$($deposition.id)/files/$($file.id)"
            }
            if ($deleteUri) {
                Invoke-RestMethod `
                    -Method Delete `
                    -Uri $deleteUri `
                    -Headers $headers | Out-Null
            }
        }
    }
}

$bucketUrl = $deposition.links.bucket
$fileName = Split-Path -Leaf $DatasetZip
$uploadUrl = "$bucketUrl/$fileName"

Write-Host "Uploading dataset ZIP..."
Invoke-RestMethod `
    -Method Put `
    -Uri $uploadUrl `
    -Headers $headers `
    -ContentType "application/octet-stream" `
    -InFile $DatasetZip | Out-Null

Write-Host "Applying metadata..."
$metadataJson = $metadata | ConvertTo-Json -Depth 20
$updated = Invoke-RestMethod `
    -Method Put `
    -Uri "https://zenodo.org/api/deposit/depositions/$($deposition.id)" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $metadataJson

Write-Host ""
Write-Host "Ready to publish:"
Write-Host "Title: $($updated.metadata.title)"
Write-Host "Version: $($updated.metadata.version)"
Write-Host "Deposition ID: $($updated.id)"
Write-Host ""
Write-Host "Publishing is permanent on Zenodo."
$confirmation = Read-Host "Type PUBLISH to publish now"
if ($confirmation -ne "PUBLISH") {
    Write-Host "Not published. Draft deposition remains in Zenodo."
    $updated | ConvertTo-Json -Depth 20 | Out-File -LiteralPath $OutputJson -Encoding utf8
    exit 2
}

Write-Host "Publishing..."
$published = Invoke-RestMethod `
    -Method Post `
    -Uri "https://zenodo.org/api/deposit/depositions/$($deposition.id)/actions/publish" `
    -Headers $headers

$published | ConvertTo-Json -Depth 20 | Out-File -LiteralPath $OutputJson -Encoding utf8

Write-Host ""
Write-Host "Published successfully."
Write-Host "DOI: $($published.doi)"
if ($published.links.record_html) {
    Write-Host "Record: $($published.links.record_html)"
}
Write-Host "Saved response to: $OutputJson"
Read-Host "Press Enter to close"
