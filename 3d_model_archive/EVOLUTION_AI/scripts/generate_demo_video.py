"""
EVOLUTION AI DEMO 视频生成脚本
使用 matplotlib 和 numpy 生成演示视频
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch
from matplotlib.collections import LineCollection
import matplotlib.patheffects as path_effects
import os
from datetime import datetime
import json
import imageio

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class DemoVideoGenerator:
    """DEMO视频生成器"""

    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # 视频参数（优化内存使用）
        self.fps = 15  # 降低帧率
        self.duration = 10  # 缩短时长
        self.total_frames = self.fps * self.duration
        self.fig_size = (12, 6.75)  # 降低分辨率

        # 场景数据
        self.scenes = [
            {"name": "系统初始化", "icon": "[SYS]", "total": 36, "color": "#00d4ff"},
            {"name": "参数加载", "icon": "[PAR]", "total": 12, "color": "#8b5cf6"},
            {"name": "曲面创建", "icon": "[SUR]", "total": 170, "color": "#00ff88"},
            {"name": "质量检测", "icon": "[QAL]", "total": 118, "color": "#ffc107"},
            {"name": "拓扑优化", "icon": "[OPT]", "total": 90, "color": "#ff6b6b"},
            {"name": "数据交接", "icon": "[HND]", "total": 51, "color": "#4facfe"},
        ]

        # 曲面数据
        self.surfaces = []

    def create_nurbs_surface(self, num_u=8, num_v=6):
        """创建NURBS曲面控制点"""
        points = []
        for i in range(num_u):
            row = []
            for j in range(num_v):
                x = i * 50
                y = j * 50
                z = 30 * np.sin(i * 0.5) * np.cos(j * 0.5)
                row.append([x, y, z])
            points.append(row)
        return np.array(points)

    def draw_progress_bar(self, ax, progress, x, y, width, height, color):
        """绘制进度条"""
        # 背景
        bg = FancyBboxPatch((x, y), width, height,
                            boxstyle="round,pad=0.02,rounding_size=0.1",
                            facecolor='#1a1a3e', edgecolor='#333333', linewidth=1)
        ax.add_patch(bg)

        # 进度
        if progress > 0:
            progress_width = width * min(progress, 100) / 100
            progress_bar = FancyBboxPatch((x, y), progress_width, height,
                                          boxstyle="round,pad=0.02,rounding_size=0.1",
                                          facecolor=color, edgecolor=color, linewidth=0)
            ax.add_patch(progress_bar)

    def draw_scene_card(self, ax, scene, progress, x, y, width, height, is_active=False):
        """绘制场景卡片"""
        # 卡片背景
        bg_color = '#1a1a3e' if not is_active else '#2a2a4e'
        edge_color = '#333333' if not is_active else scene['color']

        card = FancyBboxPatch((x, y), width, height,
                             boxstyle="round,pad=0.02,rounding_size=0.05",
                             facecolor=bg_color, edgecolor=edge_color, linewidth=2 if is_active else 1)
        ax.add_patch(card)

        # 场景名称
        text = ax.text(x + 0.1, y + height - 0.15, f"{scene['icon']} {scene['name']}",
                       fontsize=10, color='white', weight='bold')
        text.set_path_effects([path_effects.withStroke(linewidth=1, foreground=scene['color'])])

        # 状态标签
        status = "执行中" if is_active else ("已完成" if progress >= 100 else "待执行")
        status_color = scene['color'] if is_active else ('#00ff88' if progress >= 100 else '#8b9dc3')
        ax.text(x + width - 0.2, y + height - 0.15, status,
                fontsize=8, color=status_color, ha='right')

        # 进度条
        bar_y = y + 0.05
        bar_height = 0.08
        self.draw_progress_bar(ax, progress, x + 0.1, bar_y, width - 0.2, bar_height, scene['color'])

    def draw_nurbs_surface(self, ax, surface_points, offset_x=0, offset_y=0, color='#00d4ff'):
        """绘制NURBS曲面"""
        num_u, num_v, _ = surface_points.shape

        # 绘制网格线
        for i in range(num_u):
            xs = surface_points[i, :, 0] + offset_x
            ys = surface_points[i, :, 1] + offset_y
            zs = surface_points[i, :, 2]
            ax.plot(xs + zs * 0.5, ys, color=color, linewidth=1, alpha=0.8)

        for j in range(num_v):
            xs = surface_points[:, j, 0] + offset_x
            ys = surface_points[:, j, 1] + offset_y
            zs = surface_points[:, j, 2]
            ax.plot(xs + zs * 0.5, ys, color=color, linewidth=1, alpha=0.8)

    def generate_frame(self, frame_num):
        """生成单帧"""
        # 创建画布（使用较小尺寸）
        fig, ax = plt.subplots(figsize=self.fig_size, facecolor='#0a0a1a')
        ax.set_facecolor('#0a0a1a')
        ax.set_xlim(0, 12)
        ax.set_ylim(0, 6.75)
        ax.axis('off')

        # 计算当前进度
        total_progress = frame_num / self.total_frames * 100

        # 绘制标题
        title = ax.text(6, 6.3, "EVOLUTION AI", fontsize=20, color='#00d4ff',
                       ha='center', va='center', weight='bold')
        title.set_path_effects([
            path_effects.withStroke(linewidth=2, foreground='#8b5cf6'),
        ])

        ax.text(6, 6.0, "汽车A级曲面智能开发平台", fontsize=10, color='#8b9dc3', ha='center')

        # 绘制主进度条
        self.draw_progress_bar(ax, total_progress, 0.5, 5.4, 11, 0.2, '#00d4ff')
        ax.text(11.7, 5.5, f"{total_progress:.1f}%", fontsize=10, color='white', ha='right')

        # 时间显示
        elapsed = frame_num / self.fps
        remaining = self.duration - elapsed
        ax.text(0.5, 5.2, f"已用时: {int(elapsed)}秒", fontsize=8, color='#8b9dc3')
        ax.text(3, 5.2, f"剩余: {int(remaining)}秒", fontsize=8, color='#00ff88')

        # 绘制统计卡片
        stats_x = [0.5, 3, 5.5, 8]
        stats_labels = ["曲面", "评分", "优化", "格式"]
        stats_values = [
            min(4, int(total_progress / 25)),
            "--" if total_progress < 50 else f"{85 + int(total_progress/10)}",
            "--" if total_progress < 70 else f"+{int(total_progress/5)}%",
            "--" if total_progress < 90 else "4"
        ]

        for i, (x, label, value) in enumerate(zip(stats_x, stats_labels, stats_values)):
            card = FancyBboxPatch((x, 4.5), 2, 0.6,
                                 boxstyle="round,pad=0.02",
                                 facecolor='#1a1a3e', edgecolor='#333333')
            ax.add_patch(card)
            ax.text(x + 1, 4.75, value, fontsize=10, color='#00d4ff', ha='center', weight='bold')
            ax.text(x + 1, 4.55, label, fontsize=7, color='#8b9dc3', ha='center')

        # 绘制场景卡片（简化）
        scene_positions = [
            (0.5, 3.3), (4, 3.3), (8, 3.3),
            (0.5, 2.0), (4, 2.0), (8, 2.0)
        ]

        current_scene = int(total_progress / (100 / len(self.scenes)))
        scene_progress_per_scene = 100 / len(self.scenes)

        for i, (scene, (x, y)) in enumerate(zip(self.scenes, scene_positions)):
            if i < current_scene:
                progress = 100
            elif i == current_scene:
                scene_elapsed = total_progress - i * scene_progress_per_scene
                progress = min(100, scene_elapsed / scene_progress_per_scene * 100)
            else:
                progress = 0

            is_active = i == current_scene and progress < 100
            
            # 简化的场景卡片
            bg_color = '#1a1a3e' if not is_active else '#2a2a4e'
            edge_color = '#333333' if not is_active else scene['color']
            
            card = FancyBboxPatch((x, y), 3.5, 1.0,
                                 boxstyle="round,pad=0.02",
                                 facecolor=bg_color, edgecolor=edge_color, linewidth=1)
            ax.add_patch(card)
            
            ax.text(x + 0.1, y + 0.8, f"{scene['icon']} {scene['name']}", fontsize=8, color='white', weight='bold')
            
            # 进度条
            self.draw_progress_bar(ax, progress, x + 0.1, y + 0.1, 3.3, 0.15, scene['color'])

        # 绘制NURBS曲面可视化（简化）
        if total_progress > 30:
            ax.text(0.5, 1.5, "NURBS 曲面可视化", fontsize=9, color='#00d4ff')
            
            surface_names = ["发动机盖", "车顶", "车门"]
            colors = ['#00d4ff', '#8b5cf6', '#00ff88']

            for idx, (name, color) in enumerate(zip(surface_names, colors)):
                if total_progress > 30 + idx * 15:
                    points = self.create_nurbs_surface(4, 3)
                    offset_x = idx * 3.5 + 0.5
                    offset_y = 0.3
                    self.draw_nurbs_surface(ax, points, offset_x, offset_y, color)
                    ax.text(offset_x + 1, 1.2, name, fontsize=7, color=color)

        plt.tight_layout()
        return fig

    def generate_video_with_imageio(self):
        """使用imageio生成视频（不需要FFmpeg）"""
        print("=" * 60)
        print("EVOLUTION AI DEMO 视频生成 (imageio)")
        print("=" * 60)

        output_file = os.path.join(self.output_dir,
                                   f"EVOLUTION_AI_DEMO_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")

        print(f"\n输出文件: {output_file}")
        print(f"视频时长: {self.duration}秒")
        print(f"帧率: {self.fps} fps")
        print(f"总帧数: {self.total_frames}")

        print("\n开始生成视频帧...")

        frames = []
        # 生成所有帧
        for frame_num in range(self.total_frames):
            if frame_num % 50 == 0:
                print(f"  生成帧: {frame_num}/{self.total_frames} ({frame_num/self.total_frames*100:.1f}%)")
            
            fig = self.generate_frame(frame_num)
            
            # 将figure转换为图像数组
            fig.canvas.draw()
            img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
            frames.append(img)
            
            plt.close(fig)

        print(f"  生成帧: {self.total_frames}/{self.total_frames} (100%)")

        # 使用imageio保存视频
        print("\n正在保存视频...")
        imageio.mimsave(output_file, frames, fps=self.fps, codec='libx264', quality=8)

        print(f"\n✓ 视频生成完成: {output_file}")

        return output_file

    def generate_video(self):
        """生成完整视频"""
        print("=" * 60)
        print("EVOLUTION AI DEMO 视频生成")
        print("=" * 60)

        output_file = os.path.join(self.output_dir,
                                   f"EVOLUTION_AI_DEMO_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")

        print(f"\n输出文件: {output_file}")
        print(f"视频时长: {self.duration}秒")
        print(f"帧率: {self.fps} fps")
        print(f"总帧数: {self.total_frames}")

        # 创建动画
        fig = self.generate_frame(0)

        def animate(frame):
            plt.close()
            return self.generate_frame(frame)

        print("\n开始生成视频帧...")

        anim = animation.FuncAnimation(
            fig, animate,
            frames=self.total_frames,
            interval=1000/self.fps,
            blit=False
        )

        # 保存视频
        writer = animation.FFMpegWriter(fps=self.fps, bitrate=5000)
        anim.save(output_file, writer=writer)

        plt.close('all')

        print(f"\n✓ 视频生成完成: {output_file}")

        return output_file

    def generate_frames_as_images(self):
        """生成帧图像（用于无法安装FFmpeg的情况）"""
        print("=" * 60)
        print("EVOLUTION AI DEMO 图像帧生成")
        print("=" * 60)

        frames_dir = os.path.join(self.output_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)

        print(f"\n输出目录: {frames_dir}")
        print(f"总帧数: {self.total_frames}")

        # 生成关键帧
        key_frames = [0, 90, 180, 270, 360, 450]

        for frame_num in key_frames:
            fig = self.generate_frame(frame_num)
            output_file = os.path.join(frames_dir, f"frame_{frame_num:04d}.png")
            fig.savefig(output_file, facecolor='#0a0a1a', dpi=100)
            plt.close(fig)
            print(f"  ✓ 已生成: {output_file}")

        print(f"\n✓ 关键帧生成完成")

        return frames_dir


def main():
    """主函数"""
    generator = DemoVideoGenerator()

    # 使用imageio生成完整视频
    print("正在生成DEMO视频...")
    try:
        output_file = generator.generate_video_with_imageio()
        print(f"\n✓ 视频已保存到: {output_file}")
        print(f"\n输出目录: {generator.output_dir}")
    except Exception as e:
        print(f"\n视频生成失败: {e}")
        print("生成关键帧图像作为替代...")
        generator.generate_frames_as_images()
        print(f"关键帧保存在: {generator.output_dir}/frames/")


if __name__ == "__main__":
    main()