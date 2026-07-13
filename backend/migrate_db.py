"""
数据库迁移脚本：为持久化改造添加新字段和新表
- model_files 表添加 car_data_json 列
- 创建 model_variants 表
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "evolution_ai.db"


def migrate():
    print(f"数据库路径: {DB_PATH}")
    if not DB_PATH.exists():
        print("数据库文件不存在，将由 SQLAlchemy 自动创建")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 检查并添加 car_data_json 列
    cursor.execute("PRAGMA table_info(model_files)")
    columns = [row[1] for row in cursor.fetchall()]

    if "car_data_json" not in columns:
        cursor.execute("ALTER TABLE model_files ADD COLUMN car_data_json TEXT")
        print("[OK] 添加 model_files.car_data_json 列")
    else:
        print("[SKIP] model_files.car_data_json 列已存在")

    if "params_json" not in columns:
        cursor.execute("ALTER TABLE model_files ADD COLUMN params_json TEXT")
        print("[OK] 添加 model_files.params_json 列")
    else:
        print("[SKIP] model_files.params_json 列已存在")

    # 创建 model_variants 表
    cursor.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name='model_variants'
    """)
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE model_variants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                parent_variant_id INTEGER,
                params_json TEXT,
                description TEXT,
                car_data_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES model_files(id),
                FOREIGN KEY (parent_variant_id) REFERENCES model_variants(id)
            )
        """)
        print("[OK] 创建 model_variants 表")
    else:
        print("[SKIP] model_variants 表已存在")

    conn.commit()
    conn.close()
    print("迁移完成!")


if __name__ == "__main__":
    migrate()
