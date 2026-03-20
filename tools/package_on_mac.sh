#!/bin/bash

# Usage: ./package.sh [output_path]
# Default output path is current directory
# 先安装 python3 -m pip install python-minifier --break-system-packages
set -e
echo ${BASH_SOURCE}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/../strategy-picker"
OUTPUT_PATH="${1:-$SCRIPT_DIR}"
ZIP_NAME="BitSoulStockSkill_$(date +%Y%m%d_%H%M%S).zip"
TMP_DIR="$(mktemp -d)"

echo "Copying BitSoulStockSkill to temp dir: $TMP_DIR"
cp -r "$SOURCE_DIR" "$TMP_DIR/BitSoulStockSkill"

echo "Copying documentation files..."
cp "$SCRIPT_DIR/../API_FOR_LLM.md" "$TMP_DIR/BitSoulStockSkill/references/API_FOR_LLM.md"

echo "Removing hidden files..."
find "$TMP_DIR/BitSoulStockSkill" -name ".*" -delete

echo "Removing __pycache__ directories..."
find "$TMP_DIR/BitSoulStockSkill" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "Removing test files..."
rm -rf "$TMP_DIR/BitSoulStockSkill/scripts/tests"

if [ "$MINIFY" = "true" ]; then
  echo "需要加密"
fi

if [ "$MINIFY" = "true" ]; then
  pyminify --in-place --prefer-single-line $TMP_DIR/BitSoulStockSkill/scripts/data_fetcher.py
  pyminify --in-place --prefer-single-line $TMP_DIR/BitSoulStockSkill/scripts/remote_api.py
fi


echo "Creating zip archive..."
(cd "$TMP_DIR" && zip -r "$ZIP_NAME" BitSoulStockSkill)
mv "$TMP_DIR/$ZIP_NAME" "$GITHUB_WORKSPACE/$ZIP_NAME"
echo "ZIP_NAME=$ZIP_NAME" >> $GITHUB_ENV

rm -rf "$TMP_DIR"

echo "Done: $OUTPUT_PATH/$ZIP_NAME"
