param(
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"
$bookRoot = $PSScriptRoot
$baseTextRoot = Split-Path -Parent $bookRoot
$laneRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $bookRoot "..\..\..\..")
)

if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $laneRoot "output\through-ch03-pdf"
}
$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
[System.IO.Directory]::CreateDirectory($OutputDirectory) | Out-Null

$env:SOURCE_DATE_EPOCH = "1787270400" # 2026-08-21T00:00:00Z
$env:FORCE_SOURCE_DATE = "1"
$env:TEXINPUTS = "$baseTextRoot;"

Push-Location -LiteralPath $bookRoot
try {
    & latexmk `
        -g `
        -pdf `
        -interaction=nonstopmode `
        -halt-on-error `
        -file-line-error `
        -recorder `
        "-outdir=$OutputDirectory" `
        "book1-through-ch03-id.tex"
    if ($LASTEXITCODE -ne 0) {
        throw "latexmk failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
