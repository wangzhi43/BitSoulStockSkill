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

def get_skill_dir():
    current_file_path = os.path.abspath(__file__)
    dir = os.path.dirname(os.path.dirname(current_file_path))
    return dir

def get_skill_assets_dir():
    return os.path.join(get_skill_dir(), "assets")

def scan_files_in_dir(dir:str):
    file_list = []
    # scandir 返回可迭代的 DirEntry 对象，包含文件信息
    with os.scandir(dir) as entries:
        for entry in entries:
            # is_file(follow_symlinks=False)：排除符号链接，仅判断真实文件
            if entry.is_file(follow_symlinks=False):
                file_list.append(entry.path)  # entry.path 直接返回完整路径
    return file_list

if __name__ == "__main__":
    print(get_skill_work_dir())