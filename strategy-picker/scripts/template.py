import sys
import pathlib
sys.path.insert(0, '{search_path}')
import config
import define
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
    
    cache_dir = define.get_cache_dir()
    logger_file = os.path.join(cache_dir, f"log_{ts}.txt")
    file_logger = TrackLogger(logger_file)
    llm_impl(None)
    #api = StockApi(file_logger)
 
    # if mode == Mode.User_exec:
    #     llm_impl(api)
    # else:
    #     llm_impl(api)
