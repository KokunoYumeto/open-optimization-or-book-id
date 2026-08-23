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
    $OutputDirectory = Join-Path $laneRoot "output\unit1-pdf"
}
$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
[System.IO.Directory]::CreateDirectory($OutputDirectory) | Out-Null

# Freeze PDF metadata and trailer generation at the edition boundary.
$env:SOURCE_DATE_EPOCH = "1787184000" # 2026-08-20T00:00:00Z
$env:FORCE_SOURCE_DATE = "1"

# Upstream graphics are addressed as Figures/... even though the controller
# lives one level below baseText.  The trailing separator retains TeX defaults.
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
        "book1-unit1-id.tex"
    if ($LASTEXITCODE -ne 0) {
        throw "latexmk failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
