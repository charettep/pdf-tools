$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..")

python (Join-Path $RepoRoot "scripts\\validate-metadata.py")

$meta = Get-Content -Path (Join-Path $RepoRoot "build\\metadata.json") -Raw | ConvertFrom-Json

$AppName = $meta.app_name
$AppDisplayName = $meta.app_display_name
$AppVersion = $meta.app_version
$AppPublisher = $meta.app_publisher
$versionParts = $AppVersion -split '\.'
while ($versionParts.Count -lt 4) { $versionParts += '0' }
$FileVersionTuple = ($versionParts[0..3] -join ', ')

python -m pip install -r (Join-Path $RepoRoot "requirements.txt") -r (Join-Path $RepoRoot "requirements-dev.txt")

$versionFile = Join-Path $env:TEMP "pdf-tools-version-info.txt"
@"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($FileVersionTuple),
    prodvers=($FileVersionTuple),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', '$AppPublisher'),
          StringStruct('FileDescription', '$AppDisplayName'),
          StringStruct('FileVersion', '$AppVersion'),
          StringStruct('InternalName', '$AppName'),
          StringStruct('OriginalFilename', '$($AppName).exe'),
          StringStruct('ProductName', '$AppDisplayName'),
          StringStruct('ProductVersion', '$AppVersion'),
          StringStruct('LegalCopyright', 'Copyright (c) $AppPublisher')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [0x0409, 1200])])
  ]
)
"@ | Set-Content -Path $versionFile -Encoding UTF8

New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot "dist") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot "build\\pyinstaller") | Out-Null

$legacySpec = Join-Path $PSScriptRoot "$AppName.spec"
if (Test-Path $legacySpec) {
    Remove-Item -Path $legacySpec -Force -ErrorAction SilentlyContinue
}

Push-Location $RepoRoot
pyinstaller `
  --noconfirm `
  --onefile `
  --name $AppName `
  --windowed `
  --version-file $versionFile `
  --distpath "dist" `
  --workpath "build\\pyinstaller" `
  --specpath "build\\pyinstaller" `
  "src\\pdf_tools\\main.py"
Pop-Location

Remove-Item -Path $versionFile -ErrorAction SilentlyContinue

Write-Host "Build complete. Executable: dist/$AppName.exe"

$exePath = Join-Path $RepoRoot ("dist\\{0}.exe" -f $meta.app_name)
if (-not (Test-Path $exePath)) {
    throw "Expected EXE not found at: $exePath"
}

$iscc = Get-Command ISCC -ErrorAction SilentlyContinue
$minInnoVersion = [Version]"6.0.0"
$canBuildInstaller = $true

if (-not $iscc) {
    Write-Warning "ISCC.exe not found. Install Inno Setup and ensure ISCC is on PATH."
    $canBuildInstaller = $false
} else {
    $helpText = & $iscc.Source "/?"
    $versionMatch = ($helpText | Select-String -Pattern "Inno Setup\s+(\d+\.\d+(\.\d+)?)").Matches
    if ($versionMatch.Count -gt 0) {
        $versionText = $versionMatch[0].Groups[1].Value
        $installedVersion = [Version]$versionText
        if ($installedVersion -lt $minInnoVersion) {
            Write-Warning "Inno Setup $installedVersion found, but $minInnoVersion or newer is recommended."
            $canBuildInstaller = $false
        }
    } else {
        Write-Warning "Unable to determine Inno Setup version. Continuing without version validation."
    }
}

if (-not $canBuildInstaller) {
    while ($true) {
        $choice = Read-Host "Build only the standalone .exe and skip the installer? (Y/n)"
        if ([string]::IsNullOrWhiteSpace($choice) -or $choice.Trim().ToLower() -eq "y") {
            Write-Host "Skipping installer build."
            exit 0
        }
        if ($choice.Trim().ToLower() -eq "n") {
            Write-Host "Exiting without building the installer."
            exit 0
        }
        Write-Host "Invalid Response. Build only the standalone .exe and skip the installer? (Y/n)"
    }
}

& $iscc.Source `
  /DMyAppExePath="$exePath" `
  /DMyAppName="$($meta.app_display_name)" `
  /DMyAppExeName="$($meta.app_exe_name)" `
  /DMyAppPublisher="$($meta.app_publisher)" `
  /DMyAppVersion="$($meta.app_version)" `
  /DMyAppSetupBaseName="$($meta.app_setup_base_name)" `
  (Join-Path $PSScriptRoot "installer.iss")

Write-Host "Installer created in dist/ ($($meta.app_setup_base_name).exe)"
