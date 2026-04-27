#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
整理claw_pool目录结构
- account_XXXX -> account/account_XXXX
- ranking_XXXX -> ranking/ranking_XXXX
"""

import os
import shutil

CLAW_POOL_DIR = r"d:\codebase\BitSoulStockSkill\claw_pool"

def organize_folders():
    if not os.path.exists(CLAW_POOL_DIR):
        print(f"目录不存在: {CLAW_POOL_DIR}")
        return
    
    # 创建子目录
    account_dir = os.path.join(CLAW_POOL_DIR, "account")
    ranking_dir = os.path.join(CLAW_POOL_DIR, "ranking")
    
    os.makedirs(account_dir, exist_ok=True)
    os.makedirs(ranking_dir, exist_ok=True)
    
    moved_accounts = 0
    moved_rankings = 0
    
    for item in os.listdir(CLAW_POOL_DIR):
        src = os.path.join(CLAW_POOL_DIR, item)
        
        if not os.path.isdir(src):
            continue
        
        if item.startswith("account_"):
            dst = os.path.join(account_dir, item)
            if os.path.exists(dst):
                print(f"跳过（已存在）: {item}")
            else:
                shutil.move(src, dst)
                moved_accounts += 1
                print(f"移动: {item} -> account/")
        
        elif item.startswith("ranking_"):
            dst = os.path.join(ranking_dir, item)
            if os.path.exists(dst):
                print(f"跳过（已存在）: {item}")
            else:
                shutil.move(src, dst)
                moved_rankings += 1
                print(f"移动: {item} -> ranking/")
    
    print(f"\n完成!")
    print(f"  移动账户目录: {moved_accounts} 个")
    print(f"  移动排名目录: {moved_rankings} 个")

if __name__ == "__main__":
    organize_folders()