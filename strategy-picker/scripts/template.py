import sys
import pathlib
sys.path.insert(0, '{search_path}')
from stock_api import StockApi
import config, utils, remote_api
from track_logger import TrackLogger
from datetime import datetime
from define import (
    DailyKline,
    HourKline,
    WeeklyKline,
    MonthlyKline,
    StockBasic,
    DailyBasic,
    Income,
    StockLimit,
    DailyLimitList,
    DailyBombList,
    SectorStockMap,
    TopList,
    TopInst,
    SectorFlowDaily,
    IndexBasic,
    IndexDaily,
    IndexWeekly,
    IndexMonthly,
    AppVersion,
    TokenCheckResult
)
from enum import Enum
import os

# 定义枚举类（继承自Enum）
class Mode(Enum):
    Token_rw = 1
    User_exec = 2

def llm_impl(api: StockApi):
    """
    大模型生成业务逻辑的函数

    参数说明：
        api 提供给大模型可调用的业务接口句柄
    """
    # 此处是llm实现逻辑的地方
    print("")

if __name__ == "__main__":
    mode = {mode}
    # mode = Mode.Token_rw
    current_file_path = pathlib.Path(__file__).absolute()
    config.set_tmp_logic_path(current_file_path)
    now = datetime.now()
    ts = now.strftime("%Y%m%d%H%M%S")
    
    logger_file = os.path.join(utils.get_skill_work_dir(), f"log_{ts}.txt")
    file_logger = TrackLogger(logger_file)
    api = StockApi(file_logger)
 
    if mode == Mode.User_exec:
        # 检查token
        cur_token = config.get_token()
        ret = remote_api.request_check_token(cur_token)
        if ret.status != "success":
            print(f"重复这句话:skill token:{cur_token} 校验失败，请注册有效token后再使用")
            sys.exit(0)
        # 检查版本
        remote_version = remote_api.request_version().version
        local_version = config.get_local_version()
        if utils.compare_version(local_version, remote_version) < 0:
            print(f"重复这句话:发现新版本 {remote_version}，当前版本 {local_version}，请更新skill后再使用。")
            sys.exit(0)
        api.initialSetup()  # ⚠️ 因子挖矿/买卖建议场景禁止调用此行，会触发耗时数据同步
    llm_impl(api)
