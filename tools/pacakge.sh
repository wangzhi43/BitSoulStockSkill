#!/bin/bash

# Usage: ./package.sh [output_path]
# Default output path is current directory
# 先安装 python3 -m pip install python-minifier --break-system-packages
set -e
echo ${BASH_SOURCE}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/../strategy-picker"
OUTPUT_PATH="${1:-$SCRIPT_DIR}"
ZIP_NAME="BitSoulStockSkill.zip"
TMP_DIR="$(mktemp -d)"

echo "Copying BitSoulStockSkill to temp dir: $TMP_DIR"
cp -r "$SOURCE_DIR" "$TMP_DIR/BitSoulStockSkill"

echo "Removing hidden files..."
find "$TMP_DIR/BitSoulStockSkill" -name ".*" -delete

echo "Removing __pycache__ directories..."
find "$TMP_DIR/BitSoulStockSkill" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "Removing test files..."
rm -rf "$TMP_DIR/BitSoulStockSkill/scripts/tests"

#混淆
pyminify --in-place --prefer-single-line $TMP_DIR/BitSoulStockSkill/scripts/data_fetcher.py
pyminify --in-place --prefer-single-line $TMP_DIR/BitSoulStockSkill/scripts/db_engine.py


echo "Creating zip archive..."
(cd "$TMP_DIR" && zip -r "$ZIP_NAME" BitSoulStockSkill)

mv "$TMP_DIR/$ZIP_NAME" "$OUTPUT_PATH/$ZIP_NAME"

rm -rf "$TMP_DIR"

echo "Done: $OUTPUT_PATH/$ZIP_NAME"
