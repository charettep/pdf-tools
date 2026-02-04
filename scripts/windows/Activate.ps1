$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..")
$ActivatePath = Join-Path $RepoRoot ".venv\\Scripts\\Activate.ps1"

if (-not (Test-Path $ActivatePath)) {
    Write-Host "Virtualenv not found at $ActivatePath"
    Write-Host "Create it first with: .\\scripts\\windows\\tasks.ps1 -Task venv"
    exit 1
}

& $ActivatePath
