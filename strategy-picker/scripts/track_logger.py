import os
from time import time
from define import BASE_URL
import config
import requests
from logger import log
class TrackLogger:
    def __init__(self, file_path):
        self.logger_file = file_path
        self.f = open(file_path, mode="a", encoding="utf-8")
    
    def write(self, message:str):
        self.f.write(f"{message}\n")
        self.f.flush()

    def reportToServer(self, timestamp_id:str):
        url = f"{BASE_URL}/api/upload_log"
        # 准备multipart表单数据
        with open(self.logger_file, 'rb') as f:
            files = {'log_file': f}
            data = {
                'token': config.get_token(),
                'timestamp_id': timestamp_id
            }
            response = requests.post(url, files=files, data=data)
            # 验证响应
            if response.status_code == 200:
                response_data = response.json()
                if "log_path" in response_data:
                    log_path = response_data["log_path"]
                    log(f"SUCCESS: Log uploaded successfully to: {log_path}")
                else:
                    log("FAILURE: log_path not found in response")
            else:
                log("FAILURE: Upload failed")