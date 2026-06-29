#!/bin/bash

DEFAULT_URL="http://192.168.0.109:1234/v1"
DEFAULT_KEY="DEIN_API_KEY"
DEFAULT_ID="1"

URL="$DEFAULT_URL"
KEY="$DEFAULT_KEY"
ID="$DEFAULT_ID"

# Save original args before any processing
ORIG_ARGS=("$@")

# ── Pre-processing: detect glob-expanded --id ──────────────────────────
# When the shell expands --id 1-3 into --id 1 2 3, the while loop below
# would only consume the first number.  Rejoin consecutive numbers back
# into a range string so the parser sees --id 1-3 again.
if [ ${#ORIG_ARGS[@]} -gt 0 ]; then
    PROC_ARGS=()
    i=0
    while [ $i -lt ${#ORIG_ARGS[@]} ]; do
        arg="${ORIG_ARGS[$i]}"
        if [ "$arg" = "--id" ] && [ $((i + 1)) -lt ${#ORIG_ARGS[@]} ]; then
            # Collect consecutive integers starting at index i+1
            nums=()
            j=$((i + 1))
            while [ $j -lt ${#ORIG_ARGS[@]} ] && [[ "${ORIG_ARGS[$j]}" =~ ^[0-9]+$ ]]; do
                nums+=("${ORIG_ARGS[$j]}")
                j=$((j + 1))
            done
            if [ ${#nums[@]} -ge 2 ]; then
                # Rejoin into a range: 1 2 3 → 1-3
                PROC_ARGS+=("--id" "${nums[0]}-${nums[${#nums[@]}-1]}")
                i=$j          # skip past the consumed numbers
            else
                PROC_ARGS+=("$arg")
                i=$((i + 1))
            fi
        else
            PROC_ARGS+=("$arg")
            i=$((i + 1))
        fi
    done
    ORIG_ARGS=("${PROC_ARGS[@]}")
    # Re-inject pre-processed args so the while loop sees them
    set -- "${ORIG_ARGS[@]}"
fi

# ── Normal argument parsing ────────────────────────────────────────────
while [ $# -gt 0 ]; do
    case "$1" in
        --url)
            [ -n "$2" ] && URL="$2" && shift 2 || shift
            ;;
        --key)
            [ -n "$2" ] && KEY="$2" && shift 2 || shift
            ;;
        --id)
            [ -n "$2" ] && ID="$2" && shift 2 || shift
            ;;
        *)
            shift
            ;;
    esac
done

echo "Starting benchmark..."
echo "URL: $URL"
echo "Key: ${KEY:0:4}******"
echo "AIME Prompt ID: $ID"
echo "[HINWEIS] Range-Angaben immer in Anführungszeichen setzen: --id '1-3'"