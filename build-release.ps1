# Builds the distributable package:
#   dist\dj-tags\                      (dj-tags.exe + _internal + license files)
#   dist\dj-tags-<version>-win64.zip   (the file to publish)
#
# Usage (from this folder):  .\build-release.ps1
# Refuses to build while app\about.py / README.md still contain placeholder values;
# pass -AllowPlaceholders only for a local test build that will not be published.

param([switch]$AllowPlaceholders)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = ".\.venv\Scripts\python.exe"
$dist = "dist\dj-tags"

$placeholders = Select-String -Path "app\about.py", "README.md" -Pattern "YOUR_HANDLE|YOUR_ACCOUNT"
if ($placeholders) {
    $placeholders | ForEach-Object { Write-Host "  placeholder: $($_.Path):$($_.LineNumber): $($_.Line.Trim())" }
    if (-not $AllowPlaceholders) {
        throw "Replace YOUR_HANDLE / YOUR_ACCOUNT in app\about.py and README.md before building a release."
    }
    Write-Warning "Building with placeholder values (-AllowPlaceholders). Do not publish this build."
}

$version = (Select-String -Path "app\about.py" -Pattern '^VERSION = "(.+)"').Matches[0].Groups[1].Value

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name dj-tags `
    --paths . `
    app\main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

# License texts must travel with the binaries.
Copy-Item LICENSE, README.md, THIRD-PARTY-NOTICES.md $dist -Force
Copy-Item licenses "$dist\licenses" -Recurse -Force

$zip = "dist\dj-tags-$version-win64.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $dist -DestinationPath $zip

Write-Host "Built: $dist\dj-tags.exe"
Write-Host "Package: $zip"
