"""
EVOLUTION AI - 专业级汽车造型视频生成器
基于真实汽车比例和造型特征生成高质量渲染
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, Polygon, Wedge, Arc
from matplotlib.collections import PatchCollection
import os
from datetime import datetime
import imageio

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class ProfessionalCarVideoGenerator:
    """专业级汽车造型视频生成器"""

    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.fps = 12
        self.duration = 12
        self.total_frames = self.fps * self.duration
        
        # 真实汽车比例参数（基于豪华轿车）
        self.car_params = {
            'length': 4.8,      # 米
            'width': 1.85,     # 米
            'height': 1.45,    # 米
            'wheelbase': 2.8,  # 米
            'front_overhang': 0.9,
            'rear_overhang': 1.1,
            'ground_clearance': 0.15,
            'wheel_radius': 0.35,
            'hood_height': 0.8,
            'roof_height': 1.35,
            'trunk_height': 0.6,
            'a_pillar_angle': 25,  # A柱倾斜角度
            'c_pillar_angle': 35,  # C柱倾斜角度
            'windshield_angle': 65,
            'rear_window_angle': 30,
        }
        
        # 车身颜色方案
        self.colors = {
            'body': '#2C3E50',       # 深灰蓝车身
            'body_highlight': '#34495E',
            'glass': '#85C1E9',      # 浅蓝玻璃
            'glass_tint': '#5DADE2',
            'wheel': '#1C2833',      # 深色轮胎
            'rim': '#BDC3C7',        # 银色轮毂
            'rim_detail': '#ECF0F1',
            'headlight': '#F7DC6F',  # 金色大灯
            'headlight_led': '#F8F9F9',
            'taillight': '#E74C3C',  # 红色尾灯
            'taillight_led': '#F39C12',
            'grille': '#17202A',     # 黑色格栅
            'grille_chrome': '#BDC3C7',
            'mirror': '#2C3E50',
            'mirror_glass': '#85C1E9',
            'door_handle': '#BDC3C7',
            'trim': '#BDC3C7',       # 银色装饰条
            'shadow': '#0D1117',
            'road': '#2D3436',
            'background': '#0A0A1A'
        }
        
        # 构建顺序
        self.build_sequence = [
            {'name': '底盘轮廓', 'start': 0, 'end': 1.0},
            {'name': '前轮', 'start': 1.0, 'end': 1.5},
            {'name': '后轮', 'start': 1.5, 'end': 2.0},
            {'name': '发动机盖', 'start': 2.0, 'end': 3.5},
            {'name': '前大灯', 'start': 3.5, 'end': 4.0},
            {'name': '进气格栅', 'start': 4.0, 'end': 4.5},
            {'name': 'A柱', 'start': 4.5, 'end': 5.5},
            {'name': '前风挡', 'start': 5.5, 'end': 6.5},
            {'name': '车顶', 'start': 6.5, 'end': 7.5},
            {'name': 'C柱', 'start': 7.5, 'end': 8.5},
            {'name': '后风挡', 'start': 8.5, 'end': 9.5},
            {'name': '行李箱', 'start': 9.5, 'end': 10.5},
            {'name': '后尾灯', 'start': 10.5, 'end': 11.0},
            {'name': '前车门', 'start': 11.0, 'end': 12.0},
            {'name': '后车门', 'start': 12.0, 'end': 12.5},
            {'name': '车门玻璃', 'start': 12.5, 'end': 13.0},
            {'name': '后视镜', 'start': 13.0, 'end': 13.5},
            {'name': '装饰细节', 'start': 13.5, 'end': 14.0},
            {'name': '光影渲染', 'start': 14.0, 'end': 15.0},
        ]

    def get_realistic_car_profile(self):
        """获取真实汽车侧视图轮廓点"""
        # 基于豪华轿车（如奔驰E级/宝马5系）的真实比例
        profile_points = {
            # 底盘线
            'ground': [(0, 0), (4.8, 0)],
            
            # 前保险杠
            'front_bumper': [
                (0, 0.15),      # 底部
                (0, 0.35),      # 顶部
                (0.15, 0.4),    # 转角
            ],
            
            # 发动机盖（双曲面造型）
            'hood': [
                (0.15, 0.4),    # 前端
                (0.5, 0.55),    # 中段隆起
                (1.0, 0.65),    # 最高点
                (1.3, 0.68),    # 后端
                (1.4, 0.72),    # 连接A柱
            ],
            
            # A柱（倾斜）
            'a_pillar': [
                (1.4, 0.72),    # 底部
                (1.55, 1.0),    # 中段
                (1.7, 1.25),    # 顶部连接车顶
            ],
            
            # 前风挡
            'windshield': [
                (1.4, 0.72),    # 底部
                (1.7, 1.25),    # 顶部
            ],
            
            # 车顶（微弧形）
            'roof': [
                (1.7, 1.35),    # 前端
                (2.0, 1.38),    # 前段
                (2.5, 1.40),    # 最高点
                (3.0, 1.38),    # 后段
                (3.3, 1.35),    # 连接C柱
            ],
            
            # C柱（倾斜）
            'c_pillar': [
                (3.3, 1.35),    # 顶部
                (3.5, 1.0),     # 中段
                (3.7, 0.65),    # 底部
            ],
            
            # 后风挡
            'rear_window': [
                (3.3, 1.35),    # 顶部
                (3.7, 0.65),    # 底部
            ],
            
            # 行李箱
            'trunk': [
                (3.7, 0.65),    # 前端顶部
                (4.0, 0.55),    # 中段
                (4.3, 0.45),    # 后段
                (4.5, 0.38),    # 后端
            ],
            
            # 后保险杠
            'rear_bumper': [
                (4.5, 0.38),    # 顶部
                (4.65, 0.35),   # 转角
                (4.8, 0.15),    # 底部
            ],
            
            # 车门区域
            'door_front': [
                (1.7, 0.35),    # 底部前端
                (1.7, 0.72),    # 顶部前端（窗线下）
                (2.5, 0.72),    # 顶部后端
                (2.5, 0.35),    # 底部后端
            ],
            
            'door_rear': [
                (2.55, 0.35),   # 底部前端
                (2.55, 0.65),   # 顶部前端（窗线下）
                (3.3, 0.65),    # 顶部后端
                (3.3, 0.35),    # 底部后端
            ],
            
            # 车窗区域
            'window_front': [
                (1.72, 0.74),   # 底部前端
                (1.7, 1.25),    # A柱顶部
                (2.0, 1.35),    # 车顶前端
                (2.48, 0.74),   # 底部后端
            ],
            
            'window_rear': [
                (2.58, 0.67),   # 底部前端
                (2.55, 1.0),    # B柱顶部
                (3.0, 1.38),    # 车顶中段
                (3.28, 0.67),   # 底部后端
            ],
            
            # 车轮位置
            'wheel_front': (0.9, 0.35),
            'wheel_rear': (3.7, 0.35),
        }
        
        return profile_points

    def draw_realistic_wheel(self, ax, center, radius, progress, is_front=True):
        """绘制真实车轮"""
        if progress <= 0:
            return
            
        # 轮胎
        tire_outer = Circle(center, radius * progress, 
                           facecolor=self.colors['wheel'], 
                           edgecolor='#0D1117', linewidth=2, zorder=10)
        ax.add_patch(tire_outer)
        
        # 轮毂外圈
        rim_radius = radius * 0.75 * progress
        rim_outer = Circle(center, rim_radius,
                          facecolor=self.colors['rim'],
                          edgecolor=self.colors['rim_detail'], linewidth=1, zorder=11)
        ax.add_patch(rim_outer)
        
        # 轮毂内圈
        rim_inner_radius = radius * 0.35 * progress
        rim_inner = Circle(center, rim_inner_radius,
                          facecolor=self.colors['rim_detail'],
                          edgecolor=self.colors['rim'], linewidth=1, zorder=12)
        ax.add_patch(rim_inner)
        
        # 轮毂辐条（5辐设计）
        if progress > 0.5:
            num_spokes = 5
            for i in range(num_spokes):
                angle = i * (2 * np.pi / num_spokes)
                x1 = center[0] + rim_inner_radius * np.cos(angle)
                y1 = center[1] + rim_inner_radius * np.sin(angle)
                x2 = center[0] + rim_radius * 0.9 * np.cos(angle)
                y2 = center[1] + rim_radius * 0.9 * np.sin(angle)
                
                spoke = plt.Line2D([x1, x2], [y1, y2],
                                  color=self.colors['rim'], linewidth=2, zorder=13)
                ax.add_line(spoke)
        
        # 轮毂中心盖
        center_cap = Circle(center, radius * 0.15 * progress,
                           facecolor=self.colors['rim_detail'],
                           edgecolor=self.colors['rim'], linewidth=1, zorder=14)
        ax.add_patch(center_cap)

    def draw_realistic_headlight(self, ax, x, y, width, height, progress):
        """绘制真实前大灯（LED造型）"""
        if progress <= 0:
            return
            
        # 大灯外壳
        light_shape = Polygon([
            (x, y),
            (x + width * progress, y),
            (x + width * progress * 0.9, y + height * progress),
            (x + width * progress * 0.1, y + height * progress)
        ], closed=True, facecolor=self.colors['headlight'],
          edgecolor='#F8F9F9', linewidth=1, zorder=15)
        ax.add_patch(light_shape)
        
        # LED灯带
        if progress > 0.3:
            led_y = y + height * progress * 0.3
            led_width = width * progress * 0.7
            
            # 上LED带
            led_top = Rectangle((x + width * progress * 0.15, led_y),
                                led_width, height * progress * 0.15,
                                facecolor=self.colors['headlight_led'],
                                alpha=0.9, zorder=16)
            ax.add_patch(led_top)
            
            # 下LED带
            led_bottom = Rectangle((x + width * progress * 0.15, y + height * progress * 0.6),
                                   led_width, height * progress * 0.15,
                                   facecolor=self.colors['headlight_led'],
                                   alpha=0.9, zorder=16)
            ax.add_patch(led_bottom)
        
        # 投影效果
        if progress > 0.5:
            projector = Circle((x + width * progress * 0.5, y + height * progress * 0.5),
                              height * progress * 0.25,
                              facecolor='#F7DC6F', alpha=0.8, zorder=17)
            ax.add_patch(projector)

    def draw_realistic_taillight(self, ax, x, y, width, height, progress):
        """绘制真实后尾灯"""
        if progress <= 0:
            return
            
        # 尾灯外壳
        light_shape = Polygon([
            (x, y),
            (x + width * progress, y),
            (x + width * progress, y + height * progress),
            (x, y + height * progress)
        ], closed=True, facecolor=self.colors['taillight'],
          edgecolor='#C0392B', linewidth=1, zorder=15)
        ax.add_patch(light_shape)
        
        # LED灯带（贯穿式设计）
        if progress > 0.3:
            led_bar = Rectangle((x + width * progress * 0.1, y + height * progress * 0.4),
                                width * progress * 0.8, height * progress * 0.2,
                                facecolor=self.colors['taillight_led'],
                                alpha=0.9, zorder=16)
            ax.add_patch(led_bar)

    def draw_realistic_grille(self, ax, x, y, width, height, progress):
        """绘制真实进气格栅"""
        if progress <= 0:
            return
            
        # 格栅外框
        grille_frame = FancyBboxPatch((x, y), width * progress, height * progress,
                                      boxstyle="round,pad=0.02",
                                      facecolor=self.colors['grille'],
                                      edgecolor=self.colors['grille_chrome'],
                                      linewidth=2, zorder=14)
        ax.add_patch(grille_frame)
        
        # 格栅网格
        if progress > 0.2:
            num_horizontal = 8
            num_vertical = 4
            
            for i in range(num_horizontal):
                line_y = y + (i + 1) * height * progress / (num_horizontal + 1)
                h_line = plt.Line2D([x + 0.02, x + width * progress - 0.02],
                                   [line_y, line_y],
                                   color='#2C3E50', linewidth=1, zorder=15)
                ax.add_line(h_line)
            
            for i in range(num_vertical):
                line_x = x + (i + 1) * width * progress / (num_vertical + 1)
                v_line = plt.Line2D([line_x, line_x],
                                   [y + 0.02, y + height * progress - 0.02],
                                   color='#2C3E50', linewidth=1, zorder=15)
                ax.add_line(v_line)
        
        # 品牌Logo位置
        if progress > 0.5:
            logo_pos = (x + width * progress * 0.5, y + height * progress * 0.6)
            logo = Circle(logo_pos, height * progress * 0.15,
                         facecolor=self.colors['grille_chrome'],
                         edgecolor='#ECF0F1', linewidth=1, zorder=16)
            ax.add_patch(logo)

    def draw_realistic_body_panel(self, ax, points, progress, color_key='body'):
        """绘制真实车身面板"""
        if progress <= 0:
            return
            
        # 根据进度缩放点
        scaled_points = []
        base_point = points[0]
        
        for point in points:
            dx = point[0] - base_point[0]
            dy = point[1] - base_point[1]
            new_x = base_point[0] + dx * progress
            new_y = base_point[1] + dy * progress
            scaled_points.append((new_x, new_y))
        
        panel = Polygon(scaled_points, closed=True,
                       facecolor=self.colors[color_key],
                       edgecolor=self.colors['body_highlight'],
                       linewidth=1.5, zorder=8)
        ax.add_patch(panel)

    def draw_realistic_glass(self, ax, points, progress):
        """绘制真实玻璃"""
        if progress <= 0:
            return
            
        scaled_points = []
        base_point = points[0]
        
        for point in points:
            dx = point[0] - base_point[0]
            dy = point[1] - base_point[1]
            new_x = base_point[0] + dx * progress
            new_y = base_point[1] + dy * progress
            scaled_points.append((new_x, new_y))
        
        glass = Polygon(scaled_points, closed=True,
                       facecolor=self.colors['glass'],
                       edgecolor=self.colors['glass_tint'],
                       linewidth=1, alpha=0.7, zorder=9)
        ax.add_patch(glass)

    def draw_realistic_mirror(self, ax, x, y, progress):
        """绘制真实后视镜"""
        if progress <= 0:
            return
            
        size = 0.12 * progress
        
        # 镜壳
        mirror_body = FancyBboxPatch((x, y), size, size * 0.6,
                                     boxstyle="round,pad=0.01",
                                     facecolor=self.colors['mirror'],
                                     edgecolor=self.colors['trim'],
                                     linewidth=1, zorder=18)
        ax.add_patch(mirror_body)
        
        # 镜面
        mirror_glass = Rectangle((x + size * 0.1, y + size * 0.1),
                                 size * 0.8, size * 0.4,
                                 facecolor=self.colors['mirror_glass'],
                                 alpha=0.6, zorder=19)
        ax.add_patch(mirror_glass)

    def draw_door_handle(self, ax, x, y, progress):
        """绘制门把手"""
        if progress <= 0:
            return
            
        handle = FancyBboxPatch((x, y), 0.15 * progress, 0.03 * progress,
                               boxstyle="round,pad=0.005",
                               facecolor=self.colors['door_handle'],
                               edgecolor='#ECF0F1', linewidth=0.5, zorder=17)
        ax.add_patch(handle)

    def draw_trim_line(self, ax, start, end, progress):
        """绘制装饰线"""
        if progress <= 0:
            return
            
        trim = plt.Line2D([start[0], start[0] + (end[0] - start[0]) * progress],
                         [start[1], start[1]],
                         color=self.colors['trim'], linewidth=1.5, zorder=16)
        ax.add_line(trim)

    def draw_shadow(self, ax, progress):
        """绘制车身阴影"""
        if progress <= 0:
            return
            
        shadow_height = 0.08 * progress
        shadow = Rectangle((0.2, -shadow_height), 4.4, shadow_height,
                          facecolor=self.colors['shadow'],
                          alpha=0.5, zorder=1)
        ax.add_patch(shadow)

    def draw_road_surface(self, ax):
        """绘制路面"""
        road = Rectangle((-0.5, -0.1), 5.8, 0.1,
                        facecolor=self.colors['road'],
                        edgecolor='#1D1D1D', linewidth=1, zorder=0)
        ax.add_patch(road)

    def get_build_progress(self, current_time, component_idx):
        """获取组件构建进度"""
        comp = self.build_sequence[component_idx]
        if current_time < comp['start']:
            return 0
        elif current_time >= comp['end']:
            return 1
        else:
            return (current_time - comp['start']) / (comp['end'] - comp['start'])

    def get_active_component_idx(self, current_time):
        """获取当前活动组件索引"""
        for i, comp in enumerate(self.build_sequence):
            if current_time < comp['end']:
                return i
        return len(self.build_sequence) - 1

    def generate_frame(self, frame_num):
        """生成单帧"""
        fig, (ax_car, ax_info) = plt.subplots(1, 2, figsize=(12, 6),
                                              gridspec_kw={'width_ratios': [2.5, 1]},
                                              facecolor=self.colors['background'])
        
        ax_car.set_facecolor(self.colors['background'])
        ax_info.set_facecolor(self.colors['background'])
        
        ax_car.set_xlim(-0.5, 5.5)
        ax_car.set_ylim(-0.3, 1.8)
        ax_car.axis('off')
        
        ax_info.set_xlim(0, 6)
        ax_info.set_ylim(0, 7)
        ax_info.axis('off')
        
        current_time = frame_num / self.fps
        total_progress = current_time / self.duration * 100
        
        # 标题
        title = ax_car.text(2.5, 1.65, "EVOLUTION AI", fontsize=22, color='#00d4ff',
                           ha='center', va='center', weight='bold')
        title.set_path_effects([path_effects.withStroke(linewidth=3, foreground='#8b5cf6')])
        
        ax_car.text(2.5, 1.55, "专业级汽车造型生成系统", fontsize=12, color='#8b9dc3', ha='center')
        
        # 绘制路面
        self.draw_road_surface(ax_car)
        
        # 绘制阴影
        self.draw_shadow(ax_car, min(1, total_progress / 10))
        
        # 获取轮廓数据
        profile = self.get_realistic_car_profile()
        
        active_idx = self.get_active_component_idx(current_time)
        
        # 按顺序绘制各部件
        # 底盘轮廓
        if active_idx >= 0:
            progress = self.get_build_progress(current_time, 0)
            chassis_points = [(0, 0.15), (4.8, 0.15)]
            chassis_line = plt.Line2D([0, 4.8 * progress], [0.15, 0.15],
                                     color=self.colors['body'], linewidth=3, zorder=5)
            ax_car.add_line(chassis_line)
        
        # 前轮
        if active_idx >= 1:
            progress = self.get_build_progress(current_time, 1)
            self.draw_realistic_wheel(ax_car, profile['wheel_front'], 
                                     self.car_params['wheel_radius'], progress, True)
        
        # 后轮
        if active_idx >= 2:
            progress = self.get_build_progress(current_time, 2)
            self.draw_realistic_wheel(ax_car, profile['wheel_rear'],
                                     self.car_params['wheel_radius'], progress, False)
        
        # 发动机盖
        if active_idx >= 3:
            progress = self.get_build_progress(current_time, 3)
            self.draw_realistic_body_panel(ax_car, profile['hood'], progress)
            # 前保险杠
            self.draw_realistic_body_panel(ax_car, profile['front_bumper'], progress)
        
        # 前大灯
        if active_idx >= 4:
            progress = self.get_build_progress(current_time, 4)
            self.draw_realistic_headlight(ax_car, 0.05, 0.45, 0.35, 0.18, progress)
        
        # 进气格栅
        if active_idx >= 5:
            progress = self.get_build_progress(current_time, 5)
            self.draw_realistic_grille(ax_car, 0.15, 0.42, 0.8, 0.25, progress)
        
        # A柱
        if active_idx >= 6:
            progress = self.get_build_progress(current_time, 6)
            self.draw_realistic_body_panel(ax_car, profile['a_pillar'], progress)
        
        # 前风挡
        if active_idx >= 7:
            progress = self.get_build_progress(current_time, 7)
            self.draw_realistic_glass(ax_car, profile['windshield'], progress)
        
        # 车顶
        if active_idx >= 8:
            progress = self.get_build_progress(current_time, 8)
            self.draw_realistic_body_panel(ax_car, profile['roof'], progress)
        
        # C柱
        if active_idx >= 9:
            progress = self.get_build_progress(current_time, 9)
            self.draw_realistic_body_panel(ax_car, profile['c_pillar'], progress)
        
        # 后风挡
        if active_idx >= 10:
            progress = self.get_build_progress(current_time, 10)
            self.draw_realistic_glass(ax_car, profile['rear_window'], progress)
        
        # 行李箱
        if active_idx >= 11:
            progress = self.get_build_progress(current_time, 11)
            self.draw_realistic_body_panel(ax_car, profile['trunk'], progress)
            # 后保险杠
            self.draw_realistic_body_panel(ax_car, profile['rear_bumper'], progress)
        
        # 后尾灯
        if active_idx >= 12:
            progress = self.get_build_progress(current_time, 12)
            self.draw_realistic_taillight(ax_car, 4.35, 0.48, 0.35, 0.12, progress)
        
        # 前车门
        if active_idx >= 13:
            progress = self.get_build_progress(current_time, 13)
            self.draw_realistic_body_panel(ax_car, profile['door_front'], progress)
            # 门把手
            self.draw_door_handle(ax_car, 2.1, 0.55, progress)
        
        # 后车门
        if active_idx >= 14:
            progress = self.get_build_progress(current_time, 14)
            self.draw_realistic_body_panel(ax_car, profile['door_rear'], progress)
            # 门把手
            self.draw_door_handle(ax_car, 2.85, 0.50, progress)
        
        # 车门玻璃
        if active_idx >= 15:
            progress = self.get_build_progress(current_time, 15)
            self.draw_realistic_glass(ax_car, profile['window_front'], progress)
            self.draw_realistic_glass(ax_car, profile['window_rear'], progress)
        
        # 后视镜
        if active_idx >= 16:
            progress = self.get_build_progress(current_time, 16)
            self.draw_realistic_mirror(ax_car, 1.65, 0.78, progress)
        
        # 装饰细节
        if active_idx >= 17:
            progress = self.get_build_progress(current_time, 17)
            # 窗线装饰
            self.draw_trim_line(ax_car, (1.7, 0.72), (3.3, 0.65), progress)
            # 底部装饰线
            self.draw_trim_line(ax_car, (0.2, 0.35), (4.6, 0.35), progress)
        
        # 光影渲染
        if active_idx >= 18:
            progress = self.get_build_progress(current_time, 18)
            # 车身高光
            highlight_line = plt.Line2D([0.5, 3.5 * progress], [0.6, 0.8],
                                       color='#FFFFFF', linewidth=2, alpha=0.3 * progress, zorder=20)
            ax_car.add_line(highlight_line)
        
        # 信息面板
        ax_info.text(0.5, 6.5, "构建状态", fontsize=14, color='#8b9dc3', weight='bold')
        
        current_comp = self.build_sequence[active_idx]['name']
        ax_info.text(0.5, 6.0, current_comp, fontsize=16, color='#00d4ff', weight='bold')
        
        # 主进度条
        bg_bar = Rectangle((0.5, 5.2), 5, 0.25, facecolor='#1a1a3e', edgecolor='#333333')
        ax_info.add_patch(bg_bar)
        
        fill_bar = Rectangle((0.5, 5.2), 5 * total_progress / 100, 0.25, facecolor='#00d4ff')
        ax_info.add_patch(fill_bar)
        
        ax_info.text(5.7, 5.35, f"{total_progress:.1f}%", fontsize=12, color='white')
        
        # 时间信息
        elapsed = current_time
        remaining = self.duration - elapsed
        ax_info.text(0.5, 4.8, f"已用时: {int(elapsed)}秒", fontsize=10, color='#8b9dc3')
        ax_info.text(3.5, 4.8, f"剩余: {int(remaining)}秒", fontsize=10, color='#00ff88')
        
        # 统计信息
        stats = [
            {"label": "部件数", "value": active_idx + 1, "color": '#00d4ff'},
            {"label": "曲面数", "value": (active_idx + 1) * 2, "color": '#8b5cf6'},
            {"label": "质量分", "value": "--" if total_progress < 90 else f"{95 + int(total_progress/20)}", "color": '#00ff88'},
            {"label": "A级", "value": "检测中" if total_progress < 90 else "通过", "color": '#ffc107'}
        ]
        
        for i, stat in enumerate(stats):
            card = FancyBboxPatch((0.5 + i * 1.25, 3.8), 1.1, 0.6,
                                 boxstyle="round,pad=0.02",
                                 facecolor='#1a1a3e', edgecolor='#333333')
            ax_info.add_patch(card)
            ax_info.text(0.55 + i * 1.25, 4.15, str(stat['value']), fontsize=11,
                        color=stat['color'], weight='bold')
            ax_info.text(0.55 + i * 1.25, 3.95, stat['label'], fontsize=8, color='#8b9dc3')
        
        # 构建清单
        ax_info.text(0.5, 3.2, "构建清单", fontsize=12, color='#8b9dc3', weight='bold')
        
        for i, comp in enumerate(self.build_sequence):
            y_pos = 2.9 - i * 0.15
            if y_pos < 0.3:
                break
            
            if i <= active_idx:
                ax_info.text(0.5, y_pos, f"[OK] {comp['name']}", fontsize=9, color='#00ff88')
            else:
                ax_info.text(0.5, y_pos, f"[--] {comp['name']}", fontsize=9, color='#444444')
        
        plt.tight_layout()
        return fig

    def generate_video(self):
        """生成视频"""
        print("=" * 70)
        print("EVOLUTION AI 专业级汽车造型视频生成")
        print("=" * 70)
        
        output_file = os.path.join(self.output_dir,
                                  f"EVOLUTION_AI_PROFESSIONAL_CAR_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
        
        print(f"\n输出文件: {output_file}")
        print(f"视频时长: {self.duration}秒")
        print(f"帧率: {self.fps} fps")
        print(f"总帧数: {self.total_frames}")
        print("\n汽车参数:")
        print(f"  • 车身长度: {self.car_params['length']}m")
        print(f"  • 车身宽度: {self.car_params['width']}m")
        print(f"  • 车身高度: {self.car_params['height']}m")
        print(f"  • 轴距: {self.car_params['wheelbase']}m")
        
        frames = []
        for frame_num in range(self.total_frames):
            if frame_num % 40 == 0:
                progress = frame_num / self.total_frames * 100
                print(f"  生成帧: {frame_num}/{self.total_frames} ({progress:.1f}%)")
            
            fig = self.generate_frame(frame_num)
            
            fig.canvas.draw()
            img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
            frames.append(img)
            
            plt.close(fig)
        
        print(f"  生成帧: {self.total_frames}/{self.total_frames} (100%)")
        
        print("\n正在保存视频...")
        imageio.mimsave(output_file, frames, fps=self.fps, codec='libx264', quality=9)
        
        print(f"\n✓ 视频生成完成: {output_file}")
        
        return output_file

def main():
    generator = ProfessionalCarVideoGenerator()
    output_file = generator.generate_video()
    print(f"\n视频已保存到: {output_file}")

if __name__ == '__main__':
    main()