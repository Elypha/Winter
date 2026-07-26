$ErrorActionPreference = 'Stop'

$project = Split-Path -Parent $PSScriptRoot
Push-Location $project
try {
    uv run pyinstaller --noconfirm --clean .\packaging\Winter.spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }

    Copy-Item `
        -LiteralPath (Join-Path $project 'config.yaml') `
        -Destination (Join-Path $project 'dist\Winter\config.yaml') `
        -Force

    $artifactDirectory = Join-Path $project 'artifacts'
    New-Item -ItemType Directory -Path $artifactDirectory -Force | Out-Null
    $archive = Join-Path $artifactDirectory 'Winter-windows-x64.zip'
    Compress-Archive `
        -LiteralPath (Join-Path $project 'dist\Winter') `
        -DestinationPath $archive `
        -CompressionLevel Optimal `
        -Force
    Write-Output $archive
}
finally {
    Pop-Location
}
