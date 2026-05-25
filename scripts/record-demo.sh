#!/usr/bin/env bash
# Record a clean asciinema demo of rag-poison-lab.
#
# Follows the "hybrid" demo flow:
#   1. Show that ANTHROPIC_API_KEY is set (first 12 chars only, to prove env
#      is wired up without leaking the key).
#   2. Run the single-model `attack` command live, so the viewer sees the
#      progress bars + per-attack landings stream in.
#   3. Cat the head of a pre-generated `compare` report so the viewer also
#      sees the multi-model matrix output without having to wait for the
#      full 4-model run (~3 minutes).
#
# If reports/comparison-naive.md doesn't exist yet, this script runs
# `compare` once first to generate it.
#
# Output: demo.cast in the repo root (configurable via $1).
# Idle pauses longer than 2 seconds get compressed to 2s on playback so the
# recording stays watchable.
#
# Usage:
#   scripts/record-demo.sh              # writes ./demo.cast
#   scripts/record-demo.sh my-demo.cast # writes ./my-demo.cast

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CAST_FILE="${1:-demo.cast}"

if ! command -v asciinema >/dev/null 2>&1; then
    echo "error: asciinema not on PATH. Install with: sudo pacman -S asciinema" >&2
    exit 1
fi

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    echo "warning: ANTHROPIC_API_KEY not set in this shell."
    echo "         The demo will record an error message instead of an attack run."
    echo "         Set it and re-run for a clean demo."
    sleep 2
fi

# Pre-flight: make sure reports/comparison-naive.md exists so the demo can
# cat it at the end. If not, run compare once.
if [[ ! -f reports/comparison-naive.md ]]; then
    echo "No reports/comparison-naive.md yet. Running compare first..."
    uv run rag-poison-lab compare
    echo
fi

# Build the inner script that runs inside the recording.
# `zsh -f` skips rc files (no fastfetch, no welcome banner) but we set a
# clean prompt so the recording still looks polished.
INNER_SCRIPT=$(mktemp --suffix=.zsh)
trap "rm -f $INNER_SCRIPT" EXIT

cat > "$INNER_SCRIPT" << 'EOF'
PS1='%F{green}❯%f '
clear

echo '❯ echo "$ANTHROPIC_API_KEY" | head -c 12; echo'
echo "$ANTHROPIC_API_KEY" | head -c 12; echo
sleep 1
echo

echo '❯ uv run rag-poison-lab attack'
uv run rag-poison-lab attack
sleep 1
echo

echo '❯ # Full 4-model comparison was generated earlier. Showing the matrix:'
sleep 0.5
echo '❯ head -55 reports/comparison-naive.md'
head -55 reports/comparison-naive.md
sleep 2
EOF

chmod +x "$INNER_SCRIPT"

echo "Recording to $CAST_FILE"
echo "(idle pauses > 2s are compressed on playback)"
echo

asciinema rec --idle-time-limit 2 --overwrite \
    --command "zsh -f $INNER_SCRIPT" \
    "$CAST_FILE"

echo
echo "Done. $CAST_FILE saved."
echo
echo "Preview locally:  asciinema play $CAST_FILE"
echo "Upload + share:   asciinema upload $CAST_FILE"
echo
echo "After upload, add to README.md somewhere near the top:"
echo "    [![asciicast](https://asciinema.org/a/<id>.svg)](https://asciinema.org/a/<id>)"
