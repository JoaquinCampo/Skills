#!/usr/bin/env bash
# render.sh — Render PlantUML diagrams with validation and error reporting
# Usage:
#   render.sh <file.puml>              Render one file to PNG
#   render.sh <file.puml> --svg        Render one file to SVG
#   render.sh --all                    Render all .puml files in docs/diagrams/
#   render.sh --all --svg              Render all to SVG

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
DIAGRAMS_DIR="$REPO_ROOT/docs/diagrams"
FORMAT="png"
TARGET=""
ALL=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --svg)  FORMAT="svg"; shift ;;
    --png)  FORMAT="png"; shift ;;
    --all)  ALL=true; shift ;;
    *)      TARGET="$1"; shift ;;
  esac
done

# Verify plantuml is available
if ! command -v plantuml &>/dev/null; then
  echo "ERROR: plantuml not found. Install via: brew install plantuml" >&2
  exit 1
fi

# Collect files to render
FILES=()
if [[ "$ALL" == true ]]; then
  if [[ ! -d "$DIAGRAMS_DIR" ]]; then
    echo "ERROR: $DIAGRAMS_DIR does not exist" >&2
    exit 1
  fi
  while IFS= read -r -d '' f; do
    FILES+=("$f")
  done < <(find "$DIAGRAMS_DIR" -name '*.puml' -print0 | sort -z)
  if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "No .puml files found in $DIAGRAMS_DIR"
    exit 0
  fi
elif [[ -n "$TARGET" ]]; then
  # Resolve relative to repo root if not absolute
  if [[ "$TARGET" != /* ]]; then
    TARGET="$REPO_ROOT/$TARGET"
  fi
  if [[ ! -f "$TARGET" ]]; then
    echo "ERROR: File not found: $TARGET" >&2
    exit 1
  fi
  FILES+=("$TARGET")
else
  echo "Usage: render.sh <file.puml> [--svg] | render.sh --all [--svg]" >&2
  exit 1
fi

# Render
ERRORS=0
RENDERED=0
for file in "${FILES[@]}"; do
  rel="${file#"$REPO_ROOT/"}"
  output="${file%.puml}.$FORMAT"
  output_rel="${output#"$REPO_ROOT/"}"

  if plantuml -t"$FORMAT" "$file" 2>&1; then
    if [[ -f "$output" ]]; then
      echo "OK  $rel -> $output_rel"
      ((RENDERED++))
    else
      echo "WARN  $rel rendered but output not found at $output_rel"
    fi
  else
    echo "FAIL  $rel"
    ((ERRORS++))
  fi
done

# Summary
echo ""
echo "Rendered: $RENDERED | Errors: $ERRORS | Format: $FORMAT"
[[ $ERRORS -gt 0 ]] && exit 1
exit 0
