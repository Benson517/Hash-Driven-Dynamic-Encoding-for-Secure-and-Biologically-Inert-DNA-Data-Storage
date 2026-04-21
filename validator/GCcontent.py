import csv
import hashlib
import random
import json
import time
import matplotlib.pyplot as plt
from collections import defaultdict
try:
    import matplotlib

    matplotlib.use('Agg')  # 使用非交互式后端
    import matplotlib.pyplot as plt
except ImportError:
    print("错误：请安装 matplotlib (pip install matplotlib)。")
    exit()



# ==========================================
# GC 分布可视化函数（模仿论文图）
# ==========================================
def plot_gc_distribution(gc_stats):


    # --- 1. 保存所有 GC 含量数据到 CSV ---
    csv_filename = 'gc_content_data.csv'
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Sample Index', 'GC Content (%)']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for i, gc in enumerate(gc_stats):
                writer.writerow({
                    'Sample Index': i + 1,
                    'GC Content (%)': f"{gc:.2f}" # 格式化到两位小数
                })
        print(f"\n所有 GC 含量数据已保存至 CSV 文件：{csv_filename}")
    except Exception as e:
        print(f"保存 GC 数据到 CSV 时出错: {e}")
    # --- 结束 CSV 保存逻辑 ---


    """
    随机抽取 GC 含量样本（最多 1000 个），绘制其分布散点图（GC含量 vs 样本序号）。
    """
    # 随机抽取 1000 个样本 (如果数量足够)
    max_samples = 100
    if len(gc_stats) >= max_samples:
        sampled_gc = random.sample(gc_stats, max_samples)
    else:
        sampled_gc = gc_stats

    # 定义 GC 区间、颜色和顺序
    gc_bins = {
        '<38%': (0, 38, '#00008B'),  # 深蓝色
        '38-45%': (38, 45, '#4169E1'),  # 皇家蓝
        '46-54%': (46, 54, '#90EE90'),  # 浅绿色 (目标区间)
        '55-62%': (55, 62, '#FFA07A'),  # 浅珊瑚色
        '>62%': (62, 101, '#FF0000')  # 红色
    }
    ordered_labels = ['<38%', '38-45%', '46-54%', '55-62%', '>62%']

    # 准备绘图数据：按 GC 范围划分数据点
    plot_data = defaultdict(lambda: {'x': [], 'y': []})

    # 重新定义 x 轴：从 1 到 len(sampled_gc)
    for i, gc in enumerate(sampled_gc):
        for label in ordered_labels:
            low, high, _ = gc_bins[label]
            if low <= gc < high:
                plot_data[label]['x'].append(i + 1)
                plot_data[label]['y'].append(gc)
                break

    # 绘图
    plt.figure(figsize=(10, 6))
    ax = plt.gca()

    # 绘制水平范围线 (突出目标区域 46-54%)
    ax.axhspan(46, 54, color='#90EE90', alpha=0.2, label='Target GC Range (46%-54%)')

    # 绘制散点图
    # 按照顺序绘制，确保图例和颜色一致
    for label in ordered_labels:
        data = plot_data[label]
        color = gc_bins[label][2]
        # 使用 scatter 绘制点，确保每个范围都是一个独立的图例项
        ax.scatter(data['x'], data['y'],
                   color=color,
                   s=10,  # 减小点的大小
                   alpha=0.7,
                   label=f'GC: {label} ({len(data["x"])} Samples)')

    # 设置标题和坐标轴标签
    ax.set_title(f'GC Content per Sample (Random {len(sampled_gc)} Records)', fontsize=14)
    ax.set_xlabel('Sample Index (Record Count)', fontsize=12)
    ax.set_ylabel('GC Content (%)', fontsize=12)

    # 限制 Y 轴范围
    ax.set_ylim(0, 100)

    # 添加网格
    plt.grid(True, linestyle='--', alpha=0.5)

    plt.legend(loc='lower right', fontsize=10)
    plt.tight_layout()
    plot_filename = 'gc_content_scatter_sampled.png'  # 更改文件名以区分散点图
    plt.savefig(plot_filename)
    print(f"\nGC 含量散点可视化已保存至：{plot_filename}")

# --- 辅助函数 ---
def bytes_to_binary_str(byte_data):
    return ''.join(f'{byte:08b}' for byte in byte_data)
