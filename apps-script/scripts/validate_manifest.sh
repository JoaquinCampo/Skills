#!/usr/bin/env bash
# validate_manifest.sh — Pre-push validation for appsscript.json
# Usage: ./validate_manifest.sh [path/to/appsscript.json]
#
# Checks:
# 1. File exists and is valid JSON
# 2. runtimeVersion is V8
# 3. timeZone is set
# 4. oauthScopes are present (warns if overly broad)
# 5. No obvious misconfigurations

set -euo pipefail

MANIFEST="${1:-appsscript.json}"

if [[ ! -f "$MANIFEST" ]]; then
  echo "ERROR: $MANIFEST not found"
  exit 1
fi

# Check valid JSON
if ! python3 -c "import json; json.load(open('$MANIFEST'))" 2>/dev/null; then
  echo "ERROR: $MANIFEST is not valid JSON"
  exit 1
fi

echo "Validating $MANIFEST..."
ERRORS=0
WARNINGS=0

# Check runtimeVersion
RUNTIME=$(python3 -c "import json; m=json.load(open('$MANIFEST')); print(m.get('runtimeVersion', 'MISSING'))")
if [[ "$RUNTIME" == "MISSING" ]]; then
  echo "  WARNING: runtimeVersion not set (defaults to Rhino — use V8 for modern JS)"
  ((WARNINGS++))
elif [[ "$RUNTIME" != "V8" ]]; then
  echo "  WARNING: runtimeVersion is '$RUNTIME' — consider 'V8' for modern JavaScript"
  ((WARNINGS++))
fi

# Check timeZone
TZ=$(python3 -c "import json; m=json.load(open('$MANIFEST')); print(m.get('timeZone', 'MISSING'))")
if [[ "$TZ" == "MISSING" ]]; then
  echo "  WARNING: timeZone not set"
  ((WARNINGS++))
fi

# Check scopes
SCOPES=$(python3 -c "
import json
m = json.load(open('$MANIFEST'))
scopes = m.get('oauthScopes', [])
print(len(scopes))
for s in scopes:
    print(s)
")

SCOPE_COUNT=$(echo "$SCOPES" | head -1)
if [[ "$SCOPE_COUNT" == "0" ]]; then
  echo "  INFO: No explicit scopes (auto-detection will be used)"
fi

# Check for overly broad scopes
BROAD_SCOPES=(
  "https://mail.google.com/"
  "https://www.googleapis.com/auth/drive"
  "https://www.googleapis.com/auth/gmail"
  "https://www.googleapis.com/auth/calendar"
  "https://www.googleapis.com/auth/spreadsheets"
)

while IFS= read -r scope; do
  for broad in "${BROAD_SCOPES[@]}"; do
    if [[ "$scope" == "$broad" ]]; then
      echo "  WARNING: Broad scope detected: $scope"
      echo "           Consider using a narrower alternative (e.g., .readonly, .file)"
      ((WARNINGS++))
    fi
  done
done <<< "$(echo "$SCOPES" | tail -n +2)"

# Check webapp config
WEBAPP_ACCESS=$(python3 -c "
import json
m = json.load(open('$MANIFEST'))
wa = m.get('webapp', {})
print(wa.get('access', 'NONE'))
" 2>/dev/null || echo "NONE")

if [[ "$WEBAPP_ACCESS" == "ANYONE_ANONYMOUS" ]]; then
  echo "  WARNING: Web app accessible by anyone without Google account"
  ((WARNINGS++))
fi

# Summary
echo ""
if [[ $ERRORS -gt 0 ]]; then
  echo "FAILED: $ERRORS error(s), $WARNINGS warning(s)"
  exit 1
elif [[ $WARNINGS -gt 0 ]]; then
  echo "PASSED with $WARNINGS warning(s)"
  exit 0
else
  echo "PASSED: No issues found"
  exit 0
fi
