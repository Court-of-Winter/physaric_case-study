#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

WITH_TESTS=0
while (($#)); do
    case "$1" in
        --with-tests)
            WITH_TESTS=1
            ;;
        -h|--help)
            printf '%s\n' \
                "Usage: bash ./run.sh [--with-tests]" \
                "  --with-tests  Build and run the test suite before analysis"
            exit 0
            ;;
        *)
            printf 'Unknown option: %s\n' "$1" >&2
            printf '%s\n' "Usage: bash ./run.sh [--with-tests]" >&2
            exit 2
            ;;
    esac
    shift
done

EMAIL_DATA_DIR="${EMAIL_DATA_DIR:-enron_mail_20150507/maildir}"
HMAC_KEY_FILE="${HMAC_KEY_FILE:-../secrets/hmac.key}"
ALIAS_MAP_FILE="${ALIAS_MAP_FILE:-config/empty_alias_map.json}"
MIN_EDGE_COUNT="${MIN_EDGE_COUNT:-5}"
EXPORT_EDGES="${EXPORT_EDGES:-0}"
OUTPUT_DIR="$ROOT_DIR/outputs"

resolve_input_path() {
    local path="$1"
    if [[ "$path" != /* ]]; then
        path="$ROOT_DIR/$path"
    fi
    realpath -e -- "$path"
}

if ! EMAIL_DATA_DIR="$(resolve_input_path "$EMAIL_DATA_DIR")" \
    || ! HMAC_KEY_FILE="$(resolve_input_path "$HMAC_KEY_FILE")" \
    || ! ALIAS_MAP_FILE="$(resolve_input_path "$ALIAS_MAP_FILE")"; then
    printf '%s\n' "Input directory, key file, or alias-map file is unavailable." >&2
    exit 2
fi
if [[ ! -d "$EMAIL_DATA_DIR" || ! -f "$HMAC_KEY_FILE" || ! -f "$ALIAS_MAP_FILE" ]]; then
    printf '%s\n' "Input directory, key file, or alias-map file is unavailable." >&2
    exit 2
fi
case "$HMAC_KEY_FILE" in
    "$ROOT_DIR"/*)
        printf '%s\n' "Store the HMAC key outside the repository." >&2
        exit 2
        ;;
esac
if [[ ! "$MIN_EDGE_COUNT" =~ ^[1-9][0-9]*$ ]]; then
    printf '%s\n' "MIN_EDGE_COUNT must be a positive integer." >&2
    exit 2
fi
if [[ "$EXPORT_EDGES" != 0 && "$EXPORT_EDGES" != 1 ]]; then
    printf '%s\n' "EXPORT_EDGES must be 0 (default) or 1." >&2
    exit 2
fi

DATA_REAL="$(cd -- "$EMAIL_DATA_DIR" && pwd -P)"
case "$OUTPUT_DIR/" in
    "$DATA_REAL/"*)
        printf '%s\n' "Output directory must be outside the input corpus." >&2
        exit 2
        ;;
esac
mkdir -p "$OUTPUT_DIR"
if [[ "$EXPORT_EDGES" == 0 ]] && {
    [[ -f "$OUTPUT_DIR/person_edges_2001.csv" ]] ||
    [[ -f "$OUTPUT_DIR/organization_edges_2001.csv" ]]
}; then
    printf '%s\n' \
        "WARNING: prior edge exports remain in outputs/; remove them manually if no longer needed." \
        >&2
fi

RUN_UID="${SUDO_UID:-$(id -u)}"
RUN_GID="${SUDO_GID:-$(id -g)}"
if [[ "$WITH_TESTS" == 1 ]]; then
    docker build --target test -t enron-metadata-analysis:test "$ROOT_DIR"
    docker run --rm enron-metadata-analysis:test
fi
docker build -t enron-metadata-analysis:local "$ROOT_DIR"
EDGE_EXPORT_ARGS=()
if [[ "$EXPORT_EDGES" == 1 ]]; then
    EDGE_EXPORT_ARGS+=(--export-edges)
fi
docker run --rm \
    --user "$RUN_UID:$RUN_GID" \
    --mount "type=bind,source=$EMAIL_DATA_DIR,target=/data,readonly" \
    --mount "type=bind,source=$HMAC_KEY_FILE,target=/run/secrets/hmac.key,readonly" \
    --mount "type=bind,source=$ALIAS_MAP_FILE,target=/run/secrets/alias-map.json,readonly" \
    --mount "type=bind,source=$OUTPUT_DIR,target=/outputs" \
    enron-metadata-analysis:local \
    --data-dir /data \
    --key-file /run/secrets/hmac.key \
    --alias-map /run/secrets/alias-map.json \
    --output-dir /outputs \
    --min-edge-count "$MIN_EDGE_COUNT" \
    "${EDGE_EXPORT_ARGS[@]}"
