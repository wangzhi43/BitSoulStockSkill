import tempfile
import os
import shutil

def get_skill_work_dir():
    """获取/创建skill专属的自定义临时目录"""
    # 1. 获取系统临时目录路径（原生方法，跨平台）
    system_temp_dir = tempfile.gettempdir()
    # 2. 创建skill专属子目录（命名如：BitSoulStockSkill）
    skill_temp_dir = os.path.join(system_temp_dir, "BitSoulStockSkill")
    
    # 目录不存在则创建
    if not os.path.exists(skill_temp_dir):
        os.makedirs(skill_temp_dir, exist_ok=True)
    return skill_temp_dir
 
if __name__ == "__main__":
    print(get_skill_work_dir())