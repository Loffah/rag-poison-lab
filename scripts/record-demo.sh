#!/usr/bin/env bash
# Record a clean asciinema demo of rag-poison-lab.
#
# Follows the contrast-led demo flow:
#   1. Show env keys are set (first chars only, to prove without leaking).
#   2. Live `attack` against Claude Opus 4.7 (frontier). Most attacks
#      defeated, demonstrates the model recognising injection attempts.
#   3. Same `attack` against Llama 3.3 70B on Groq (open-weight). Most
#      attacks land, demonstrating the comparative-measurement story.
#   4. Cat the head of a pre-generated `compare` report so the viewer
#      sees the multi-model matrix without waiting for the full 4-model
#      run (~3 minutes).
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
    echo "         The Claude part of the demo will record an error instead of an attack run."
    sleep 2
fi

if [[ -z "${OPENAI_API_KEY:-}" || -z "${OPENAI_BASE_URL:-}" ]]; then
    echo "warning: OPENAI_API_KEY or OPENAI_BASE_URL not set."
    echo "         The Llama (Groq) part of the demo will record an error."
    echo "         Set both for the full contrast demo:"
    echo "           export OPENAI_API_KEY=gsk_your_groq_key"
    echo "           export OPENAI_BASE_URL=https://api.groq.com/openai/v1"
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

echo '❯ # Keys are set (showing first chars only):'
echo '❯ echo "$ANTHROPIC_API_KEY" | head -c 12; echo'
echo "$ANTHROPIC_API_KEY" | head -c 12; echo
echo '❯ echo "$OPENAI_API_KEY" | head -c 8; echo'
echo "$OPENAI_API_KEY" | head -c 8; echo
sleep 1
echo

echo '❯ # First: run the attack corpus against Claude Opus 4.7 (frontier model)'
sleep 0.5
echo '❯ uv run rag-poison-lab attack'
uv run rag-poison-lab attack
sleep 2
echo

echo '❯ # Now the same corpus against Llama 3.3 70B on Groq (open-weight, less safety RLHF)'
sleep 0.5
echo '❯ RAG_POISON_LAB_BACKEND=openai uv run rag-poison-lab attack'
RAG_POISON_LAB_BACKEND=openai uv run rag-poison-lab attack
sleep 2
echo

echo '❯ # Full 4-model comparison report from an earlier run:'
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
