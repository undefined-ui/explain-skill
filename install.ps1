# Install the /explain skill for Claude Code on Windows, with video mode ready to go.
#
#   irm https://raw.githubusercontent.com/undefined-ui/explain-skill/main/install.ps1 | iex
#
# Text, diagram and HTML modes only (skip Manim + voice models, ~400 MB):
#   $env:EXPLAIN_NO_VIDEO = 1; irm https://raw.githubusercontent.com/undefined-ui/explain-skill/main/install.ps1 | iex

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$Repo = 'undefined-ui/explain-skill'
$Branch = if ($env:EXPLAIN_BRANCH) { $env:EXPLAIN_BRANCH } else { 'main' }
$SkillsDir = if ($env:CLAUDE_SKILLS_DIR) { $env:CLAUDE_SKILLS_DIR } else { Join-Path $HOME '.claude\skills' }
$NoVideo = [bool]$env:EXPLAIN_NO_VIDEO -or ($args -contains '-NoVideo')

function Say($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }

# Use this checkout when run as .\install.ps1, else download the repo.
$here = if ($PSScriptRoot) { $PSScriptRoot } else { $null }
if ($here -and (Test-Path (Join-Path $here 'skills\explain\SKILL.md'))) {
    $src = $here
} else {
    $tmp = Join-Path ([IO.Path]::GetTempPath()) ("explain-skill-" + [guid]::NewGuid())
    New-Item -ItemType Directory -Path $tmp | Out-Null
    Say "Downloading $Repo ($Branch)"
    $zip = Join-Path $tmp 'repo.zip'
    Invoke-WebRequest "https://codeload.github.com/$Repo/zip/refs/heads/$Branch" -OutFile $zip -UseBasicParsing
    Expand-Archive $zip -DestinationPath $tmp
    $src = (Get-ChildItem $tmp -Directory | Select-Object -First 1).FullName
}

$dest = Join-Path $SkillsDir 'explain'
Say "Installing skill to $dest"
New-Item -ItemType Directory -Force -Path $SkillsDir | Out-Null
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
Copy-Item -Recurse (Join-Path $src 'skills\explain') $dest

if (-not $NoVideo) {
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    $localUv = Join-Path $HOME '.local\bin\uv.exe'
    if (-not $uv -and -not (Test-Path $localUv)) {
        Say 'Installing uv (Python manager, https://docs.astral.sh/uv/)'
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    }
    $env:Path = "$(Join-Path $HOME '.local\bin');$env:Path"
    Say 'Setting up video mode (Manim + Kokoro/Piper voices)'
    # uv reports progress on stderr. Windows PowerShell turns redirected stderr into errors, so relax 'Stop' here.
    $ErrorActionPreference = 'Continue'
    & uv run --no-project --python 3.12 (Join-Path $dest 'scripts\setup.py')
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($code -ne 0) { throw "Video setup failed (exit $code). Text, diagram and HTML modes still work." }
}

if ($tmp -and (Test-Path $tmp)) { Remove-Item -Recurse -Force $tmp }

Write-Host @'

Done. Restart Claude Code (or start a new session), then try:

  /explain how TCP handshakes work diagram
  /explain softmax temperature html
  /explain why the determinant is an area video

Optional: $env:ELEVENLABS_API_KEY = '...' for ElevenLabs narration (free local voices are used otherwise).
'@
