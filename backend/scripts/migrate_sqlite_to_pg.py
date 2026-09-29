"""一次性 SQLite → PostgreSQL 数据迁移脚本（Phase 5a 基础设施改造）

前置条件：
  1. 目标库已通过 Alembic 建表：python -m alembic upgrade head
  2. 已安装 psycopg：pip install "psycopg[binary]"

用法（在 backend/ 目录下执行，--target 缺省取 settings.DATABASE_URL）：
  python scripts/migrate_sqlite_to_pg.py \
      --source sqlite:///./evolution_ai.db \
      --target postgresql+psycopg://evolution:CHANGE_ME@localhost:5432/evolution

特性：
  - 按 ORM 依赖顺序（Base.metadata.sorted_tables）逐表迁移，满足外键约束
  - 保留自增主键 ID，迁移后重置 PG 序列，避免后续插入主键冲突
  - 目标表已有数据时跳过（幂等保护，可安全重复执行）
  - 分批读写（每批 500 行），大表不占爆内存

注意：源库需为运行过最新版应用的库（users.role / projects.user_id 等补列
迁移已由 init_db 自动执行）。若缺列，请先用当前版本应用启动一次再迁移。
"""
import argparse

from sqlalchemy import create_engine, inspect, text

from app.config import settings
from app.database import Base

BATCH_SIZE = 500


def migrate(source_url: str, target_url: str) -> None:
    src = create_engine(source_url)
    dst = create_engine(target_url)

    src_tables = set(inspect(src).get_table_names())
    dst_tables = set(inspect(dst).get_table_names())

    total_rows = 0
    for table in Base.metadata.sorted_tables:
        tname = table.name
        if tname not in src_tables:
            print(f"  - {tname}: 源库不存在，跳过")
            continue
        if tname not in dst_tables:
            raise RuntimeError(
                f"目标库缺少表 {tname}，请先在目标库执行：python -m alembic upgrade head"
            )
        with dst.begin() as conn:
            existing = conn.execute(text(f'SELECT COUNT(*) FROM "{tname}"')).scalar_one()
            if existing:
                print(f"  - {tname}: 目标已有 {existing} 行，跳过（幂等保护）")
                continue

        cols = [c.name for c in table.columns]
        moved = 0
        with src.connect() as sconn, dst.begin() as dconn:
            result = sconn.execution_options(yield_per=BATCH_SIZE).execute(table.select())
            for partition in result.partitions():
                dconn.execute(
                    table.insert(),
                    [dict(zip(cols, row)) for row in partition],
                )
                moved += len(partition)
        total_rows += moved
        print(f"  - {tname}: 迁移 {moved} 行")

    # 重置 PG 自增序列到 max(id)，保证后续 INSERT 不与迁移数据主键冲突
    with dst.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in dst_tables:
                continue
            seq = conn.execute(
                text("SELECT pg_get_serial_sequence(:t, 'id')"), {"t": table.name}
            ).scalar()
            if not seq:
                continue
            max_id = conn.execute(
                text(f'SELECT COALESCE(MAX(id), 0) FROM "{table.name}"')
            ).scalar_one()
            if max_id:
                conn.execute(text("SELECT setval(:s, :v)"), {"s": seq, "v": max_id})
            else:
                conn.execute(text("SELECT setval(:s, 1, false)"), {"s": seq})

    print(f"完成：共迁移 {total_rows} 行，序列已校准")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQLite → PostgreSQL 一次性数据迁移")
    parser.add_argument(
        "--source",
        required=True,
        help="源库连接串，例如 sqlite:///./evolution_ai.db",
    )
    parser.add_argument(
        "--target",
        default=settings.DATABASE_URL,
        help="目标库连接串（postgresql+psycopg://...），缺省取 DATABASE_URL 配置",
    )
    args = parser.parse_args()

    if args.target.startswith("sqlite"):
        raise SystemExit("目标必须是 PostgreSQL 连接串（postgresql+psycopg://...）")
    migrate(args.source, args.target)
