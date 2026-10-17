#!/bin/bash

# Vercel Ignored Build Step Script
# Return 0 = CANCEL / SKIP BUILD (No deployment, no storage consumed)
# Return 1 = PROCEED WITH BUILD

echo "=== Vercel Build Filter ==="
echo "Branch: ${VERCEL_GIT_COMMIT_REF:-unknown}"
echo "Commit message: ${VERCEL_GIT_COMMIT_MESSAGE:-unknown}"

# 1. Skip if on gh-pages branch (MkDocs documentation branch)
if [ "${VERCEL_GIT_COMMIT_REF}" = "gh-pages" ]; then
  echo "🛑 Skip build: gh-pages branch is reserved for MkDocs documentation."
  exit 0
fi

# 2. Check if frontend files actually changed
# Note: GitHub Actions automated forecast pipeline commits with [skip ci] to prevent
# recursive GitHub Actions triggers, but writes fresh forecasts to frontend/public/data/.
# Therefore, any change under frontend/ must proceed with deployment.
CHECK_PATH="frontend"

if [ -n "$VERCEL_GIT_PREVIOUS_SHA" ] && [ -n "$VERCEL_GIT_COMMIT_SHA" ]; then
  DIFF_TARGET="${VERCEL_GIT_PREVIOUS_SHA}...${VERCEL_GIT_COMMIT_SHA}"
else
  DIFF_TARGET="HEAD^ HEAD"
fi

if git diff --quiet $DIFF_TARGET -- "$CHECK_PATH" 2>/dev/null; then
  echo "🛑 Skip build: No changes detected in $CHECK_PATH."
  exit 0
fi

echo "✅ Changes detected in $CHECK_PATH. Proceeding with deployment build."
exit 1
