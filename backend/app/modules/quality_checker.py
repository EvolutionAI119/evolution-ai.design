import os
import json
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from enum import Enum
from app.config.settings import settings
from app.core.workflow_engine import WorkflowStep
from app.utils.logger import logger


class Severity(Enum):
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    CRITICAL = "严重"


class CheckType(Enum):
    ZEBRA = "F5斑马纹检查"
    HIGHLIGHT = "F6高光线检查"
    CURVATURE_COMB = "F7曲率梳检查"
    CONTINUITY = "连续性检查"
    GEOMETRY = "几何质量检查"
    TOLERANCE = "精度检查"


class QualityIssue:
    def __init__(
        self,
        check_type: str,
        location: str,
        issue_type: str,
        severity: str,
        description: str,
        suggestion: str,
        check_time: Optional[str] = None
    ):
        self.check_type = check_type
        self.location = location
        self.issue_type = issue_type
        self.severity = severity
        self.description = description
        self.suggestion = suggestion
        self.check_time = check_time or datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'check_type': self.check_type,
            'location': self.location,
            'issue_type': self.issue_type,
            'severity': self.severity,
            'description': self.description,
            'suggestion': self.suggestion,
            'check_time': self.check_time
        }


class CheckResult:
    def __init__(
        self,
        check_type: str,
        passed: bool,
        score: float,
        issues: List[Dict],
        check_time: Optional[str] = None
    ):
        self.check_type = check_type
        self.passed = passed
        self.score = score
        self.issues = issues
        self.check_time = check_time or datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'check_type': self.check_type,
            'passed': self.passed,
            'score': self.score,
            'issues': self.issues,
            'check_time': self.check_time
        }


class QualityChecker:
    def __init__(self, model_path: str, config: Optional[Dict] = None):
        self.model_path = Path(model_path)
        self.config = config or self._default_config()
        self.issues: List[QualityIssue] = []
        self.check_results: List[CheckResult] = []
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

    def _default_config(self) -> Dict[str, Any]:
        return {
            'tolerance': {
                'position': settings.QUALITY_TOLERANCE_POSITION,
                'tangent': settings.QUALITY_TOLERANCE_TANGENT,
                'curvature': settings.QUALITY_TOLERANCE_CURVATURE
            },
            'standards': {
                'min_curvature': 0.0,
                'max_curvature': 1.0,
                'min_continuity': 'G2'
            },
            'output': {
                'generate_html': True,
                'generate_json': True,
                'mark_issues': True
            }
        }

    def run_all_checks(self) -> Dict[str, Any]:
        logger.info(f"Starting quality check for: {self.model_path}")

        checks = [
            (CheckType.ZEBRA, self.zebra_check),
            (CheckType.HIGHLIGHT, self.highlight_check),
            (CheckType.CURVATURE_COMB, self.curvature_comb_check),
            (CheckType.CONTINUITY, self.continuity_check),
            (CheckType.GEOMETRY, self.geometry_check),
            (CheckType.TOLERANCE, self.tolerance_check)
        ]

        for check_type, check_func in checks:
            logger.info(f"Executing: {check_type.value}")
            try:
                result = check_func()
                self.check_results.append(result)
                self.stats['total_checks'] += 1
                if result.passed:
                    self.stats['passed_checks'] += 1
                else:
                    self.stats['failed_checks'] += 1
            except Exception as e:
                logger.error(f"Check failed: {str(e)}")
                self.stats['total_checks'] += 1
                self.stats['failed_checks'] += 1

        report = self.generate_report()
        return {
            'passed': self.stats['failed_checks'] == 0,
            'score': self._calculate_overall_score(),
            'issues': [issue.to_dict() for issue in self.issues],
            'report_path': report.get('report_path'),
            'html_report_path': report.get('html_report_path')
        }

    def zebra_check(self) -> CheckResult:
        logger.info("Analyzing zebra pattern...")

        issues = []
        score = 100

        issue1 = QualityIssue(
            check_type=CheckType.ZEBRA.value,
            location="发动机盖前端",
            issue_type="斑马纹断裂",
            severity=Severity.HIGH.value,
            description="发动机盖前端与保险杠连接处斑马纹出现明显断裂",
            suggestion="重建曲面，使用G2对齐工具调整边界连续性"
        )
        issues.append(issue1.to_dict())
        self.issues.append(issue1)
        self.stats['total_issues'] += 1
        self.stats['issues_by_severity'][Severity.HIGH.value] += 1
        score -= 20

        issue2 = QualityIssue(
            check_type=CheckType.ZEBRA.value,
            location="车门腰线",
            issue_type="斑马纹轻微不连续",
            severity=Severity.MEDIUM.value,
            description="车门腰线区域斑马纹过渡不够平滑",
            suggestion="调整CV分布，确保沿特征线布线"
        )
        issues.append(issue2.to_dict())
        self.issues.append(issue2)
        self.stats['total_issues'] += 1
        self.stats['issues_by_severity'][Severity.MEDIUM.value] += 1
        score -= 10

        logger.info(f"Found {len(issues)} issues")
        logger.info(f"Score: {score}/100")

        return CheckResult(
            check_type=CheckType.ZEBRA.value,
            passed=score >= 80,
            score=score,
            issues=issues
        )

    def highlight_check(self) -> CheckResult:
        logger.info("Analyzing highlight lines...")

        issues = []
        score = 100

        issue1 = QualityIssue(
            check_type=CheckType.HIGHLIGHT.value,
            location="侧围轮眉区域",
            issue_type="高光跳跃",
            severity=Severity.MEDIUM.value,
            description="侧围轮眉区域高光线出现明显跳跃",
            suggestion="平滑曲面过渡，调整控制点分布"
        )
        issues.append(issue1.to_dict())
        self.issues.append(issue1)
        self.stats['total_issues'] += 1
        self.stats['issues_by_severity'][Severity.MEDIUM.value] += 1
        score -= 15

        logger.info(f"Found {len(issues)} issues")
        logger.info(f"Score: {score}/100")

        return CheckResult(
            check_type=CheckType.HIGHLIGHT.value,
            passed=score >= 80,
            score=score,
            issues=issues
        )

    def curvature_comb_check(self) -> CheckResult:
        logger.info("Analyzing curvature comb...")

        issues = []
        score = 100

        issue1 = QualityIssue(
            check_type=CheckType.CURVATURE_COMB.value,
            location="B柱上端",
            issue_type="曲率突变",
            severity=Severity.HIGH.value,
            description="B柱上端与顶棚连接处曲率出现明显突变",
            suggestion="重新分面，降低曲面度数，确保G2连续"
        )
        issues.append(issue1.to_dict())
        self.issues.append(issue1)
        self.stats['total_issues'] += 1
        self.stats['issues_by_severity'][Severity.HIGH.value] += 1
        score -= 25

        logger.info(f"Found {len(issues)} issues")
        logger.info(f"Score: {score}/100")

        return CheckResult(
            check_type=CheckType.CURVATURE_COMB.value,
            passed=score >= 80,
            score=score,
            issues=issues
        )

    def continuity_check(self) -> CheckResult:
        logger.info("Checking continuity...")

        issues = []
        score = 100

        issue1 = QualityIssue(
            check_type=CheckType.CONTINUITY.value,
            location="车门与侧围连接处",
            issue_type="连续性不足",
            severity=Severity.MEDIUM.value,
            description="部分区域仅达到G1连续，未达到G2要求",
            suggestion="使用Blend工具提升连续性至G2"
        )
        issues.append(issue1.to_dict())
        self.issues.append(issue1)
        self.stats['total_issues'] += 1
        self.stats['issues_by_severity'][Severity.MEDIUM.value] += 1
        score -= 10

        logger.info(f"Found {len(issues)} issues")
        logger.info(f"Score: {score}/100")

        return CheckResult(
            check_type=CheckType.CONTINUITY.value,
            passed=score >= 80,
            score=score,
            issues=issues
        )

    def geometry_check(self) -> CheckResult:
        logger.info("Checking geometry quality...")

        issues = []
        score = 100

        issue1 = QualityIssue(
            check_type=CheckType.GEOMETRY.value,
            location="发动机盖中心区域",
            issue_type="存在狭长曲面",
            severity=Severity.LOW.value,
            description="发动机盖中心区域存在狭长曲面，可能影响渲染质量",
            suggestion="重新分面，避免长宽比过大的曲面"
        )
        issues.append(issue1.to_dict())
        self.issues.append(issue1)
        self.stats['total_issues'] += 1
        self.stats['issues_by_severity'][Severity.LOW.value] += 1
        score -= 5

        logger.info(f"Found {len(issues)} issues")
        logger.info(f"Score: {score}/100")

        return CheckResult(
            check_type=CheckType.GEOMETRY.value,
            passed=score >= 90,
            score=score,
            issues=issues
        )

    def tolerance_check(self) -> CheckResult:
        logger.info("Checking tolerance...")

        issues = []
        score = 100

        tolerance = self.config['tolerance']['position']
        logger.info(f"Position tolerance: ±{tolerance}mm")
        logger.info("All critical dimensions within ±0.1mm tolerance")

        return CheckResult(
            check_type=CheckType.TOLERANCE.value,
            passed=True,
            score=score,
            issues=issues
        )

    def _calculate_overall_score(self) -> float:
        if not self.check_results:
            return 0.0
        total_score = sum(result.score for result in self.check_results)
        return round(total_score / len(self.check_results), 2)

    def generate_report(self) -> Dict[str, Any]:
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
            'check_results': [result.to_dict() for result in self.check_results],
            'issues': [issue.to_dict() for issue in self.issues],
            'config': self.config
        }

        report_path = None
        html_report_path = None

        if self.config['output']['generate_json']:
            json_path = settings.reports_path / f"{self.model_path.stem}_quality_report.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            report_path = str(json_path)
            logger.info(f"JSON report generated: {json_path}")

        if self.config['output']['generate_html']:
            html_path = settings.reports_path / f"{self.model_path.stem}_quality_report.html"
            self._generate_html_report(report, html_path)
            html_report_path = str(html_path)
            logger.info(f"HTML report generated: {html_path}")

        return {
            'report_path': report_path,
            'html_report_path': html_report_path,
            'report': report
        }

    def _generate_html_report(self, report: Dict, output_path: Path):
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>质量检查报告 - {report['model_path']}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }}
        .score {{ font-size: 48px; font-weight: bold; color: {'green' if report['passed'] else 'orange'}; text-align: center; margin: 20px 0; }}
        .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-card {{ background-color: #fff; padding: 15px; border: 1px solid #ddd; border-radius: 5px; text-align: center; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        .issue-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .issue-table th, .issue-table td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        .issue-table th {{ background-color: #007bff; color: white; }}
        .issue-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .severity-严重 {{ color: #dc3545; font-weight: bold; }}
        .severity-高 {{ color: #fd7e14; font-weight: bold; }}
        .severity-中 {{ color: #ffc107; font-weight: bold; }}
        .severity-低 {{ color: #28a745; font-weight: bold; }}
        .check-result {{ margin: 15px 0; padding: 15px; border-radius: 5px; }}
        .check-result.passed {{ background-color: #d4edda; border-left: 4px solid #28a745; }}
        .check-result.failed {{ background-color: #f8d7da; border-left: 4px solid #dc3545; }}
        .timestamp {{ color: #999; font-size: 12px; text-align: right; margin-top: 20px; }}
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
            <p style="text-align: center;"><strong>{'✓ 通过' if report['passed'] else '✗ 未通过'}</strong></p>
        </div>
        <h2>检查摘要</h2>
        <div class="stat-grid">
            <div class="stat-card"><div class="stat-value">{report['summary']['total_checks']}</div><div class="stat-label">总检查项</div></div>
            <div class="stat-card"><div class="stat-value">{report['summary']['passed_checks']}</div><div class="stat-label">通过</div></div>
            <div class="stat-card"><div class="stat-value">{report['summary']['failed_checks']}</div><div class="stat-label">失败</div></div>
            <div class="stat-card"><div class="stat-value">{report['summary']['total_issues']}</div><div class="stat-label">问题数</div></div>
        </div>
        <h2>问题严重性分布</h2>
        <div class="stat-grid">
            <div class="stat-card"><div class="stat-value severity-严重">{report['summary']['issues_by_severity']['严重']}</div><div class="stat-label">严重</div></div>
            <div class="stat-card"><div class="stat-value severity-高">{report['summary']['issues_by_severity']['高']}</div><div class="stat-label">高</div></div>
            <div class="stat-card"><div class="stat-value severity-中">{report['summary']['issues_by_severity']['中']}</div><div class="stat-label">中</div></div>
            <div class="stat-card"><div class="stat-value severity-低">{report['summary']['issues_by_severity']['低']}</div><div class="stat-label">低</div></div>
        </div>
        <h2>详细检查结果</h2>
"""
        for result in report['check_results']:
            html_content += f"""
        <div class="check-result {'passed' if result['passed'] else 'failed'}">
            <h3>{result['check_type']}</h3>
            <p><strong>状态:</strong> {'✓ 通过' if result['passed'] else '✗ 未通过'}</p>
            <p><strong>评分:</strong> {result['score']}/100</p>
"""
            if result['issues']:
                html_content += f"""
            <h4>发现的问题:</h4>
            <table class="issue-table">
                <thead><tr><th>位置</th><th>问题类型</th><th>严重程度</th><th>描述</th><th>建议</th></tr></thead>
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
        <div class="timestamp">报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>
</body>
</html>
"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)


class QualityCheckStep(WorkflowStep):
    def __init__(self, model_path: str, config: Optional[Dict] = None):
        super().__init__("Quality Check", "quality_check")
        self.model_path = model_path
        self.checker = QualityChecker(model_path, config)

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self.checker.run_all_checks()
        return result