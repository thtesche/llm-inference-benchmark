#!/bin/bash

# Configuration - adjust default values here
DEFAULT_URL="http://192.168.0.109:1234/v1"
DEFAULT_KEY="YOUR_API_KEY"
DEFAULT_ID="1"

# Disable globbing so "1-3" is not expanded as a pattern
set -f

# Parse flags
URL="$DEFAULT_URL"
KEY="$DEFAULT_KEY"
ID="$DEFAULT_ID"
DRY_RUN=0

# Collect all values after --id (supports: single ID, range "1-3", or multiple IDs)
ID_VALUES=()

# ── Pre-processing: detect glob-expanded --id ───────────────────────────
# When the shell expands --id 1-3 into --id 1 2 3, rejoin consecutive
# numbers back into a range string so the parser sees --id 1-3 again.
ORIG_ARGS=("$@")
if [ ${#ORIG_ARGS[@]} -gt 0 ]; then
    PROC_ARGS=()
    i=0
    while [ $i -lt ${#ORIG_ARGS[@]} ]; do
        arg="${ORIG_ARGS[$i]}"
        if [ "$arg" = "--id" ] && [ $((i + 1)) -lt ${#ORIG_ARGS[@]} ]; then
            nums=()
            j=$((i + 1))
            while [ $j -lt ${#ORIG_ARGS[@]} ] && [[ "${ORIG_ARGS[$j]}" =~ ^[0-9]+$ ]]; do
                nums+=("${ORIG_ARGS[$j]}")
                j=$((j + 1))
            done
            if [ ${#nums[@]} -ge 2 ]; then
                PROC_ARGS+=("--id" "${nums[0]}-${nums[${#nums[@]}-1]}")
                i=$j
            else
                PROC_ARGS+=("$arg")
                i=$((i + 1))
            fi
        else
            PROC_ARGS+=("$arg")
            i=$((i + 1))
        fi
    done
    set -- "${PROC_ARGS[@]}"
fi

# ── Normal argument parsing ────────────────────────────────────────────
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
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
echo "Key: ${KEY:0:4}******" # Mask key for security reasons

# Check if ID is a range string and list the entries
DISPLAY_IDS="$ID"
if [[ "$ID" =~ ^[0-9]+-[0-9]+$ ]]; then
    # Range: "1-3" → "[1 2 3]"
    IFS='-' read -r RANGE_START RANGE_END <<< "$ID"
    LIST=""
    while [ "$RANGE_START" -le "$RANGE_END" ]; do
        LIST="$LIST $RANGE_START"
        RANGE_START=$((RANGE_START + 1))
    done
    DISPLAY_IDS="[$(echo $LIST | xargs)]"
elif [[ "$ID" == *,* ]]; then
    # Comma-separated: "6,8,10" → "[6 8 10]"
    DISPLAY_IDS="[$(echo "$ID" | tr ',' ' ')]"
fi

echo "AIME Prompt ID: $DISPLAY_IDS"
echo "[NOTE] Ranges in quotes: --id '1-3' | Multiple IDs: --id 6 8 10"

# Dry-Run: Output resolved arguments and exit
if [ "$DRY_RUN" -eq 1 ]; then
    echo "PYTHON_ARGS: --url $URL --key $KEY --id $ID"
    exit 0
fi

# Check if venv exists, otherwise create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install openai
else
    source venv/bin/activate
fi

# Re-enable globbing

# Run benchmark
./venv/bin/python api_benchmark.py --url "$URL" --key "$KEY" --id "$ID"

# Exit venv
deactivate
echo "Benchmark finished."
