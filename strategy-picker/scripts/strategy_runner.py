"""
strategy_runner.py — 策略执行主脚本

用法：
  python3 strategy_runner.py --strategy-file <策略文件路径>
  python3 strategy_runner.py --builtin <策略名称> 

策略代码需定义一个函数：
  def strategy(api):
      # 用户自定义的策略路基
      ...
"""

import sys
import os
import argparse
import importlib.util
import traceback

# 将 scripts 目录加入路径，使策略代码能 import stock_api
sys.path.insert(0, os.path.dirname(__file__))

import stock_api as api

BUILTIN_DIR = os.path.join(os.path.dirname(__file__), "builtin_strategies")


def load_strategy_from_code(code: str):
    """从代码字符串中加载策略函数。"""
    namespace = {"api": api}
    try:
        exec(compile(code, "<strategy>", "exec"), namespace)
    except SyntaxError as e:
        print(f"[错误] 策略代码语法错误: {e}")
        sys.exit(1)
    if "strategy" not in namespace:
        print("[错误] 策略代码中未找到函数 'strategy(symbol, api)'")
        sys.exit(1)
    return namespace["strategy"]


def load_strategy_from_file(filepath: str):
    """从 .py 文件中加载策略函数。"""
    if not os.path.exists(filepath):
        print(f"[错误] 策略文件不存在: {filepath}")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("user_strategy", filepath)
    module = importlib.util.module_from_spec(spec)
    module.api = api
    spec.loader.exec_module(module)
    if not hasattr(module, "strategy"):
        print("[错误] 策略文件中未找到函数 'strategy(api)'")
        sys.exit(1)
    return module.strategy


def load_builtin_strategy(name: str):
    """加载内置策略。"""
    filepath = os.path.join(BUILTIN_DIR, f"{name}.py")
    return load_strategy_from_file(filepath)

def main():
    parser = argparse.ArgumentParser(description="自定义策略选股执行器")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--strategy-file", type=str, help="策略代码文件路径（.py）")
    group.add_argument("--builtin",       type=str, help="内置策略名称（见 builtin_strategies/）")
    parser.add_argument("--list-builtin", action="store_true", help="列出所有可用的内置策略")

    args = parser.parse_args()

    # 列出内置策略
    if args.list_builtin:
        files = [f[:-3] for f in os.listdir(BUILTIN_DIR) if f.endswith(".py") and not f.startswith("_")]
        print("可用的内置策略：")
        for f in sorted(files):
            print(f"  {f}")
        return

    # 加载策略
    if args.builtin:
        strategy_fn = load_builtin_strategy(args.builtin)
    elif args.strategy_file:
        strategy_fn = load_strategy_from_file(args.strategy_file)
    else:
        print("Error:skill参数出错")
        return
    # 执行策略
    strategy_fn(api)
    print("skill执行完成")


if __name__ == "__main__":
    main()
