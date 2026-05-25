#!/usr/bin/env bash
# Convert an asciinema .cast recording into an MP4 video.
#
# Pipeline: .cast --(agg)--> .gif --(ffmpeg)--> .mp4
#
# Why: asciinema's web player supports scrubbing, but for a portfolio
# embed (or sharing without depending on asciinema.org) an MP4 is easier.
# Standard video players let viewers jump around the timeline directly.
#
# Requires:
#   agg     — Rust-based asciinema GIF generator.
#             Arch:  sudo pacman -S agg
#             Cargo: cargo install --git https://github.com/asciinema/agg
#   ffmpeg  — Universal video toolkit.
#             Arch:  sudo pacman -S ffmpeg
#
# Usage:
#   scripts/cast-to-mp4.sh                    # converts ./demo.cast
#   scripts/cast-to-mp4.sh my-recording.cast  # converts the given file

set -euo pipefail

CAST_FILE="${1:-demo.cast}"
BASE="${CAST_FILE%.cast}"
GIF_FILE="${BASE}.gif"
MP4_FILE="${BASE}.mp4"

if [[ ! -f "$CAST_FILE" ]]; then
    echo "error: $CAST_FILE not found" >&2
    echo "       Record one first with scripts/record-demo.sh" >&2
    exit 1
fi

for cmd in agg ffmpeg; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "error: $cmd not on PATH" >&2
        case "$cmd" in
            agg)
                echo "       Arch:  sudo pacman -S agg" >&2
                echo "       Cargo: cargo install --git https://github.com/asciinema/agg" >&2
                ;;
            ffmpeg)
                echo "       Arch:  sudo pacman -S ffmpeg" >&2
                ;;
        esac
        exit 1
    fi
done

echo "[1/2] Rendering $CAST_FILE to GIF..."
agg "$CAST_FILE" "$GIF_FILE"

echo "[2/2] Encoding GIF to MP4..."
# -movflags faststart  puts the metadata at the front so the file is
#                      streamable / seekable from the moment it loads
# -pix_fmt yuv420p     widest browser/player compatibility
# -vf scale=...        force even dimensions (some encoders require this)
# -crf 23              visually lossless for terminal content
ffmpeg -y -hide_banner -loglevel error \
    -i "$GIF_FILE" \
    -movflags faststart \
    -pix_fmt yuv420p \
    -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" \
    -c:v libx264 \
    -crf 23 \
    "$MP4_FILE"

echo
echo "Output:"
echo "  $MP4_FILE  (share this)"
echo "  $GIF_FILE  (intermediate, safe to delete)"
echo
echo "To display the MP4 inline on the GitHub repo page:"
echo
echo "  1. Open any issue, PR, or discussion on the repo (a draft is fine):"
echo "     https://github.com/Loffah/rag-poison-lab/issues/new"
echo
echo "  2. Drag $MP4_FILE into the comment editor. GitHub uploads it and"
echo "     replaces it with a URL that looks like:"
echo "       https://github.com/user-attachments/assets/..."
echo
echo "  3. Copy that URL. Don't actually submit the issue / comment."
echo
echo "  4. Paste the URL on its own line in README.md. GitHub auto-embeds"
echo "     it as a video player with a scrub bar."
echo
echo "  The MP4 itself stays on GitHub's CDN; you don't have to commit it."
