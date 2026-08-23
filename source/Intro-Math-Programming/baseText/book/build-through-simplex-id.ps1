param(
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"
$bookRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$baseTextRoot = [System.IO.Path]::GetFullPath(
    (Split-Path -Parent $bookRoot)
)
$externalSourcesRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $baseTextRoot "external-sources")
)
$laneRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $bookRoot "..\..\..\..")
)

if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $laneRoot "output\through-simplex-pdf"
}
$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
[System.IO.Directory]::CreateDirectory($OutputDirectory) | Out-Null

$env:SOURCE_DATE_EPOCH = "1787270400" # 2026-08-21T00:00:00Z
$env:FORCE_SOURCE_DATE = "1"

# The admitted upstream Matplotlib PDF contains a Type 3 font.  Repaint that
# single small figure at 600 dpi into a deterministic bitmap-wrapped PDF in a
# fixed lane-local TEXINPUTS shadow.  The fixed path prevents pdfTeX from
# serializing the chosen build-output directory into otherwise identical PDFs,
# while keeping the source asset untouched and every book font scalable.
$fontSafeAssetRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $laneRoot "output\through-simplex-build-assets\texinputs")
)
$fontSafeAssetDirectory = Join-Path $fontSafeAssetRoot `
    "foundationsAppliedMathematicsLabs\Volume2\Simplex\figures"
[System.IO.Directory]::CreateDirectory($fontSafeAssetDirectory) | Out-Null
$sourcePolytope = [System.IO.Path]::GetFullPath(
    (Join-Path $externalSourcesRoot `
        "foundationsAppliedMathematicsLabs\Volume2\Simplex\figures\feasiblePolytope.pdf")
)
$fontSafePolytope = Join-Path $fontSafeAssetDirectory "feasiblePolytope.pdf"
$expectedSourcePolytopeHash = `
    "22244C474C080829C93A599D4C95F0140210CDC4FB47D03B9CA63544726D02FE"
$actualSourcePolytopeHash = `
    (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePolytope).Hash
if ($actualSourcePolytopeHash -cne $expectedSourcePolytopeHash) {
    throw "Unexpected feasiblePolytope.pdf source hash: $actualSourcePolytopeHash"
}
& mutool draw -q -F pclm -r 600 -o $fontSafePolytope $sourcePolytope
$mutoolExitCode = $LASTEXITCODE
$expectedFontSafePolytopeHash = `
    "C925B6EAF59EFAC328B98B264A44805EF9EA6F95B8F0EDAF9E88485A936C5FBA"
if (-not (Test-Path -LiteralPath $fontSafePolytope)) {
    throw "mutool did not create the font-safe replay"
}
$actualFontSafePolytopeHash = `
    (Get-FileHash -Algorithm SHA256 -LiteralPath $fontSafePolytope).Hash
# The 2017 Matplotlib source contains a duplicate /Group dictionary entry, so
# require both successful rendering and the exact pinned output bytes.
if (($mutoolExitCode -ne 0) -or
    ($actualFontSafePolytopeHash -cne $expectedFontSafePolytopeHash)) {
    throw "Unexpected font-safe replay (exit $mutoolExitCode, hash $actualFontSafePolytopeHash)"
}

$pathSeparator = [System.IO.Path]::PathSeparator
$env:TEXINPUTS = [string]::Join(
    $pathSeparator,
    @($fontSafeAssetRoot, $baseTextRoot, $externalSourcesRoot, "")
)

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
        "book1-through-simplex-id.tex"
    if ($LASTEXITCODE -ne 0) {
        throw "latexmk failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
