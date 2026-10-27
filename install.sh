#!/usr/bin/env bash
# Install the /explain skill for Claude Code, with video mode ready to go.
#
#   curl -fsSL https://raw.githubusercontent.com/undefined-ui/explain-skill/main/install.sh | bash
#
# Options (after "bash -s --"):
#   --no-video     text, diagram and HTML modes only (skip Manim + voice models, ~400 MB)
#   --dir <path>   skills folder (default: ~/.claude/skills)
set -euo pipefail

REPO="undefined-ui/explain-skill"
BRANCH="${EXPLAIN_BRANCH:-main}"
SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
VIDEO=1

while [ $# -gt 0 ]; do
  case "$1" in
    --no-video) VIDEO=0 ;;
    --dir) SKILLS_DIR="$2"; shift ;;
    -h|--help) sed -n '2,10p' "$0" 2>/dev/null || true; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

# Use this checkout when run as ./install.sh, else download the repo.
here="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
if [ -n "$here" ] && [ -f "$here/skills/explain/SKILL.md" ]; then
  src="$here"
else
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  say "Downloading $REPO ($BRANCH)"
  curl -fsSL "https://codeload.github.com/$REPO/tar.gz/refs/heads/$BRANCH" | tar -xz -C "$tmp"
  src="$(find "$tmp" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
fi

dest="$SKILLS_DIR/explain"
say "Installing skill to $dest"
mkdir -p "$SKILLS_DIR"
rm -rf "$dest"
cp -R "$src/skills/explain" "$dest"

if [ "$VIDEO" = 1 ]; then
  if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
    say "Installing uv (Python manager, https://docs.astral.sh/uv/)"
    curl -LsSf https://astral.sh/uv/install.sh | sh
  fi
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  say "Setting up video mode (Manim + Kokoro/Piper voices)"
  uv run --no-project --python 3.12 "$dest/scripts/setup.py"
fi

cat <<EOF

Done. Restart Claude Code (or start a new session), then try:

  /explain how TCP handshakes work diagram
  /explain softmax temperature html
  /explain why the determinant is an area video

Optional: export ELEVENLABS_API_KEY=... for ElevenLabs narration (free local voices are used otherwise).
EOF
