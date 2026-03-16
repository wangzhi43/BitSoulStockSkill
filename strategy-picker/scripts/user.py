
import json
import utils
import os
import requests
import define
def get_token() -> str:
    with open(os.path.join(utils.get_skill_assets_dir(), "user.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
        return data["token"]
