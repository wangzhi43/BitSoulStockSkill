#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import argparse
import glob
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime

def plot_lobster_returns(ranking_dir: str, lobster_ids: list, start_date: str = None, end_date: str = None, output_dir: str = None):
    if not os.path.exists(ranking_dir):
        print(f"错误: 文件夹不存在 {ranking_dir}")
        return
        
    if output_dir is None:
        output_dir = ranking_dir
    else:
        os.makedirs(output_dir, exist_ok=True)

    # 获取所有的 json 文件并按日期排序
    json_files = glob.glob(os.path.join(ranking_dir, "ranking_*.json"))
    json_files.sort()

    if not json_files:
        print(f"错误: 在 {ranking_dir} 中没有找到 ranking_*.json 文件")
        return

    # 解析出日期列表
    dates = []
    file_map = {}
    for f in json_files:
        filename = os.path.basename(f)
        # ranking_2026-03-16.json
        date_str = filename.replace("ranking_", "").replace(".json", "")
        
        # 应用日期过滤
        if start_date and date_str < start_date:
            continue
        if end_date and date_str > end_date:
            continue
            
        dates.append(date_str)
        file_map[date_str] = f

    if not dates:
        print("错误: 指定日期区间内没有找到数据")
        return

    print(f"找到 {len(dates)} 天的数据: {dates[0]} 到 {dates[-1]}")

    # 强制设置无头环境
    matplotlib.use('Agg')
    
    # 终极解决 Windows 中文乱码方案 (通过 fontManager.addfont 动态注册)
    import matplotlib.font_manager as fm
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning) 

    zh_font_path = None
    # 优先使用绝对路径，避免 findSystemFonts 的遗漏
    for fp in ["C:\\Windows\\Fonts\\msyh.ttc", "C:\\Windows\\Fonts\\msyh.ttf", "C:\\Windows\\Fonts\\simhei.ttf", "C:\\Windows\\Fonts\\simsun.ttc"]:
        if os.path.exists(fp):
            zh_font_path = fp
            break

    if not zh_font_path:
        font_paths = fm.findSystemFonts()
        for font_name in ['msyh', 'simhei', 'simsun', 'yahei']:
            for fp in font_paths:
                if font_name in fp.lower():
                    zh_font_path = fp
                    break
            if zh_font_path:
                break

    if zh_font_path:
        # 核心修复：直接将物理字体文件注册到 matplotlib 内存中
        fm.fontManager.addfont(zh_font_path)
        my_font = fm.FontProperties(fname=zh_font_path)
        # 将注册好的字体设为全局默认字体
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = [my_font.get_name(), 'sans-serif']
    else:
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
    
    plt.rcParams['axes.unicode_minus'] = False # 正常显示负号

    # 设置类似前端的现代美观样式
    try:
        plt.style.use('seaborn-v0_8-darkgrid')
    except OSError:
        try:
            plt.style.use('seaborn-darkgrid')
        except OSError:
            pass  # Fallback to default
    
    # 颜色主题 (暗黑模式匹配系统UI)
    primary_color = '#F6465D'  # 红色 (收益为正的颜色)
    negative_color = '#0ECB81' # 绿色 (收益为负的颜色)
    bg_color = '#131722'       # 深蓝色背景
    grid_color = '#2A2E39'     # 网格线颜色
    text_color = '#A0AEC0'     # 浅灰色文字
    title_color = '#FFFFFF'    # 白色标题
    fill_color = '#F6465D'     # 填充红色
    zero_line_color = '#A0AEC0' # 0基准线颜色

    # 遍历每个指定的龙虾ID
    for lid in lobster_ids:
        returns = []
        valid_dates = []
        
        print(f"正在处理龙虾ID: {lid} ...")
        
        # 记录前一个有效收益率，防止前期未进入前100名时无数据
        last_return = 0.0
        
        # 从每一天的 json 文件中寻找该龙虾的总收益率
        for d in dates:
            with open(file_map[d], 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            found = False
            for account in data:
                if account['id'] == lid:
                    returns.append(account['total_return_pct'])
                    last_return = account['total_return_pct']
                    valid_dates.append(d)
                    found = True
                    break
            
            if not found:
                # 如果某天前100名没找到它，尝试使用全量csv或者保持前一天的收益率
                # 因为默认只存了前100名，如果没有它，我们暂时用上一次的记录
                print(f"  警告: 日期 {d} 的前100名中未找到龙虾 {lid}，使用前一记录: {last_return}%")
                returns.append(last_return)
                valid_dates.append(d)
        
        if not valid_dates:
            print(f"  龙虾 {lid} 没有可用的绘图数据。")
            continue
            
        # 过滤掉收益率为0的数据（通常是没有发生交易，或者没有上榜）
        filtered_dates = []
        filtered_returns = []
        for d, r in zip(valid_dates, returns):
            if r != 0.0:
                filtered_dates.append(d)
                filtered_returns.append(r)
                
        if not filtered_dates:
            print(f"  龙虾 {lid} 所有日期的收益率均为 0，无有效数据绘图。")
            continue
            
        # 开始绘图
        fig, ax = plt.subplots(figsize=(14, 7), facecolor=bg_color)
        ax.set_facecolor(bg_color)
        
        # 强制所有 Text 对象应用此字体
        if zh_font_path:
            prop = fm.FontProperties(fname=zh_font_path)
        else:
            prop = None
        
        # 绘制0%基准线
        ax.axhline(y=0, color=zero_line_color, linestyle='--', linewidth=1.5, alpha=0.6, zorder=1)
        
        # 绘制主曲线和数据点
        ax.plot(filtered_dates, filtered_returns, marker='o', linestyle='-', linewidth=3, 
                markersize=8, color=primary_color, markerfacecolor=bg_color, 
                markeredgewidth=2, zorder=3, label='累计收益率')
        
        # 填充曲线下方面积以增加现代感
        ax.fill_between(filtered_dates, filtered_returns, 0, where=[r >= 0 for r in filtered_returns], 
                        color=fill_color, alpha=0.2, zorder=2)
        ax.fill_between(filtered_dates, filtered_returns, 0, where=[r < 0 for r in filtered_returns], 
                        color=negative_color, alpha=0.2, zorder=2) 
        
        # 在数据点上方添加数值标签
        for i, (date_str, ret) in enumerate(zip(filtered_dates, filtered_returns)):
            # 为了防止重叠，上下错开标注。如果当日比前一天涨了，字写在上面；跌了写在下面
            if i == 0:
                offset = 15 if ret >= 0 else -20
            else:
                offset = 15 if ret >= filtered_returns[i-1] else -20
                
            ha = 'right' if i == len(filtered_returns) - 1 else ('left' if i == 0 else 'center')
            t = ax.annotate(f'{ret:.2f}%', 
                        (i, ret),
                        textcoords="offset points",
                        xytext=(0, offset),
                        ha=ha,
                        fontsize=10,
                        fontweight='bold',
                        color=primary_color if ret >= 0 else negative_color)
            if prop: t.set_fontproperties(prop)
        
        # 设置图表标题和标签
        t_title = ax.set_title(f'龙虾{lid}收益曲线图', fontsize=20, fontweight='bold', color=title_color, pad=25)
        if prop: t_title.set_fontproperties(prop)
        
        # 添加小字副标题
        t_sub = ax.text(0.5, 1.02, f'{filtered_dates[0]} ~ {filtered_dates[-1]}', 
                transform=ax.transAxes, ha='center', fontsize=12, color=text_color)
        if prop: t_sub.set_fontproperties(prop)
                
        t_xl = ax.set_xlabel('交易日期', fontsize=14, color=text_color, labelpad=10)
        t_yl = ax.set_ylabel('累计总收益率 (%)', fontsize=14, color=text_color, labelpad=10)
        if prop:
            t_xl.set_fontproperties(prop)
            t_yl.set_fontproperties(prop)
        
        # 美化刻度标签
        ax.tick_params(axis='x', colors=text_color, labelsize=11, rotation=45)
        ax.tick_params(axis='y', colors=text_color, labelsize=11)
        if prop:
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_fontproperties(prop)
        
        # 美化网格和边框
        ax.grid(True, linestyle='-', color=grid_color, alpha=0.8, zorder=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.spines['bottom'].set_visible(True)
        ax.spines['bottom'].set_color(grid_color)
        ax.spines['left'].set_visible(True)
        ax.spines['left'].set_color(grid_color)
        
        # 自动调整布局
        plt.tight_layout()
        
        # 保存图片
        output_file = os.path.join(output_dir, f"lobster_{lid}_return_curve.png")
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close()
        
        print(f"  生成成功! 图表保存在: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='绘制指定龙虾的每日总收益率曲线')
    parser.add_argument('--dir', required=True, help='排名文件夹路径，例如 d:\\codebase\\BitSoulStockSkill\\claw_pool\\ranking\\ranking_1775788853')
    parser.add_argument('--ids', required=True, type=int, nargs='+', help='龙虾ID列表，空格分隔，例如 --ids 710 800')
    parser.add_argument('--start', help='开始日期 (YYYY-MM-DD)，可选')
    parser.add_argument('--end', help='结束日期 (YYYY-MM-DD)，可选')
    
    args = parser.parse_args()
    
    plot_lobster_returns(args.dir, args.ids, args.start, args.end)