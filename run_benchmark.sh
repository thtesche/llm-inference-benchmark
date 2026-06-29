#!/bin/bash

# Konfiguration - Hier kannst du die Standardwerte anpassen
DEFAULT_URL="http://192.168.0.109:1234/v1"
DEFAULT_KEY="DEIN_API_KEY"
DEFAULT_ID="1"

# Flags parsen
URL="$DEFAULT_URL"
KEY="$DEFAULT_KEY"
ID="$DEFAULT_ID"

# Sammle alle Werte nach --id (unterstützt: einzelnes ID, Range "1-3", oder mehrere IDs)
ID_VALUES=()

for arg in "$@"; do
    case "$arg" in
        --url)
            URL="$2"
            shift 2
            ;;
        --key)
            KEY="$2"
            shift 2
            ;;
        --id)
            # Alle folgenden Zahlen-Argumente bis zum nächsten Flag sammeln
            shift 1  # --id selbst überspringen
            while [ $# -gt 0 ]; do
                next="$1"
                # Wenn nächstes Argument ein Flag ist, aufhören
                case "$next" in
                    --*) break ;;
                esac
                # Nur Zahlen-Argumente sammeln
                if [[ "$next" =~ ^[0-9]+$ ]]; then
                    ID_VALUES+=("$next")
                else
                    # Kein Zahlen-Wert: als Range oder einzelnes ID nehmen
                    ID_VALUES+=("$next")
                fi
                shift
            done
            # Alle gesammelten Werte zu einem String verbinden (kommagetrennt)
            if [ ${#ID_VALUES[@]} -eq 0 ]; then
                ID="$DEFAULT_ID"
            elif [ ${#ID_VALUES[@]} -eq 1 ]; then
                ID="${ID_VALUES[0]}"
            else
                # Mehrere IDs: kommagetrennt übergeben (z.B. "6,8,10")
                ID=$(IFS=,; echo "${ID_VALUES[*]}")
            fi
            ;;
        *)
            # Positionales Argument (erstes nicht-flag): URL
            if [ "$URL" = "$DEFAULT_URL" ] && [ -z "$URL_SET" ]; then
                URL="$arg"
                URL_SET=1
                shift
            else
                shift
            fi
            ;;
    esac
done

echo "Starting benchmark..."
echo "URL: $URL"
echo "Key: ${KEY:0:4}******" # Key aus Sicherheitsgründen maskieren

# Prüfe ob ID ein Range-String ist und liste die Einträge auf
DISPLAY_IDS="$ID"
if [[ "$ID" =~ ^[0-9]+-[0-9]+$ ]]; then
    # Range: "1-3" → "1 2 3"
    RANGE_PART="${ID/-/ }"
    START="${RANGE_PART%% *}"
    END="${RANGE_PART## *}"
    LIST=""
    for ((i=START; i<=END; i++)); do
        LIST="$LIST $i"
    done
    DISPLAY_IDS="[$(echo $LIST | xargs)]"
elif [[ "$ID" == *,* ]]; then
    # Kommagetrennt: "6,8,10" → "[6 8 10]"
    DISPLAY_IDS="[$(echo "$ID" | tr ',' ' ')]"
fi

echo "AIME Prompt ID: $DISPLAY_IDS"
echo "[HINWEIS] Ranges in Anführungszeichen: --id '1-3' | Mehrere IDs: --id 6 8 10"

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
