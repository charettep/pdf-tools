param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("venv", "install", "run", "validate", "build")]
    [string]$Task
)

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..")

switch ($Task) {
    "venv" {
        python -m venv (Join-Path $RepoRoot ".venv")
    }
    "install" {
        python -m pip install -r (Join-Path $RepoRoot "requirements.txt") -r (Join-Path $RepoRoot "requirements-dev.txt")
        python -m pip install -e $RepoRoot
    }
    "run" {
        python -m pdf_tools
    }
    "validate" {
        python (Join-Path $RepoRoot "scripts\\validate-metadata.py")
    }
    "build" {
        & (Join-Path $RepoRoot "scripts\\windows\\build-win.ps1")
    }
}
