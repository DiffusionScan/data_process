import os
import open3d as o3d
import shutil
import numpy as np
import logging
from colorama import Fore, Style, init
import tkinter as tk
from tkinter import messagebox

# 初始化 colorama
init(autoreset=True)

# 设置日志记录器
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': Fore.BLUE,
        'INFO': Fore.BLUE,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
        'DIAGONAL': Fore.GREEN,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, Fore.WHITE)
        if 'Diagonal length of the 3D model' in record.getMessage():
            color = self.COLORS['DIAGONAL']  # 特殊处理
        return color + super().format(record) + Style.RESET_ALL

formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# 定义源文件夹和目标文件夹
start_num = 0  # 设置从第几个文件夹开始显示
source_folder = 'G:/mesh_data/abc_0002_obj_v00'
destination_folder = './destination_folder'

# 创建目标文件夹
os.makedirs(destination_folder, exist_ok=True)

# 创建分类文件夹
categories = ['螺丝', '螺母', '连接件', '异形件']
for category in categories:
    os.makedirs(os.path.join(destination_folder, category), exist_ok=True)

# 初始化 Open3D 可视化器
vis = o3d.visualization.Visualizer()
vis.create_window(width=1000, height=800)  # 设置窗口大小

# 当前处理的文件夹索引
current_index = start_num

def load_next_model():
    global current_index, current_dir_path, current_obj_file
    
    # 获取当前文件夹路径
    for root, dirs, files in os.walk(source_folder):
        if current_index >= len(dirs):
            return
        
        dir_name = dirs[current_index]
        current_dir_path = os.path.join(root, dir_name)
        current_index += 1
        
        obj_files = [f for f in os.listdir(current_dir_path) if f.endswith('.obj')]
        
        if not obj_files:
            logger.info(f"No .obj file found in {current_dir_path}. Skipping...")
            load_next_model()
            return
        
        current_obj_file = os.path.join(current_dir_path, obj_files[0])
        
        try:
            mesh = o3d.io.read_triangle_mesh(current_obj_file)
            logger.info(f"Loaded 3D model from {current_obj_file}")
        except Exception as e:
            logger.error(f"Failed to load 3D model from {current_obj_file}: {e}")
            load_next_model()
            return
        
        # 计算对角线长度
        bounds = mesh.get_axis_aligned_bounding_box()
        diagonal_length = np.linalg.norm(bounds.get_extent())
        logger.info(f"Diagonal length of the 3D model: {diagonal_length / 1000:.2f} m")
        
        # 根据高度设置颜色
        z_values = np.asarray(mesh.vertices)[:, 2]
        min_z, max_z = z_values.min(), z_values.max()

        # 归一化 Z 值到 [0, 1] 区间
        normalized_heights = (z_values - min_z) / (max_z - min_z)

        # 创建颜色映射
        colors = np.zeros((len(mesh.vertices), 3))  # 初始化颜色数组
        for i in range(len(mesh.vertices)):
            # 根据归一化高度设置颜色
            colors[i] = [normalized_heights[i], 0.5, 1 - normalized_heights[i]]  # 渐变色，从蓝色到红色

        mesh.vertex_colors = o3d.utility.Vector3dVector(colors)

        # 显示模型
        vis.clear_geometries()
        vis.add_geometry(mesh)
        vis.poll_events()
        vis.update_renderer()
        
        # 更新当前文件名标签
        current_file_label.config(text=f"Current File: {os.path.basename(current_obj_file)}")

def classify_model(category):
    global current_dir_path, current_obj_file
    
    if current_dir_path and current_obj_file:
        new_dir_name = f"{source_folder.split('/')[-1].split('_')[0]}_{source_folder.split('/')[-1].split('_')[1]}_{os.path.basename(current_dir_path)}"
        new_dir_path = os.path.join(destination_folder, category, new_dir_name)
        
        if os.path.exists(new_dir_path):
            shutil.rmtree(new_dir_path)
        
        shutil.copytree(current_dir_path, new_dir_path)
        new_obj_file = os.path.join(new_dir_path, f"{new_dir_name}.obj")
        os.rename(os.path.join(new_dir_path, os.path.basename(current_obj_file)), new_obj_file)
        
        logger.info(f"Classified {current_dir_path} as {category}")
    
    load_next_model()

# 创建主窗口
root = tk.Tk()
root.title("3D Model Classifier")

# 创建标签显示当前文件名
current_file_label = tk.Label(root, text=f"Current File: ", font=("Arial", 12))
current_file_label.pack(pady=10)

# 创建按钮
for category in categories:
    button = tk.Button(root, text=category, command=lambda cat=category: classify_model(cat))
    button.pack(side=tk.LEFT, padx=10, pady=10)

next_button = tk.Button(root, text="下一件", command=load_next_model)
next_button.pack(side=tk.LEFT, padx=10, pady=10)

# 加载第一个模型
load_next_model()

# 运行主循环
root.mainloop()

# 关闭 Open3D 可视化器
vis.destroy_window()