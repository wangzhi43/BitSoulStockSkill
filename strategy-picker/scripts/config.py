
import json
import utils
import os
import requests
import define
import remote_api
def get_token() -> str:
    user_json_file = os.path.join(utils.get_skill_work_dir(), "user.json")
    if not os.path.exists(user_json_file):
        return ""
    with open(user_json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data["token"]
    
def set_token(token: str):
    user_json_file = os.path.join(utils.get_skill_work_dir(), "user.json")
    data:dict = {}
    if os.path.exists(user_json_file):
        with open(user_json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    data["token"] = token
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    with open(user_json_file, "w", encoding="utf-8") as f:
        f.write(json_str)

def get_local_version() -> str:
    with open(os.path.join(utils.get_skill_assets_dir(), "config.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
        return data["version"]