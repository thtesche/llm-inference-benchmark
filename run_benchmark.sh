#!/bin/bash

# Konfiguration - Hier kannst du die Standardwerte anpassen
DEFAULT_URL="http://192.168.0.109:1234/v1"
DEFAULT_KEY="DEIN_API_KEY"
DEFAULT_ID="1"

# Globbing deaktivieren, damit "1-3" nicht als Pattern expandiert wird
set -f

# Flags parsen
URL="$DEFAULT_URL"
KEY="$DEFAULT_KEY"
ID="$DEFAULT_ID"
DRY_RUN=0

# Sammle alle Werte nach --id (unterstützt: einzelnes ID, Range "1-3", oder mehrere IDs)
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
echo "Key: ${KEY:0:4}******" # Key aus Sicherheitsgründen maskieren

# Prüfe ob ID ein Range-String ist und liste die Einträge auf
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
    # Kommagetrennt: "6,8,10" → "[6 8 10]"
    DISPLAY_IDS="[$(echo "$ID" | tr ',' ' ')]"
fi

echo "AIME Prompt ID: $DISPLAY_IDS"
echo "[HINWEIS] Ranges in Anführungszeichen: --id '1-3' | Mehrere IDs: --id 6 8 10"

# Dry-Run: Ausgabe der aufgelösten Argumente und Beendigung
if [ "$DRY_RUN" -eq 1 ]; then
    echo "PYTHON_ARGS: --url $URL --key $KEY --id $ID"
    exit 0
fi

# Prüfen ob venv existiert, ansonsten erstellen
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install openai
else
    source venv/bin/activate
fi

# Globbing reaktivieren
set +f

# Benchmark ausführen
./venv/bin/python api_benchmark.py --url "$URL" --key "$KEY" --id "$ID"

# venv wieder verlassen
deactivate
echo "Benchmark finished."
