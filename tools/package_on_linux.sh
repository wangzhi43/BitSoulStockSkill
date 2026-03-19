#!/bin/bash
set -e

ZIP_NAME="BitSoulStockSkill_$(date +%Y%m%d_%H%M%S).zip"
TMP_DIR="$(mktemp -d)"

cp -r strategy-picker "$TMP_DIR/BitSoulStockSkill"

find "$TMP_DIR/BitSoulStockSkill" -name ".*" -delete
find "$TMP_DIR/BitSoulStockSkill" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
rm -rf "$TMP_DIR/BitSoulStockSkill/scripts/tests"

(cd "$TMP_DIR" && zip -r "$ZIP_NAME" BitSoulStockSkill)
mv "$TMP_DIR/$ZIP_NAME" "$GITHUB_WORKSPACE/$ZIP_NAME"

echo "ZIP_NAME=$ZIP_NAME" >> $GITHUB_ENV
