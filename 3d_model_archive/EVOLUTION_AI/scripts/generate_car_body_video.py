"""
EVOLUTION AI - 完整汽车造型DEMO视频生成器
展示完整车身造型：发动机盖+前挡风+车顶+后挡风+行李箱+四门分缝+前后大灯+进气格栅+轮拱+四轮+后视镜+玻璃
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch
import os
from datetime import datetime
import json
import imageio

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class CarBodyVideoGenerator:
    """完整汽车造型视频生成器"""

    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.fps = 15
        self.duration = 12
        self.total_frames = self.fps * self.duration
        self.fig_size = (14, 7)
        
        self.car_params = {
            'length': 4800,
            'width': 1850,
            'height': 1450,
            'wheelbase': 2800,
            'ground_clearance': 150
        }
        
        self.component_colors = {
            'body': '#c0c0c0',
            'glass': '#87CEEB',
            'bumper': '#808080',
            'grille': '#1a1a1a',
            'headlight': '#ffffff',
            'taillight': '#ff0000',
            'wheel': '#222222',
            'rim': '#666666',
            'mirror': '#c0c0c0',
            'mirror_glass': '#87CEEB',
            'pillar': '#1a1a1a',
            'fender': '#c0c0c0',
            'seam': '#111111'
        }
        
        self.components_sequence = [
            {'name': '底盘', 'start': 0, 'duration': 1},
            {'name': '前保险杠', 'start': 1, 'duration': 0.5},
            {'name': '进气格栅', 'start': 1.5, 'duration': 0.5},
            {'name': '前大灯', 'start': 2, 'duration': 0.5},
            {'name': '发动机盖', 'start': 2.5, 'duration': 1},
            {'name': '前风挡', 'start': 3.5, 'duration': 0.5},
            {'name': '车顶', 'start': 4, 'duration': 1},
            {'name': '后风挡', 'start': 5, 'duration': 0.5},
            {'name': '行李箱', 'start': 5.5, 'duration': 0.5},
            {'name': '后保险杠', 'start': 6, 'duration': 0.5},
            {'name': '后尾灯', 'start': 6.5, 'duration': 0.5},
            {'name': '翼子板', 'start': 7, 'duration': 0.5},
            {'name': '车门', 'start': 7.5, 'duration': 1},
            {'name': '立柱', 'start': 8.5, 'duration': 0.5},
            {'name': '后视镜', 'start': 9, 'duration': 0.5},
            {'name': '车轮', 'start': 9.5, 'duration': 0.5},
            {'name': '分缝', 'start': 10, 'duration': 0.5},
            {'name': '完成', 'start': 10.5, 'duration': 1.5}
        ]

    def draw_car_body(self, ax, progress):
        """绘制汽车车身"""
        scale = 0.001
        x_offset = 1
        y_offset = 1
        
        car_length = self.car_params['length'] * scale
        car_width = self.car_params['width'] * scale
        ground_y = y_offset + self.car_params['ground_clearance'] * scale
        
        active_idx = 0
        for i, comp in enumerate(self.components_sequence):
            if progress >= comp['start']:
                active_idx = i
        
        if active_idx >= 0:
            self.draw_chassis(ax, x_offset, ground_y, car_length, car_width, 
                             progress > self.components_sequence[0]['start'])
        
        if active_idx >= 1:
            self.draw_bumper_front(ax, x_offset, ground_y, car_width,
                                  self.get_component_progress(progress, 1))
        
        if active_idx >= 2:
            self.draw_grille(ax, x_offset + 0.2, ground_y + 0.3,
                             self.get_component_progress(progress, 2))
        
        if active_idx >= 3:
            self.draw_headlights(ax, x_offset + 0.15, ground_y + 0.4,
                                self.get_component_progress(progress, 3))
        
        if active_idx >= 4:
            self.draw_hood(ax, x_offset + 0.1, ground_y + 0.4, car_length * 0.3, car_width * 0.85,
                          self.get_component_progress(progress, 4))
        
        if active_idx >= 5:
            self.draw_windshield(ax, x_offset + 0.35, ground_y + 0.8,
                                 self.get_component_progress(progress, 5))
        
        if active_idx >= 6:
            self.draw_roof(ax, x_offset + 0.35, ground_y + 1.2, car_length * 0.35, car_width * 0.85,
                          self.get_component_progress(progress, 6))
        
        if active_idx >= 7:
            self.draw_rear_window(ax, x_offset + 0.7, ground_y + 0.9,
                                  self.get_component_progress(progress, 7))
        
        if active_idx >= 8:
            self.draw_trunk(ax, x_offset + 0.75, ground_y + 0.5, car_length * 0.2, car_width * 0.8,
                           self.get_component_progress(progress, 8))
        
        if active_idx >= 9:
            self.draw_bumper_rear(ax, x_offset + car_length - 0.2, ground_y, car_width,
                                 self.get_component_progress(progress, 9))
        
        if active_idx >= 10:
            self.draw_taillights(ax, x_offset + car_length - 0.3, ground_y + 0.4,
                                self.get_component_progress(progress, 10))
        
        if active_idx >= 11:
            self.draw_fenders(ax, x_offset, ground_y, car_length,
                             self.get_component_progress(progress, 11))
        
        if active_idx >= 12:
            self.draw_doors(ax, x_offset + 0.4, ground_y + 0.25, car_length * 0.3, car_width,
                           self.get_component_progress(progress, 12))
        
        if active_idx >= 13:
            self.draw_pillars(ax, x_offset, ground_y + 0.8, car_length,
                             self.get_component_progress(progress, 13))
        
        if active_idx >= 14:
            self.draw_mirrors(ax, x_offset + 0.55, ground_y + 0.85,
                             self.get_component_progress(progress, 14))
        
        if active_idx >= 15:
            self.draw_wheels(ax, x_offset, ground_y, car_length,
                            self.get_component_progress(progress, 15))
        
        if active_idx >= 16:
            self.draw_seams(ax, x_offset + 0.65, ground_y + 0.3,
                           self.get_component_progress(progress, 16))
        
        return self.components_sequence[active_idx]['name']

    def get_component_progress(self, current_time, component_idx):
        """获取组件显示进度"""
        comp = self.components_sequence[component_idx]
        elapsed = current_time - comp['start']
        return min(1.0, max(0.0, elapsed / comp['duration']))

    def draw_chassis(self, ax, x, y, length, width, show):
        """绘制底盘"""
        if not show: return
        chassis = Rectangle((x, y), length, 0.05, facecolor='#333333', zorder=1)
        ax.add_patch(chassis)
        
        ground_line = plt.Line2D([x - 0.5, x + length + 0.5], [y, y], 
                                color='#444444', linestyle='--', linewidth=1)
        ax.add_line(ground_line)

    def draw_bumper_front(self, ax, x, y, width, progress):
        """绘制前保险杠"""
        h = 0.25 * progress
        bumper = Rectangle((x, y + 0.05), 0.15, h, facecolor=self.component_colors['bumper'], zorder=2)
        ax.add_patch(bumper)
        
        lip = Rectangle((x - 0.02, y + h - 0.03), 0.19, 0.03, facecolor='#444444', zorder=3)
        ax.add_patch(lip)

    def draw_grille(self, ax, x, y, progress):
        """绘制进气格栅"""
        h = 0.3 * progress
        grille = Rectangle((x, y), 1.0, h, facecolor=self.component_colors['grille'], zorder=3)
        ax.add_patch(grille)
        
        for i in range(7):
            line = plt.Line2D([x, x + 1.0], [y + (i + 1) * h / 8, y + (i + 1) * h / 8],
                            color='#444444', linewidth=1)
            ax.add_line(line)
        
        logo = Circle((x + 0.5, y + h * 0.6), 0.05, facecolor='#00d4ff', zorder=4)
        ax.add_patch(logo)

    def draw_headlights(self, ax, x, y, progress):
        """绘制前大灯"""
        w = 0.4 * progress
        
        hl_left = FancyBboxPatch((x, y), w, 0.12, boxstyle="round,pad=0.01",
                                facecolor=self.component_colors['headlight'], zorder=4)
        ax.add_patch(hl_left)
        
        hl_right = FancyBboxPatch((x + 0.7, y), w, 0.12, boxstyle="round,pad=0.01",
                                 facecolor=self.component_colors['headlight'], zorder=4)
        ax.add_patch(hl_right)
        
        inner_left = Rectangle((x + 0.02, y + 0.02), w * 0.6, 0.08, 
                               facecolor='#00ffff', alpha=0.8, zorder=5)
        ax.add_patch(inner_left)
        
        inner_right = Rectangle((x + 0.72, y + 0.02), w * 0.6, 0.08,
                                facecolor='#00ffff', alpha=0.8, zorder=5)
        ax.add_patch(inner_right)

    def draw_hood(self, ax, x, y, length, width, progress):
        """绘制发动机盖"""
        xs = [x, x + length * progress, x + length * progress * 0.95, x + length * 0.05]
        ys = [y, y + 0.15, y + 0.3, y + 0.1]
        
        hood = plt.Polygon(list(zip(xs, ys)), closed=True, 
                          facecolor=self.component_colors['body'], zorder=5)
        ax.add_patch(hood)
        
        center_line = plt.Line2D([x + length * 0.05, x + length * 0.5 * progress],
                                [y + 0.12, y + 0.2], color='#888888', linewidth=1)
        ax.add_line(center_line)

    def draw_windshield(self, ax, x, y, progress):
        """绘制前风挡"""
        h = 0.6 * progress
        xs = [x, x + 0.15 * progress, x + 0.1, x]
        ys = [y, y + h, y + h * 0.9, y + 0.05]
        
        ws = plt.Polygon(list(zip(xs, ys)), closed=True, 
                        facecolor=self.component_colors['glass'], alpha=0.5, zorder=6)
        ax.add_patch(ws)

    def draw_roof(self, ax, x, y, length, width, progress):
        """绘制车顶"""
        roof_width = width * progress
        half_width = roof_width / 2
        
        xs = [x, x + length * progress, x + length * progress * 0.98, x + 0.02]
        ys = [y, y + 0.05, y + 0.2, y + 0.18]
        
        roof = plt.Polygon(list(zip(xs, ys)), closed=True, 
                          facecolor=self.component_colors['body'], zorder=6)
        ax.add_patch(roof)

    def draw_rear_window(self, ax, x, y, progress):
        """绘制后风挡"""
        h = 0.5 * progress
        xs = [x, x + 0.1 * progress, x + 0.12 * progress, x + 0.02]
        ys = [y, y + h, y + h * 0.8, y + 0.05]
        
        rw = plt.Polygon(list(zip(xs, ys)), closed=True, 
                        facecolor=self.component_colors['glass'], alpha=0.5, zorder=6)
        ax.add_patch(rw)

    def draw_trunk(self, ax, x, y, length, width, progress):
        """绘制行李箱"""
        xs = [x, x + length * progress, x + length * progress * 0.98, x + 0.02]
        ys = [y, y + 0.05, y + 0.25, y + 0.15]
        
        trunk = plt.Polygon(list(zip(xs, ys)), closed=True, 
                           facecolor=self.component_colors['body'], zorder=5)
        ax.add_patch(trunk)

    def draw_bumper_rear(self, ax, x, y, width, progress):
        """绘制后保险杠"""
        h = 0.25 * progress
        bumper = Rectangle((x, y + 0.05), 0.15, h, facecolor=self.component_colors['bumper'], zorder=2)
        ax.add_patch(bumper)
        
        lip = Rectangle((x - 0.02, y + h - 0.03), 0.19, 0.03, facecolor='#444444', zorder=3)
        ax.add_patch(lip)

    def draw_taillights(self, ax, x, y, progress):
        """绘制后尾灯"""
        w = 0.35 * progress
        
        tl_left = FancyBboxPatch((x, y), w, 0.15, boxstyle="round,pad=0.01",
                                facecolor=self.component_colors['taillight'], zorder=4)
        ax.add_patch(tl_left)
        
        tl_right = FancyBboxPatch((x + 0.75, y), w, 0.15, boxstyle="round,pad=0.01",
                                 facecolor=self.component_colors['taillight'], zorder=4)
        ax.add_patch(tl_right)
        
        reverse_left = Rectangle((x + w - 0.1, y + 0.03), 0.08, 0.06,
                                facecolor='#ffffff', zorder=5)
        ax.add_patch(reverse_left)
        
        reverse_right = Rectangle((x + 0.75 + w - 0.1, y + 0.03), 0.08, 0.06,
                                 facecolor='#ffffff', zorder=5)
        ax.add_patch(reverse_right)

    def draw_fenders(self, ax, x, y, length, progress):
        """绘制翼子板"""
        fender_width = 0.4 * progress
        
        front_left = FancyBboxPatch((x + 0.7, y + 0.35), 0.3, fender_width,
                                   boxstyle="round,pad=0.05",
                                   facecolor=self.component_colors['fender'], zorder=4)
        ax.add_patch(front_left)
        
        front_right = FancyBboxPatch((x + 0.7, y + 0.35 + 0.45), 0.3, fender_width,
                                    boxstyle="round,pad=0.05",
                                    facecolor=self.component_colors['fender'], zorder=4)
        ax.add_patch(front_right)
        
        rear_left = FancyBboxPatch((x + length - 0.5, y + 0.3), 0.3, fender_width,
                                  boxstyle="round,pad=0.05",
                                  facecolor=self.component_colors['fender'], zorder=4)
        ax.add_patch(rear_left)
        
        rear_right = FancyBboxPatch((x + length - 0.5, y + 0.3 + 0.45), 0.3, fender_width,
                                   boxstyle="round,pad=0.05",
                                   facecolor=self.component_colors['fender'], zorder=4)
        ax.add_patch(rear_right)

    def draw_doors(self, ax, x, y, length, width, progress):
        """绘制车门"""
        door_height = 0.65 * progress
        
        front_door_left = Rectangle((x, y), 0.5, door_height, 
                                   facecolor=self.component_colors['body'], zorder=5)
        ax.add_patch(front_door_left)
        
        front_door_right = Rectangle((x, y + 0.45), 0.5, door_height,
                                    facecolor=self.component_colors['body'], zorder=5)
        ax.add_patch(front_door_right)
        
        rear_door_left = Rectangle((x + 0.52, y), 0.45, door_height * 0.95,
                                  facecolor=self.component_colors['body'], zorder=5)
        ax.add_patch(rear_door_left)
        
        rear_door_right = Rectangle((x + 0.52, y + 0.45), 0.45, door_height * 0.95,
                                   facecolor=self.component_colors['body'], zorder=5)
        ax.add_patch(rear_door_right)
        
        window_height = door_height * 0.4
        win_front_left = Rectangle((x + 0.05, y + door_height - window_height), 0.4, window_height,
                                  facecolor=self.component_colors['glass'], alpha=0.5, zorder=6)
        ax.add_patch(win_front_left)
        
        win_front_right = Rectangle((x + 0.05, y + 0.45 + door_height - window_height), 0.4, window_height,
                                   facecolor=self.component_colors['glass'], alpha=0.5, zorder=6)
        ax.add_patch(win_front_right)
        
        win_rear_left = Rectangle((x + 0.57, y + door_height * 0.95 - window_height * 0.9), 0.38, window_height * 0.9,
                                 facecolor=self.component_colors['glass'], alpha=0.5, zorder=6)
        ax.add_patch(win_rear_left)
        
        win_rear_right = Rectangle((x + 0.57, y + 0.45 + door_height * 0.95 - window_height * 0.9), 0.38, window_height * 0.9,
                                  facecolor=self.component_colors['glass'], alpha=0.5, zorder=6)
        ax.add_patch(win_rear_right)

    def draw_pillars(self, ax, x, y, length, progress):
        """绘制立柱"""
        pillar_width = 0.06 * progress
        
        A_pillar_left = Rectangle((x + 0.35, y), pillar_width, 0.4,
                                 facecolor=self.component_colors['pillar'], zorder=5)
        ax.add_patch(A_pillar_left)
        
        A_pillar_right = Rectangle((x + 0.35, y + 0.45), pillar_width, 0.4,
                                  facecolor=self.component_colors['pillar'], zorder=5)
        ax.add_patch(A_pillar_right)
        
        B_pillar_left = Rectangle((x + 0.92, y + 0.1), pillar_width, 0.55,
                                 facecolor=self.component_colors['pillar'], zorder=5)
        ax.add_patch(B_pillar_left)
        
        B_pillar_right = Rectangle((x + 0.92, y + 0.55), pillar_width, 0.55,
                                  facecolor=self.component_colors['pillar'], zorder=5)
        ax.add_patch(B_pillar_right)
        
        C_pillar_left = Rectangle((x + length * 0.65, y + 0.15), pillar_width, 0.4,
                                 facecolor=self.component_colors['pillar'], zorder=5)
        ax.add_patch(C_pillar_left)
        
        C_pillar_right = Rectangle((x + length * 0.65, y + 0.6), pillar_width, 0.4,
                                  facecolor=self.component_colors['pillar'], zorder=5)
        ax.add_patch(C_pillar_right)

    def draw_mirrors(self, ax, x, y, progress):
        """绘制后视镜"""
        mirror_size = 0.1 * progress
        
        mirror_left = FancyBboxPatch((x, y), mirror_size, mirror_size * 0.8,
                                    boxstyle="round,pad=0.01",
                                    facecolor=self.component_colors['mirror'], zorder=7)
        ax.add_patch(mirror_left)
        
        mirror_glass_left = Rectangle((x + mirror_size * 0.1, y + mirror_size * 0.1),
                                     mirror_size * 0.6, mirror_size * 0.5,
                                     facecolor=self.component_colors['mirror_glass'], alpha=0.6, zorder=8)
        ax.add_patch(mirror_glass_left)
        
        mirror_right = FancyBboxPatch((x, y + 0.45 + 0.1), mirror_size, mirror_size * 0.8,
                                     boxstyle="round,pad=0.01",
                                     facecolor=self.component_colors['mirror'], zorder=7)
        ax.add_patch(mirror_right)
        
        mirror_glass_right = Rectangle((x + mirror_size * 0.1, y + 0.45 + 0.1 + mirror_size * 0.1),
                                      mirror_size * 0.6, mirror_size * 0.5,
                                      facecolor=self.component_colors['mirror_glass'], alpha=0.6, zorder=8)
        ax.add_patch(mirror_glass_right)

    def draw_wheels(self, ax, x, y, length, progress):
        """绘制车轮"""
        wheel_radius = 0.2 * progress
        
        front_wheel_left = Circle((x + 0.9, y), wheel_radius, 
                                  facecolor=self.component_colors['wheel'], zorder=3)
        ax.add_patch(front_wheel_left)
        
        front_wheel_right = Circle((x + 0.9, y + 0.9), wheel_radius,
                                   facecolor=self.component_colors['wheel'], zorder=3)
        ax.add_patch(front_wheel_right)
        
        rear_wheel_left = Circle((x + length - 0.5, y), wheel_radius,
                                 facecolor=self.component_colors['wheel'], zorder=3)
        ax.add_patch(rear_wheel_left)
        
        rear_wheel_right = Circle((x + length - 0.5, y + 0.9), wheel_radius,
                                  facecolor=self.component_colors['wheel'], zorder=3)
        ax.add_patch(rear_wheel_right)
        
        rim_radius = wheel_radius * 0.6
        front_rim_left = Circle((x + 0.9, y), rim_radius,
                               facecolor=self.component_colors['rim'], zorder=4)
        ax.add_patch(front_rim_left)
        
        front_rim_right = Circle((x + 0.9, y + 0.9), rim_radius,
                                facecolor=self.component_colors['rim'], zorder=4)
        ax.add_patch(front_rim_right)
        
        rear_rim_left = Circle((x + length - 0.5, y), rim_radius,
                              facecolor=self.component_colors['rim'], zorder=4)
        ax.add_patch(rear_rim_left)
        
        rear_rim_right = Circle((x + length - 0.5, y + 0.9), rim_radius,
                               facecolor=self.component_colors['rim'], zorder=4)
        ax.add_patch(rear_rim_right)

    def draw_seams(self, ax, x, y, progress):
        """绘制车门分缝"""
        seam_height = 0.7 * progress
        
        seam = plt.Line2D([x, x], [y, y + seam_height], 
                         color=self.component_colors['seam'], linewidth=2, zorder=8)
        ax.add_line(seam)
        
        door_handle_left = Circle((x - 0.2, y + seam_height * 0.5), 0.02,
                                 facecolor='#666666', zorder=8)
        ax.add_patch(door_handle_left)
        
        door_handle_right = Circle((x - 0.2, y + 0.45 + seam_height * 0.5), 0.02,
                                  facecolor='#666666', zorder=8)
        ax.add_patch(door_handle_right)

    def draw_progress_bar(self, ax, progress, x, y, width, height, color):
        """绘制进度条"""
        bg = Rectangle((x, y), width, height, facecolor='#1a1a3e', edgecolor='#333333')
        ax.add_patch(bg)
        
        fill_width = width * progress
        fill = Rectangle((x, y), fill_width, height, facecolor=color)
        ax.add_patch(fill)

    def generate_frame(self, frame_num):
        """生成单帧"""
        fig, (ax_main, ax_info) = plt.subplots(1, 2, figsize=self.fig_size, 
                                              gridspec_kw={'width_ratios': [2, 1]},
                                              facecolor='#0a0a1a')
        
        ax_main.set_facecolor('#0a0a1a')
        ax_info.set_facecolor('#0a0a1a')
        
        ax_main.set_xlim(0, 7)
        ax_main.set_ylim(0, 3)
        ax_main.axis('off')
        
        ax_info.set_xlim(0, 6)
        ax_info.set_ylim(0, 6)
        ax_info.axis('off')
        
        current_time = frame_num / self.fps
        total_progress = current_time / self.duration * 100
        
        title = ax_main.text(3.5, 2.8, "EVOLUTION AI", fontsize=18, color='#00d4ff',
                            ha='center', va='center', weight='bold')
        title.set_path_effects([path_effects.withStroke(linewidth=2, foreground='#8b5cf6')])
        
        ax_main.text(3.5, 2.6, "完整汽车造型生成", fontsize=10, color='#8b9dc3', ha='center')
        
        active_component = self.draw_car_body(ax_main, current_time)
        
        ax_info.text(0.5, 5.5, "当前状态", fontsize=10, color='#8b9dc3')
        ax_info.text(0.5, 5.2, active_component, fontsize=14, color='#00d4ff', weight='bold')
        
        self.draw_progress_bar(ax_info, total_progress / 100, 0.5, 4.5, 5, 0.2, '#00d4ff')
        ax_info.text(5.7, 4.6, f"{total_progress:.1f}%", fontsize=10, color='white')
        
        elapsed = current_time
        remaining = self.duration - elapsed
        ax_info.text(0.5, 4.0, f"已用时: {int(elapsed)}秒", fontsize=9, color='#8b9dc3')
        ax_info.text(3.5, 4.0, f"剩余: {int(remaining)}秒", fontsize=9, color='#00ff88')
        
        stats = [
            {"label": "车身部件", "value": min(17, int(total_progress / 6)), "color": '#00d4ff'},
            {"label": "曲面数量", "value": min(32, int(total_progress / 3)), "color": '#8b5cf6'},
            {"label": "质量评分", "value": "--" if total_progress < 80 else f"{92 + int(total_progress/20)}", "color": '#00ff88'},
            {"label": "完成状态", "value": "构建中" if total_progress < 100 else "已完成", "color": '#ffc107'}
        ]
        
        for i, stat in enumerate(stats):
            card = FancyBboxPatch((0.5 + i * 1.3, 2.8), 1.1, 0.5,
                                 boxstyle="round,pad=0.02",
                                 facecolor='#1a1a3e', edgecolor='#333333')
            ax_info.add_patch(card)
            ax_info.text(0.55 + i * 1.3, 3.1, str(stat['value']), fontsize=10, 
                        color=stat['color'], weight='bold')
            ax_info.text(0.55 + i * 1.3, 2.95, stat['label'], fontsize=7, color='#8b9dc3')
        
        components_list = [comp['name'] for comp in self.components_sequence]
        for i, comp_name in enumerate(components_list):
            y_pos = 2.0 - i * 0.12
            if y_pos < 0.2: break
            
            is_active = i == 0 or (current_time >= self.components_sequence[i]['start'])
            
            if is_active:
                ax_info.text(0.5, y_pos, f"✓ {comp_name}", fontsize=8, color='#00ff88')
            else:
                ax_info.text(0.5, y_pos, f"  {comp_name}", fontsize=8, color='#444444')
        
        plt.tight_layout()
        return fig

    def generate_video_with_imageio(self):
        """生成视频"""
        print("=" * 60)
        print("EVOLUTION AI 完整汽车造型视频生成")
        print("=" * 60)
        
        output_file = os.path.join(self.output_dir,
                                  f"EVOLUTION_AI_CAR_BODY_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
        
        print(f"\n输出文件: {output_file}")
        print(f"视频时长: {self.duration}秒")
        print(f"帧率: {self.fps} fps")
        print(f"总帧数: {self.total_frames}")
        
        frames = []
        for frame_num in range(self.total_frames):
            if frame_num % 30 == 0:
                print(f"  生成帧: {frame_num}/{self.total_frames} ({frame_num/self.total_frames*100:.1f}%)")
            
            fig = self.generate_frame(frame_num)
            
            fig.canvas.draw()
            img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
            frames.append(img)
            
            plt.close(fig)
        
        print(f"  生成帧: {self.total_frames}/{self.total_frames} (100%)")
        
        print("\n正在保存视频...")
        imageio.mimsave(output_file, frames, fps=self.fps, codec='libx264', quality=8)
        
        print(f"\n✓ 视频生成完成: {output_file}")
        
        return output_file

def main():
    generator = CarBodyVideoGenerator()
    output_file = generator.generate_video_with_imageio()
    print(f"\n视频已保存到: {output_file}")

if __name__ == '__main__':
    main()
