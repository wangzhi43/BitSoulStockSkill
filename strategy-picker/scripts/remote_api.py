from typing import List

import define
import requests
from define import AppVersion,TokenCheckResult
import config
class PatchItem:
    def __init__(self):
        self.patch_date:str = ""
        self.patch_name:str = ""
        self.version:int = int

def request_patch_list() -> List[PatchItem]:
    """
    获取所有表的patch列表
    返回json说明：
        key: 表名
        value: 所有可用patch列表
    """
    ret: List[PatchItem] = []
    response = requests.get(f"{define.BASE_URL}/api/patch_list/all")
    if response.status_code == 200:
        rsp = response.json()
        datas_json = rsp["data"]
        for data_json in datas_json:
            item: PatchItem = PatchItem()
            item.patch_name = data_json["patch_name"]
            item.patch_date = data_json["patch_date"]
            item.version = int(float(data_json["version"]) * 10)
            ret.append(item)
    return ret


def request_decrypt_key(file_name:str, token_key:str) -> str:
    url = f"{define.BASE_URL}/api/get_decryption_key"
    params = {
        "file_name": file_name,
        "token_key": token_key
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            key = data.get("key")
            return key
        else:
            return ""
    except Exception as e:
        return ""

def request_version() -> AppVersion:
    url = f"{define.BASE_URL}/api/get_latest_version"
    try:
        params = {
            "token": config.get_token()
        }
        response = requests.post(url, json=params)
        if response.status_code == 200:
            data = response.json()
            ver = AppVersion.from_dict(data)
            return ver
        else:
            return None
    except Exception as e:
        print(e)
        return None

def request_check_token(token:str) -> TokenCheckResult:
    url = f"{define.BASE_URL}/api/check_token"
    params = {
            "token": token
        }
    response = requests.post(url, json=params)
    data = response.json()
    return TokenCheckResult.from_dict(data)

if __name__ == "__main__":
    ver = request_check_token("8ACw626fHId31d3OWwVE62yzGkA7p9vCyg1kIV9AKSiU")
    print(ver)
