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
    echo "error: ANTHROPIC_API_KEY is not set." >&2
    echo "       Set it and re-run:" >&2
    echo "         export ANTHROPIC_API_KEY=sk-ant-..." >&2
    exit 1
fi

if [[ -z "${OPENAI_API_KEY:-}" || -z "${OPENAI_BASE_URL:-}" ]]; then
    echo "error: OPENAI_API_KEY or OPENAI_BASE_URL is not set." >&2
    echo "       The Groq half of the contrast demo would record a 401." >&2
    echo "       Set both for the full demo:" >&2
    echo "         export OPENAI_API_KEY=gsk_your_groq_key" >&2
    echo "         export OPENAI_BASE_URL=https://api.groq.com/openai/v1" >&2
    exit 1
fi

# Sanity-check the OpenAI base URL actually looks like Groq, not openai.com itself.
# If it points at OpenAI but the key is gsk_*, the OpenAI SDK will hit OpenAI's
# servers with a Groq key and 401 with a confusing 'platform.openai.com' message.
if [[ ! "$OPENAI_BASE_URL" =~ groq ]] && [[ "${OPENAI_API_KEY}" =~ ^gsk_ ]]; then
    echo "error: OPENAI_BASE_URL ($OPENAI_BASE_URL) doesn't look like a Groq endpoint" >&2
    echo "       but OPENAI_API_KEY starts with 'gsk_' (Groq's prefix)." >&2
    echo "       Set OPENAI_BASE_URL=https://api.groq.com/openai/v1 and re-run." >&2
    exit 1
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

echo '❯ # Trimmed corpus for the demo: direct_override, indirect_injection, markdown_exfil'
echo '❯ # (the families that produced landings in earlier runs)'
sleep 0.5
echo

echo '❯ # First: run against Claude Opus 4.7 (frontier model)'
sleep 0.5
echo '❯ uv run rag-poison-lab attack --family direct_override,indirect_injection,markdown_exfil'
uv run rag-poison-lab attack --family direct_override,indirect_injection,markdown_exfil
sleep 2
echo

echo '❯ # Now the same trimmed corpus against Llama 3.3 70B on Groq (open-weight)'
sleep 0.5
echo '❯ RAG_POISON_LAB_BACKEND=openai uv run rag-poison-lab attack --family direct_override,indirect_injection,markdown_exfil'
RAG_POISON_LAB_BACKEND=openai uv run rag-poison-lab attack --family direct_override,indirect_injection,markdown_exfil
sleep 2
echo

echo '❯ # Full 4-model comparison report from an earlier run (pretty-rendered):'
sleep 0.5
echo '❯ uv run rag-poison-lab show reports/comparison-naive.md -n 55'
uv run rag-poison-lab show reports/comparison-naive.md -n 55
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
