#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量拓扑优化脚本 - AI优化汽车A面工作流
功能：自动处理多个GLB模型，调用Instant Mesh，质量检查，批量导出OBJ
作者：AI工作流开发团队
版本：v1.0
日期：2026-03-28
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path

try:
    import trimesh
    import numpy as np
except ImportError:
    print("错误：缺少必要的依赖库")
    print("请安装：pip install trimesh numpy")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('topology_optimization.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TopologyOptimizer:
    """批量拓扑优化器"""

    def __init__(self, input_dir, output_dir, config=None):
        """
        初始化优化器

        Args:
            input_dir: 输入目录（GLB文件）
            output_dir: 输出目录（OBJ文件）
            config: 配置字典
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.config = config or self._default_config()

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 统计信息
        self.stats = {
            'total_files': 0,
            'success_count': 0,
            'failed_count': 0,
            'start_time': None,
            'end_time': None,
            'details': []
        }

    def _default_config(self):
        """默认配置"""
        return {
            'target_faces': 30000,  # 目标面数
            'quad_ratio_threshold': 0.80,  # 四边形比例阈值
            'min_quad_ratio': 0.75,  # 最小四边形比例
            'max_boundary_edges': 100,  # 最大边界边数
            'fix_normals': True,  # 是否修复法线
            'merge_vertices': True,  # 是否合并顶点
            'remove_duplicates': True,  # 是否移除重复面
            'export_format': 'obj',  # 导出格式
            'quality_check': True  # 是否进行质量检查
        }

    def process_all(self):
        """批量处理所有文件"""
        self.stats['start_time'] = datetime.now()
        logger.info("="*60)
        logger.info("开始批量拓扑优化")
        logger.info(f"输入目录: {self.input_dir}")
        logger.info(f"输出目录: {self.output_dir}")
        logger.info(f"配置: {json.dumps(self.config, ensure_ascii=False, indent=2)}")
        logger.info("="*60)

        # 获取所有GLB文件
        glb_files = list(self.input_dir.glob('*.glb')) + list(self.input_dir.glob('*.GLB'))

        if not glb_files:
            logger.warning(f"在 {self.input_dir} 中未找到GLB文件")
            return

        self.stats['total_files'] = len(glb_files)
        logger.info(f"找到 {len(glb_files)} 个GLB文件")

        # 处理每个文件
        for idx, glb_file in enumerate(glb_files, 1):
            logger.info(f"\n[{idx}/{len(glb_files)}] 处理文件: {glb_file.name}")

            try:
                self.process_single(glb_file)
                self.stats['success_count'] += 1
                logger.info(f"✓ 成功: {glb_file.name}")
            except Exception as e:
                self.stats['failed_count'] += 1
                logger.error(f"✗ 失败: {glb_file.name} - {str(e)}")

        # 生成统计报告
        self.stats['end_time'] = datetime.now()
        self.generate_report()

        logger.info("\n" + "="*60)
        logger.info("批量处理完成")
        logger.info(f"成功: {self.stats['success_count']}/{self.stats['total_files']}")
        logger.info(f"失败: {self.stats['failed_count']}/{self.stats['total_files']}")
        logger.info(f"耗时: {self._get_duration()}")
        logger.info("="*60)

    def process_single(self, glb_file):
        """处理单个文件"""
        # 1. 加载GLB模型
        logger.info(f"  加载模型...")
        mesh = self.load_mesh(glb_file)

        # 2. 预处理
        logger.info(f"  预处理...")
        mesh = self.preprocess_mesh(mesh)

        # 3. 调用Instant Mesh（模拟）
        logger.info(f"  调用Instant Mesh优化拓扑...")
        optimized_mesh = self.optimize_topology(mesh)

        # 4. 质量检查
        if self.config['quality_check']:
            logger.info(f"  质量检查...")
            quality_result = self.quality_check(optimized_mesh, glb_file.name)
        else:
            quality_result = None

        # 5. 导出OBJ
        logger.info(f"  导出OBJ...")
        output_file = self.export_mesh(optimized_mesh, glb_file)

        # 6. 记录详情
        detail = {
            'filename': glb_file.name,
            'output_file': output_file.name,
            'success': True,
            'quality': quality_result
        }
        self.stats['details'].append(detail)

    def load_mesh(self, file_path):
        """
        加载3D模型

        Args:
            file_path: 文件路径

        Returns:
            trimesh.Trimesh: 加载的网格
        """
        try:
            mesh = trimesh.load(file_path, force='mesh')

            # 如果加载的是场景，取第一个网格
            if isinstance(mesh, trimesh.Scene):
                geometries = list(mesh.geometry.values())
                if geometries:
                    mesh = geometries[0]
                else:
                    raise ValueError("场景中无几何体")

            logger.info(f"    原始面数: {len(mesh.faces)}")
            return mesh

        except Exception as e:
            raise Exception(f"加载模型失败: {str(e)}")

    def preprocess_mesh(self, mesh):
        """
        预处理网格

        Args:
            mesh: 输入网格

        Returns:
            trimesh.Trimesh: 预处理后的网格
        """
        # 修复法线
        if self.config['fix_normals']:
            mesh.fix_normals()
            logger.info(f"    法线已修复")

        # 合并重复顶点
        if self.config['merge_vertices']:
            mesh.merge_vertices()
            logger.info(f"    顶点已合并")

        # 移除重复面
        if self.config['remove_duplicates']:
            mesh.remove_duplicate_faces()
            logger.info(f"    重复面已移除")

        # 移除内部面
        mesh.remove_infinite_values()
        mesh.remove_unreferenced_vertices()

        return mesh

    def optimize_topology(self, mesh):
        """
        优化拓扑（调用Instant Mesh）

        Args:
            mesh: 输入网格

        Returns:
            trimesh.Trimesh: 优化后的网格
        """
        # 注意：这里模拟Instant Mesh的处理
        # 实际实现需要调用Instant Mesh的API或命令行工具

        # 模拟：根据目标面数进行网格简化
        target_faces = self.config['target_faces']
        current_faces = len(mesh.faces)

        if current_faces > target_faces:
            # 简化网格
            ratio = target_faces / current_faces
            simplified = mesh.simplify_quadratic_decimation(target_faces)
            logger.info(f"    网格简化: {current_faces} → {len(simplified.faces)} 面")
            mesh = simplified
        else:
            logger.info(f"    面数已满足要求: {current_faces}")

        # 这里应该调用Instant Mesh进行四边形化
        # 由于没有实际API，这里返回原始网格
        logger.info(f"    Instant Mesh处理完成（模拟）")

        return mesh

    def quality_check(self, mesh, filename):
        """
        质量检查

        Args:
            mesh: 网格
            filename: 文件名

        Returns:
            dict: 质量检查结果
        """
        result = {
            'filename': filename,
            'num_faces': len(mesh.faces),
            'num_vertices': len(mesh.vertices),
            'quad_ratio': 0.0,
            'boundary_edges': 0,
            'is_watertight': False,
            'issues': []
        }

        # 检查面数
        result['num_faces'] = len(mesh.faces)
        result['num_vertices'] = len(mesh.vertices)
        logger.info(f"    面数: {result['num_faces']}")
        logger.info(f"    顶点数: {result['num_vertices']}")

        # 计算四边形比例
        quad_count = sum(1 for face in mesh.faces if len(face) == 4)
        result['quad_ratio'] = quad_count / len(mesh.faces) if len(mesh.faces) > 0 else 0
        logger.info(f"    四边形比例: {result['quad_ratio']:.2%}")

        if result['quad_ratio'] < self.config['min_quad_ratio']:
            result['issues'].append(f"四边形比例过低: {result['quad_ratio']:.2%} < {self.config['min_quad_ratio']:.2%}")

        # 检查边界
        result['boundary_edges'] = len(mesh.boundary_edges)
        logger.info(f"    边界边数: {result['boundary_edges']}")

        if result['boundary_edges'] > self.config['max_boundary_edges']:
            result['issues'].append(f"边界边数过多: {result['boundary_edges']} > {self.config['max_boundary_edges']}")

        # 检查是否水密
        result['is_watertight'] = mesh.is_watertight
        logger.info(f"    水密性: {'是' if result['is_watertight'] else '否'}")

        if not result['is_watertight']:
            result['issues'].append("网格不水密，存在孔洞")

        # 检查法线方向
        if not mesh.is_watertight:
            result['issues'].append("可能存在法线方向问题")

        # 检查退化面
        degenerate_faces = mesh.processed()
        if degenerate_faces is not None and len(degenerate_faces.faces) < len(mesh.faces):
            result['issues'].append(f"存在退化面: {len(mesh.faces) - len(degenerate_faces.faces)} 个")

        return result

    def export_mesh(self, mesh, input_file):
        """
        导出网格

        Args:
            mesh: 网格
            input_file: 输入文件路径

        Returns:
            Path: 输出文件路径
        """
        output_filename = input_file.stem + '.obj'
        output_path = self.output_dir / output_filename

        # 导出OBJ
        mesh.export(str(output_path))
        logger.info(f"    已导出: {output_path}")

        return output_path

    def _get_duration(self):
        """获取处理时长"""
        if self.stats['start_time'] and self.stats['end_time']:
            duration = self.stats['end_time'] - self.stats['start_time']
            return str(duration).split('.')[0]  # 去掉微秒
        return "未知"

    def generate_report(self):
        """生成统计报告"""
        report = {
            'summary': {
                'total_files': self.stats['total_files'],
                'success_count': self.stats['success_count'],
                'failed_count': self.stats['failed_count'],
                'success_rate': f"{(self.stats['success_count']/self.stats['total_files']*100):.2f}%" if self.stats['total_files'] > 0 else "0%",
                'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
                'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None,
                'duration': self._get_duration()
            },
            'config': self.config,
            'details': self.stats['details']
        }

        # 保存JSON报告
        report_path = self.output_dir / 'topology_optimization_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"\n统计报告已生成: {report_path}")

        # 打印摘要
        self._print_summary(report)

    def _print_summary(self, report):
        """打印报告摘要"""
        logger.info("\n" + "="*60)
        logger.info("处理摘要")
        logger.info("="*60)
        summary = report['summary']
        logger.info(f"总文件数: {summary['total_files']}")
        logger.info(f"成功: {summary['success_count']}")
        logger.info(f"失败: {summary['failed_count']}")
        logger.info(f"成功率: {summary['success_rate']}")
        logger.info(f"开始时间: {summary['start_time']}")
        logger.info(f"结束时间: {summary['end_time']}")
        logger.info(f"处理时长: {summary['duration']}")

        # 打印质量问题
        quality_issues = [d for d in report['details'] if d.get('quality') and d['quality'].get('issues')]
        if quality_issues:
            logger.info("\n质量问题汇总:")
            for detail in quality_issues:
                logger.info(f"  {detail['filename']}:")
                for issue in detail['quality']['issues']:
                    logger.info(f"    - {issue}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='批量拓扑优化脚本')
    parser.add_argument('input_dir', help='输入目录（GLB文件）')
    parser.add_argument('output_dir', help='输出目录（OBJ文件）')
    parser.add_argument('--target-faces', type=int, default=30000, help='目标面数（默认：30000）')
    parser.add_argument('--min-quad-ratio', type=float, default=0.75, help='最小四边形比例（默认：0.75）')
    parser.add_argument('--no-quality-check', action='store_true', help='跳过质量检查')

    args = parser.parse_args()

    # 配置
    config = {
        'target_faces': args.target_faces,
        'min_quad_ratio': args.min_quad_ratio,
        'quality_check': not args.no_quality_check
    }

    # 创建优化器
    optimizer = TopologyOptimizer(args.input_dir, args.output_dir, config)

    # 执行批量处理
    optimizer.process_all()


if __name__ == "__main__":
    main()
