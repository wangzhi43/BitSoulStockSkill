"""
utils.py 单元测试
"""
import sys
import os
from unittest.mock import MagicMock

_scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_scripts_dir)
sys.path.insert(0, _scripts_dir)

# mock 外部依赖，避免 import utils 时 requests 未安装报错
sys.modules.setdefault('requests', MagicMock())

from utils import compare_version

def test_compare_version():
    # 题目给出的四个基准用例
    assert compare_version("1.0.1", "1.0.0") == 1,  "1.0.1 应大于 1.0.0"
    assert compare_version("1.19.0", "2.0.0") == -1, "1.19.0 应小于 2.0.0"
    assert compare_version("1.0", "2.0") == -1,      "1.0 应小于 2.0"
    assert compare_version("1.0", "0.9") == 1,       "1.0 应大于 0.9"

    # 相等
    assert compare_version("1.2.3", "1.2.3") == 0,   "相同版本号应相等"
    assert compare_version("1.0", "1.0.0") == 0,     "1.0 与 1.0.0 末尾补零后应相等"

    # 大版本优先
    assert compare_version("2.0.0", "1.99.99") == 1, "主版本号大则整体大"

    # 次版本号按整数比较（非字符串）
    assert compare_version("1.19", "1.9") == 1,      "1.19 应大于 1.9（整数比较）"

    # 对称性验证
    assert compare_version("1.0.0", "1.0.1") == -1,  "结果应与正向比较相反"

    print("所有测试通过")

if __name__ == "__main__":
    test_compare_version()
     
