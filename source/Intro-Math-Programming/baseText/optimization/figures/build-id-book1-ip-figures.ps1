param(
    [string]$BuildDirectory = ""
)

$ErrorActionPreference = "Stop"
$figureRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$laneRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $figureRoot "..\..\..\..\..")
)

if ([string]::IsNullOrWhiteSpace($BuildDirectory)) {
    $BuildDirectory = Join-Path $laneRoot "output\ip-figure-build"
}
$BuildDirectory = [System.IO.Path]::GetFullPath($BuildDirectory)
[System.IO.Directory]::CreateDirectory($BuildDirectory) | Out-Null

$env:SOURCE_DATE_EPOCH = "1787270400" # 2026-08-21T00:00:00Z
$env:FORCE_SOURCE_DATE = "1"

$figures = @(
    [pscustomobject]@{
        Source = Join-Path $figureRoot "figures-static\facility-location.tex"
        Job = "facility-location"
        Destination = Join-Path $figureRoot "figures-static\facility-location.pdf"
    },
    [pscustomobject]@{
        Source = Join-Path $figureRoot "figures-source\tikz\Illustration1.tex"
        Job = "tikz-Illustration1"
        Destination = Join-Path $figureRoot "figures-source\tikz-Illustration1.pdf"
    },
    [pscustomobject]@{
        Source = Join-Path $figureRoot "figures-source\tikz\Illustration2.tex"
        Job = "tikz-Illustration2"
        Destination = Join-Path $figureRoot "figures-source\tikz-Illustration2.pdf"
    },
    [pscustomobject]@{
        Source = Join-Path $figureRoot "figures-source\tikz\Illustration3.tex"
        Job = "tikz-Illustration3"
        Destination = Join-Path $figureRoot "figures-source\tikz-Illustration3.pdf"
    }
)

$records = @()
foreach ($figure in $figures) {
    if (-not (Test-Path -LiteralPath $figure.Source)) {
        throw "Missing localized figure source: $($figure.Source)"
    }

    & pdflatex `
        -interaction=nonstopmode `
        -halt-on-error `
        -file-line-error `
        "-jobname=$($figure.Job)" `
        "-output-directory=$BuildDirectory" `
        $figure.Source | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "pdflatex failed for $($figure.Job) with exit code $LASTEXITCODE"
    }

    $builtPdf = Join-Path $BuildDirectory "$($figure.Job).pdf"
    if (-not (Test-Path -LiteralPath $builtPdf)) {
        throw "Expected figure output is absent: $builtPdf"
    }
    Copy-Item -LiteralPath $builtPdf -Destination $figure.Destination

    $records += [pscustomobject]@{
        job = $figure.Job
        source = [System.IO.Path]::GetRelativePath($laneRoot, $figure.Source)
        source_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $figure.Source).Hash.ToLowerInvariant()
        destination = [System.IO.Path]::GetRelativePath($laneRoot, $figure.Destination)
        bytes = (Get-Item -LiteralPath $figure.Destination).Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $figure.Destination).Hash.ToLowerInvariant()
    }
}

$records | ConvertTo-Json -Depth 4
