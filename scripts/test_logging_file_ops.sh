#!/usr/bin/env bash
# Test shell script for script-automation-testing skill.
# Demonstrates: log output, abnormal exit, text file creation, and text writing.

set -Eeuo pipefail

SCRIPT_NAME="$(basename "$0")"
OUTPUT_DIR="${OUTPUT_DIR:-./output}"
OUTPUT_FILE="${OUTPUT_FILE:-$OUTPUT_DIR/sample.txt}"
LOG_FILE="${LOG_FILE:-$OUTPUT_DIR/${SCRIPT_NAME%.sh}.log}"
MESSAGE="${MESSAGE:-Hello from script-automation-testing}"
FAIL_MODE="${FAIL_MODE:-0}"

mkdir -p "$OUTPUT_DIR"

timestamp() {
  date '+%Y-%m-%d %H:%M:%S%z'
}

log() {
  local level="$1"
  shift
  printf '[%s] [%s] %s\n' "$(timestamp)" "$level" "$*" | tee -a "$LOG_FILE"
}

on_error() {
  local exit_code=$?
  local line_no=${BASH_LINENO[0]:-unknown}
  log "ERROR" "Unexpected failure at line ${line_no}; exit_code=${exit_code}"
  exit "$exit_code"
}
trap on_error ERR

usage() {
  cat <<USAGE
Usage: $SCRIPT_NAME [--message TEXT] [--output FILE] [--fail]

Options:
  --message TEXT   Text to write into the output file.
  --output FILE    Output text file path. Default: $OUTPUT_FILE
  --fail           Trigger an intentional abnormal exit after logging.
  -h, --help       Show this help message.

Environment:
  OUTPUT_DIR       Directory for output and logs. Default: ./output
  OUTPUT_FILE      Output text file path.
  LOG_FILE         Log file path.
  MESSAGE          Default message text.
  FAIL_MODE=1      Same as --fail.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --message)
      if [[ $# -lt 2 || -z "${2:-}" ]]; then
        log "ERROR" "--message requires a non-empty value"
        exit 2
      fi
      MESSAGE="$2"
      shift 2
      ;;
    --output)
      if [[ $# -lt 2 || -z "${2:-}" ]]; then
        log "ERROR" "--output requires a file path"
        exit 2
      fi
      OUTPUT_FILE="$2"
      OUTPUT_DIR="$(dirname "$OUTPUT_FILE")"
      mkdir -p "$OUTPUT_DIR"
      shift 2
      ;;
    --fail)
      FAIL_MODE="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      log "ERROR" "Unknown argument: $1"
      usage >&2
      exit 2
      ;;
  esac
done

log "INFO" "Starting $SCRIPT_NAME"
log "INFO" "Output file: $OUTPUT_FILE"
log "INFO" "Log file: $LOG_FILE"

if [[ "$FAIL_MODE" == "1" ]]; then
  log "ERROR" "Intentional abnormal exit requested by --fail or FAIL_MODE=1"
  exit 99
fi

log "INFO" "Creating text file"
: > "$OUTPUT_FILE"

log "INFO" "Writing text content"
{
  printf 'message=%s\n' "$MESSAGE"
  printf 'created_at=%s\n' "$(timestamp)"
  printf 'script=%s\n' "$SCRIPT_NAME"
} >> "$OUTPUT_FILE"

if [[ ! -s "$OUTPUT_FILE" ]]; then
  log "ERROR" "Output file was not created or is empty: $OUTPUT_FILE"
  exit 3
fi

log "INFO" "Text file created successfully; bytes=$(wc -c < "$OUTPUT_FILE" | tr -d ' ')"
log "INFO" "Completed successfully"
