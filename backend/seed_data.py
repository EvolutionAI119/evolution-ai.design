"""添加模拟数据到数据库"""
import json
import sys
sys.path.insert(0, '.')
from app.database import SessionLocal, init_db, Project, ModelFile, QualityReport
from datetime import datetime

def seed():
    init_db()
    db = SessionLocal()
    
    try:
        if db.query(Project).first():
            print("数据库已有数据，跳过初始化")
            return
            
        project = Project(
            name="EV-Sedan Concept",
            description="电动汽车设计项目",
            status="active"
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        print(f"创建项目: {project.id} - {project.name}")
        
        default_params = {
            "overall_length": 4950, "overall_width": 1880, "overall_height": 1460,
            "wheel_base": 2890, "track_width": 1600, "ground_clearance": 140,
            "hood_length": 1050, "roof_height": 550, "wheel_diameter": 680,
            "windshield_angle": 35, "rear_window_angle": 28, "rear_slant_angle": 18
        }
        
        models = [
            {"name": "EV-Sedan Concept v1", "file_type": "car"},
            {"name": "SUV-A Platform", "file_type": "car"},
            {"name": "Sports Coupe V2", "file_type": "car"},
            {"name": "Hatchback Design", "file_type": "car"},
        ]
        
        for i, m in enumerate(models):
            model = ModelFile(
                project_id=project.id,
                filename=f"{m['name'].lower().replace(' ', '-')}.json",
                filepath=f"data/exports/model_{i+1}/{m['name'].lower().replace(' ', '-')}.json",
                file_type=m["file_type"],
                file_size=1024000,
                status="uploaded",
                params_json=json.dumps(default_params, ensure_ascii=False),
                car_data_json=json.dumps({"name": m["name"], "components": [], "total_surfaces": 34}, ensure_ascii=False)
            )
            db.add(model)
        db.commit()
        print(f"创建 {len(models)} 个模型")
        
        report = QualityReport(
            project_id=project.id,
            model_id=1,
            overall_score=92.5,
            passed=True,
            report_data=json.dumps({"score": 92.5, "checks": {"continuity_g0": True, "continuity_g1": True}}, ensure_ascii=False)
        )
        db.add(report)
        db.commit()
        print(f"创建质量报告: {report.id}")
        
        print("✅ 模拟数据初始化完成")
        print(f"项目ID: {project.id}")
        print(f"模型ID: 1-4")
        
    finally:
        db.close()

if __name__ == "__main__":
    seed()