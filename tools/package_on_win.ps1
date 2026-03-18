# pack_strategy_picker.ps1
# 将 strategy-picker 目录打包成 zip，清理 __pycache__ 和 tests 目录

$srcDir   = "$PSScriptRoot\..\strategy-picker"
$tmpBase  = "$env:TEMP\sp_pack_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
$tmpDir   = "$tmpBase\BitSoulStockSkill"
$outZip   = "$PSScriptRoot\BitSoulStockSkill_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip"

# 1. 拷贝到临时目录
Write-Host "复制源目录..."
Copy-Item -Path $srcDir -Destination $tmpDir -Recurse -Force

# 2. 删除 __pycache__ 目录（所有层级）
Write-Host "清理 __pycache__..."
Get-ChildItem -Path $tmpDir -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force

# 3. 删除 scripts/tests 目录
$testsDir = "$tmpDir\scripts\tests"
if (Test-Path $testsDir) {
    Write-Host "清理 scripts\tests..."
    Remove-Item -Path $testsDir -Recurse -Force
}

# 4. 压缩成 zip
Write-Host "压缩中..."
Compress-Archive -Path "$tmpBase\BitSoulStockSkill" -DestinationPath $outZip

# 5. 清理临时目录
Remove-Item -Path $tmpBase -Recurse -Force

Write-Host "完成：$outZip"
