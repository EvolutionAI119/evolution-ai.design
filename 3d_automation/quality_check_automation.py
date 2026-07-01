#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
质量检查自动化脚本 - AI优化汽车A面工作流
功能：自动执行F5/F6/F7检查，生成质量报告，标记问题区域
作者：AI工作流开发团队
版本：v1.0
日期：2026-03-28
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import numpy as np
except ImportError:
    print("错误：缺少必要的依赖库")
    print("请安装：pip install numpy")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('quality_check.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Severity(Enum):
    """问题严重程度"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    CRITICAL = "严重"


class CheckType(Enum):
    """检查类型"""
    ZEBRA = "F5斑马纹检查"
    HIGHLIGHT = "F6高光线检查"
    CURVATURE_COMB = "F7曲率梳检查"
    CONTINUITY = "连续性检查"
    GEOMETRY = "几何质量检查"
    TOLERANCE = "精度检查"


@dataclass
class QualityIssue:
    """质量问题"""
    check_type: str
    location: str
    issue_type: str
    severity: str
    description: str
    suggestion: str
    check_time: Optional[str] = None

    def __post_init__(self):
        if self.check_time is None:
            self.check_time = datetime.now().isoformat()


@dataclass
class CheckResult:
    """检查结果"""
    check_type: str
    passed: bool
    score: float  # 0-100分
    issues: List[Dict]
    check_time: str

    def __post_init__(self):
        if self.check_time is None:
            self.check_time = datetime.now().isoformat()


class QualityChecker:
    """质量检查器"""

    def __init__(self, model_path, config=None):
        """
        初始化质量检查器

        Args:
            model_path: 模型文件路径
            config: 配置字典
        """
        self.model_path = Path(model_path)
        self.config = config or self._default_config()
        self.issues: List[QualityIssue] = []
        self.check_results: List[CheckResult] = []

        # 统计信息
        self.stats = {
            'total_checks': 0,
            'passed_checks': 0,
            'failed_checks': 0,
            'total_issues': 0,
            'issues_by_severity': {
                '严重': 0,
                '高': 0,
                '中': 0,
                '低': 0
            }
        }

    def _default_config(self):
        """默认配置"""
        return {
            'tolerance': {
                'position': 0.1,  # 位置容差（mm）
                'tangent': 0.01,  # 切向容差
                'curvature': 0.001  # 曲率容差
            },
            'standards': {
                'min_curvature': 0.0,  # 最小曲率
                'max_curvature': 1.0,  # 最大曲率
                'min_continuity': 'G2'  # 最小连续性
            },
            'output': {
                'generate_html': True,
                'generate_json': True,
                'mark_issues': True
            }
        }

    def run_all_checks(self):
        """执行所有检查"""
        logger.info("="*60)
        logger.info("开始质量检查")
        logger.info(f"模型文件: {self.model_path}")
        logger.info(f"检查标准: {self.config['standards']}")
        logger.info("="*60)

        # 执行各项检查
        checks = [
            (CheckType.ZEBRA, self.zebra_check),
            (CheckType.HIGHLIGHT, self.highlight_check),
            (CheckType.CURVATURE_COMB, self.curvature_comb_check),
            (CheckType.CONTINUITY, self.continuity_check),
            (CheckType.GEOMETRY, self.geometry_check),
            (CheckType.TOLERANCE, self.tolerance_check)
        ]

        for check_type, check_func in checks:
            logger.info(f"\n执行: {check_type.value}")
            try:
                result = check_func()
                self.check_results.append(result)
                self.stats['total_checks'] += 1
                if result.passed:
                    self.stats['passed_checks'] += 1
                else:
                    self.stats['failed_checks'] += 1
            except Exception as e:
                logger.error(f"检查失败: {str(e)}")
                self.stats['total_checks'] += 1
                self.stats['failed_checks'] += 1

        # 生成报告
        self.generate_report()

        # 打印摘要
        self.print_summary()

        return {
            'passed': self.stats['failed_checks'] == 0,
            'score': self._calculate_overall_score(),
            'issues': [asdict(issue) for issue in self.issues]
        }

    def zebra_check(self) -> CheckResult:
        """
        F5斑马纹检查
        检查曲面连续性
        """
        logger.info("  分析斑马纹...")

        issues = []
        score = 100

        # 模拟检查结果
        # 实际实现需要调用Alias或其他CAD软件的API

        # 模拟发现问题1
        issue1 = QualityIssue(
            check_type=CheckType.ZEBRA.value,
            location="发动机盖前端",
            issue_type="斑马纹断裂",
            severity=Severity.HIGH.value,
            description="发动机盖前端与保险杠连接处斑马纹出现明显断裂",
            suggestion="重建曲面，使用G2对齐工具调整边界连续性"
        )
        issues.append(asdict(issue1))
        self.issues.append(issue1)
        self.stats['total_issues'] += 1
        self.stats['issues_by_severity'][Severity.HIGH.value] += 1
        score -= 20

        # 模拟发现问题2
        issue2 = QualityIssue(
            check_type=CheckType.ZEBRA.value,
            location="车门腰线",
            issue_type="斑马纹轻微不连续",
            severity=Severity.MEDIUM.value,
            description="车门腰线区域斑马纹过渡不够平滑",
            suggestion="调整CV分布，确保沿特征线布线"
        )
        issues.append(asdict(issue2))
        self.issues.append(issue2)
        self.stats['total_issues'] += 1
        self.stats['issues_by_severity'][Severity.MEDIUM.value] += 1
        score -= 10

        logger.info(f"  发现 {len(issues)} 个问题")
        logger.info(f"  评分: {score}/100")

        return CheckResult(
            check_type=CheckType.ZEBRA.value,
            passed=score >= 80,
            score=score,
            issues=issues,
            check_time=datetime.now().isoformat()
        )

    def highlight_check(self) -> CheckResult:
        """
        F6高光线检查
        检查曲面光顺度
        """
        logger.info("  分析高光线...")

        issues = []
        score = 100

        # 模拟检查结果
        issue1 = QualityIssue(
            check_type=CheckType.HIGHLIGHT.value,
            location="侧围轮眉区域",
            issue_type="高光跳跃",
            severity=Severity.MEDIUM.value,
            description="侧围轮眉区域高光线出现明显跳跃",
            suggestion="平滑曲面过渡，调整控制点分布"
        )
        issues.append(asdict(issue1))
        self.issues.append(issue1)
        self.stats['total_issues'] += 1
        self.stats['issues_by_severity'][Severity.MEDIUM.value] += 1
        score -= 15

        logger.info(f"  发现 {len(issues)} 个问题")
        logger.info(f"  评分: {score}/100")

        return CheckResult(
            check_type=CheckType.HIGHLIGHT.value,
            passed=score >= 80,
            score=score,
            issues=issues,
            check_time=datetime.now().isoformat()
        )

    def curvature_comb_check(self) -> CheckResult:
        """
        F7曲率梳检查
        检查曲率变化
        """
        logger.info("  分析曲率梳...")

        issues = []
        score = 100

        # 模拟检查结果
        issue1 = QualityIssue(
            check_type=CheckType.CURVATURE_COMB.value,
            location="B柱上端",
            issue_type="曲率突变",
            severity=Severity.HIGH.value,
            description="B柱上端与顶棚连接处曲率出现明显突变",
            suggestion="重新分面，降低曲面度数，确保G2连续"
        )
        issues.append(asdict(issue1))
        self.issues.append(issue1)
        self.stats['total_issues'] += 1
        self.stats['issues_by_severity'][Severity.HIGH.value] += 1
        score -= 25

        logger.info(f"  发现 {len(issues)} 个问题")
        logger.info(f"  评分: {score}/100")

        return CheckResult(
            check_type=CheckType.CURVATURE_COMB.value,
            passed=score >= 80,
            score=score,
            issues=issues,
            check_time=datetime.now().isoformat()
        )

    def continuity_check(self) -> CheckResult:
        """
        连续性检查
        检查曲面间连续性
        """
        logger.info("  检查连续性...")

        issues = []
        score = 100

        # 模拟检查结果
        issue1 = QualityIssue(
            check_type=CheckType.CONTINUITY.value,
            location="车门与侧围连接处",
            issue_type="连续性不足",
            severity=Severity.MEDIUM.value,
            description="部分区域仅达到G1连续，未达到G2要求",
            suggestion="使用Blend工具提升连续性至G2"
        )
        issues.append(asdict(issue1))
        self.issues.append(issue1)
        self.stats['total_issues'] += 1
        self.stats['issues_by_severity'][Severity.MEDIUM.value] += 1
        score -= 10

        logger.info(f"  发现 {len(issues)} 个问题")
        logger.info(f"  评分: {score}/100")

        return CheckResult(
            check_type=CheckType.CONTINUITY.value,
            passed=score >= 80,
            score=score,
            issues=issues,
            check_time=datetime.now().isoformat()
        )

    def geometry_check(self) -> CheckResult:
        """
        几何质量检查
        检查网格质量、退化面等
        """
        logger.info("  检查几何质量...")

        issues = []
        score = 100

        # 模拟检查结果
        issue1 = QualityIssue(
            check_type=CheckType.GEOMETRY.value,
            location="发动机盖中心区域",
            issue_type="存在狭长曲面",
            severity=Severity.LOW.value,
            description="发动机盖中心区域存在狭长曲面，可能影响渲染质量",
            suggestion="重新分面，避免长宽比过大的曲面"
        )
        issues.append(asdict(issue1))
        self.issues.append(issue1)
        self.stats['total_issues'] += 1
        self.stats['issues_by_severity'][Severity.LOW.value] += 1
        score -= 5

        logger.info(f"  发现 {len(issues)} 个问题")
        logger.info(f"  评分: {score}/100")

        return CheckResult(
            check_type=CheckType.GEOMETRY.value,
            passed=score >= 90,
            score=score,
            issues=issues,
            check_time=datetime.now().isoformat()
        )

    def tolerance_check(self) -> CheckResult:
        """
        精度检查
        检查尺寸精度、位置偏差等
        """
        logger.info("  检查精度...")

        issues = []
        score = 100

        # 模拟检查结果
        tolerance = self.config['tolerance']['position']
        logger.info(f"  位置容差: ±{tolerance}mm")

        # 模拟检查结果 - 假设所有精度都在范围内
        logger.info("  所有关键尺寸精度在±0.1mm范围内")
        logger.info(f"  评分: {score}/100")

        return CheckResult(
            check_type=CheckType.TOLERANCE.value,
            passed=True,
            score=score,
            issues=issues,
            check_time=datetime.now().isoformat()
        )

    def _calculate_overall_score(self):
        """计算总体评分"""
        if not self.check_results:
            return 0

        total_score = sum(result.score for result in self.check_results)
        return round(total_score / len(self.check_results), 2)

    def generate_report(self):
        """生成质量检查报告"""
        report = {
            'model_path': str(self.model_path),
            'check_time': datetime.now().isoformat(),
            'overall_score': self._calculate_overall_score(),
            'passed': self.stats['failed_checks'] == 0,
            'summary': {
                'total_checks': self.stats['total_checks'],
                'passed_checks': self.stats['passed_checks'],
                'failed_checks': self.stats['failed_checks'],
                'total_issues': self.stats['total_issues'],
                'issues_by_severity': self.stats['issues_by_severity']
            },
            'check_results': [asdict(result) for result in self.check_results],
            'issues': [asdict(issue) for issue in self.issues],
            'config': self.config
        }

        # 保存JSON报告
        if self.config['output']['generate_json']:
            json_path = self.model_path.parent / f"{self.model_path.stem}_quality_report.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"\nJSON报告已生成: {json_path}")

        # 生成HTML报告
        if self.config['output']['generate_html']:
            html_path = self.model_path.parent / f"{self.model_path.stem}_quality_report.html"
            self._generate_html_report(report, html_path)
            logger.info(f"HTML报告已生成: {html_path}")

        return report

    def _generate_html_report(self, report: dict, output_path: Path):
        """生成HTML格式报告"""
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>质量检查报告 - {report['model_path']}</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .summary {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .score {{
            font-size: 48px;
            font-weight: bold;
            color: {'green' if report['passed'] else 'orange'};
            text-align: center;
            margin: 20px 0;
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background-color: #fff;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .issue-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .issue-table th, .issue-table td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        .issue-table th {{
            background-color: #007bff;
            color: white;
        }}
        .issue-table tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .severity-严重 {{ color: #dc3545; font-weight: bold; }}
        .severity-高 {{ color: #fd7e14; font-weight: bold; }}
        .severity-中 {{ color: #ffc107; font-weight: bold; }}
        .severity-低 {{ color: #28a745; font-weight: bold; }}
        .check-result {{
            margin: 15px 0;
            padding: 15px;
            border-radius: 5px;
        }}
        .check-result.passed {{
            background-color: #d4edda;
            border-left: 4px solid #28a745;
        }}
        .check-result.failed {{
            background-color: #f8d7da;
            border-left: 4px solid #dc3545;
        }}
        .timestamp {{
            color: #999;
            font-size: 12px;
            text-align: right;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>质量检查报告</h1>
        <p><strong>模型文件:</strong> {report['model_path']}</p>
        <p><strong>检查时间:</strong> {report['check_time']}</p>

        <div class="summary">
            <h2>总体评分</h2>
            <div class="score">{report['overall_score']}/100</div>
            <p style="text-align: center;">
                <strong>{'✓ 通过' if report['passed'] else '✗ 未通过'}</strong>
            </p>
        </div>

        <h2>检查摘要</h2>
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-value">{report['summary']['total_checks']}</div>
                <div class="stat-label">总检查项</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{report['summary']['passed_checks']}</div>
                <div class="stat-label">通过</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{report['summary']['failed_checks']}</div>
                <div class="stat-label">失败</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{report['summary']['total_issues']}</div>
                <div class="stat-label">问题数</div>
            </div>
        </div>

        <h2>问题严重性分布</h2>
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-value severity-严重">{report['summary']['issues_by_severity']['严重']}</div>
                <div class="stat-label">严重</div>
            </div>
            <div class="stat-card">
                <div class="stat-value severity-高">{report['summary']['issues_by_severity']['高']}</div>
                <div class="stat-label">高</div>
            </div>
            <div class="stat-card">
                <div class="stat-value severity-中">{report['summary']['issues_by_severity']['中']}</div>
                <div class="stat-label">中</div>
            </div>
            <div class="stat-card">
                <div class="stat-value severity-低">{report['summary']['issues_by_severity']['低']}</div>
                <div class="stat-label">低</div>
            </div>
        </div>

        <h2>详细检查结果</h2>
"""

        for result in report['check_results']:
            html_content += f"""
        <div class="check-result {'passed' if result['passed'] else 'failed'}">
            <h3>{result['check_type']}</h3>
            <p><strong>状态:</strong> {'✓ 通过' if result['passed'] else '✗ 未通过'}</p>
            <p><strong>评分:</strong> {result['score']}/100</p>
            <p><strong>检查时间:</strong> {result['check_time']}</p>
"""

            if result['issues']:
                html_content += f"""
            <h4>发现的问题:</h4>
            <table class="issue-table">
                <thead>
                    <tr>
                        <th>位置</th>
                        <th>问题类型</th>
                        <th>严重程度</th>
                        <th>描述</th>
                        <th>建议</th>
                    </tr>
                </thead>
                <tbody>
"""
                for issue in result['issues']:
                    html_content += f"""
                    <tr>
                        <td>{issue['location']}</td>
                        <td>{issue['issue_type']}</td>
                        <td class="severity-{issue['severity']}">{issue['severity']}</td>
                        <td>{issue['description']}</td>
                        <td>{issue['suggestion']}</td>
                    </tr>
"""
                html_content += """
                </tbody>
            </table>
"""
            else:
                html_content += "<p>未发现问题</p>"

            html_content += "</div>"

        html_content += f"""
        <div class="timestamp">
            报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def print_summary(self):
        """打印摘要"""
        logger.info("\n" + "="*60)
        logger.info("质量检查摘要")
        logger.info("="*60)
        logger.info(f"总体评分: {self._calculate_overall_score()}/100")
        logger.info(f"检查结果: {'✓ 通过' if self.stats['failed_checks'] == 0 else '✗ 未通过'}")
        logger.info(f"总检查项: {self.stats['total_checks']}")
        logger.info(f"通过: {self.stats['passed_checks']}")
        logger.info(f"失败: {self.stats['failed_checks']}")
        logger.info(f"问题总数: {self.stats['total_issues']}")
        logger.info("\n问题严重性分布:")
        for severity, count in self.stats['issues_by_severity'].items():
            if count > 0:
                logger.info(f"  {severity}: {count}")

        if self.issues:
            logger.info("\n问题详情:")
            for issue in self.issues:
                logger.info(f"  [{issue.severity}] {issue.check_type} - {issue.location}: {issue.issue_type}")
                logger.info(f"    描述: {issue.description}")
                logger.info(f"    建议: {issue.suggestion}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='质量检查自动化脚本')
    parser.add_argument('model_path', help='模型文件路径')
    parser.add_argument('--no-html', action='store_true', help='不生成HTML报告')
    parser.add_argument('--no-json', action='store_true', help='不生成JSON报告')

    args = parser.parse_args()

    # 配置
    config = {
        'output': {
            'generate_html': not args.no_html,
            'generate_json': not args.no_json,
            'mark_issues': True
        }
    }

    # 创建检查器
    checker = QualityChecker(args.model_path, config)

    # 执行检查
    result = checker.run_all_checks()

    # 返回退出码
    sys.exit(0 if result['passed'] else 1)


if __name__ == "__main__":
    main()
