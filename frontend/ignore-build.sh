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

# 2. Skip if commit message contains [skip ci] or [ci skip]
if echo "${VERCEL_GIT_COMMIT_MESSAGE}" | grep -qiE "\[skip ci\]|\[ci skip\]"; then
  echo "🛑 Skip build: Commit message contains [skip ci]."
  exit 0
fi

# 3. Check if frontend files actually changed
if [ -f "package.json" ]; then
  CHECK_PATH="."
else
  CHECK_PATH="frontend"
fi

if [ -n "$VERCEL_GIT_PREVIOUS_SHA" ] && [ -n "$VERCEL_GIT_COMMIT_SHA" ]; then
  DIFF_TARGET="${VERCEL_GIT_PREVIOUS_SHA}...${VERCEL_GIT_COMMIT_SHA}"
else
  DIFF_TARGET="HEAD^ HEAD"
fi

if git diff --quiet $DIFF_TARGET -- "$CHECK_PATH" 2>/dev/null; then
  echo "🛑 Skip build: No changes detected in $CHECK_PATH."
  exit 0
fi

echo "✅ Changes detected in frontend. Proceeding with deployment build."
exit 1
