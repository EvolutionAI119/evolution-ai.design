"""影响证据系统 · 演示数据种子脚本

生成过去 60 天的真实感数据，用于本地验证与看板联调：
  - PageView：约 60 名访客、按工作日/周末波动的访问、真实页面路径与停留时长
  - Message：中英文留言，约 70% 已回复
  - ExternalReference：多平台引用，约 80% 已核验

用法（在 backend 目录）：
  python -m scripts.seed_analytics            # 默认 60 天
  python -m scripts.seed_analytics --reset    # 清空三表后重建
"""
from __future__ import annotations

import argparse
import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# 允许直接 python scripts/seed_analytics.py 运行
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import (ExternalReference, Message, PageView,
                          SessionLocal, init_db)

PATHS = [
    ("/", 0.28), ("/designer", 0.18), ("/projects", 0.12),
    ("/demo", 0.12), ("/deep-learning", 0.08), ("/quality", 0.06),
    ("/deliver", 0.05), ("/help", 0.05), ("/account", 0.04),
    ("/analytics", 0.02),
]
PLATFORMS = ["知乎", "CSDN", "微信公众号", "B站", "微博", "GitHub",
             "掘金", "小红书", "X / Twitter"]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/17.6",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0) Mobile/15E148",
    "Mozilla/5.0 (Linux; Android 15) Chrome/128.0 Mobile",
]
ZH_MSGS = [
    "平台的 NURBS 曲面生成能力令人印象深刻，期待更多案例。",
    "2D 视图标注非常专业，对教学帮助很大。",
    "建议增加导出 STEP 格式的批量功能。",
    "AI 设计的车身比例控制很精准，名实相符。",
    "请问支持自定义品牌知识库接入吗？",
    "贝叶斯优化闭环的思路很有启发性。",
]
EN_MSGS = [
    "The parametric surface workflow is brilliant, great work!",
    "Can I integrate my own LLM endpoint with the platform?",
    "The class-A quality metrics are well designed.",
]
REPLIES_ZH = ["感谢支持！更多案例正在持续更新。",
              "已记录您的建议，将纳入下一版本规划。",
              "支持 OpenAI 兼容接口接入，详见帮助文档。"]
REPLIES_EN = ["Thanks! More tutorials are on the way.",
              "Yes, any OpenAI-compatible endpoint works."]


def _weighted_path() -> str:
    r = random.random()
    acc = 0.0
    for path, w in PATHS:
        acc += w
        if r <= acc:
            return path
    return "/"


def seed(days: int = 60, reset: bool = False) -> None:
    init_db()
    db = SessionLocal()
    try:
        if reset:
            db.query(PageView).delete()
            db.query(Message).delete()
            db.query(ExternalReference).delete()
            db.commit()

        now = datetime.utcnow()
        start = now - timedelta(days=days)

        # -- 访客池：每人首次出现时间随机分布 --
        visitors = []
        for _ in range(62):
            visitor_id = uuid.uuid4().hex[:24]
            first_day = random.randint(0, days - 1)
            visits_count = random.choices(
                [1, 2, 3, 5, 8, 14],
                weights=[30, 24, 16, 12, 10, 8])[0]
            visitors.append((visitor_id, first_day, visits_count))

        total_views = 0
        for visitor_id, first_day, visits_count in visitors:
            session_seed = uuid.uuid4().hex[:16]
            for n in range(visits_count):
                day_offset = min(first_day + int(abs(random.gauss(
                    n * days / max(visits_count, 1) * 0.6, 6))), days - 1)
                day = start + timedelta(days=day_offset)
                # 周末访问量略低，工作时段集中
                weekend = day.weekday() >= 5
                hour = random.choices(range(24), weights=[
                    1, 1, 1, 1, 1, 2, 4, 7, 10, 12, 11, 9,
                    8, 7, 6, 7, 9, 10, 8, 6, 4, 3, 2, 1])[0]
                ts = day.replace(hour=hour, minute=random.randint(0, 59),
                                 second=random.randint(0, 59))
                if ts > now:
                    continue
                duration = 0
                if random.random() < 0.72:
                    duration = int(abs(random.gauss(140, 110))) + 8
                db.add(PageView(
                    visitor_id=visitor_id,
                    session_id=session_seed if n == 0 else uuid.uuid4().hex[:16],
                    path=_weighted_path(),
                    referrer=random.choice(
                        [None, None, "https://www.google.com/",
                         "https://www.baidu.com/", "https://github.com/"]),
                    ip=f"{random.randint(11, 220)}.{random.randint(0,255)}."
                       f"{random.randint(0,255)}.{random.randint(1,254)}",
                    user_agent=random.choice(USER_AGENTS),
                    duration_seconds=duration,
                    created_at=ts,
                ))
                total_views += 1

        # -- 留言：约 46 条，70% 已回复 --
        names_zh = ["临风", "知行合一", "铸剑人", "青山客", "观潮", "明远",
                    "子衿", "北辰"]
        names_en = ["Alex", "Maria", "Kenji", "Elena", "David"]
        for i in range(46):
            is_en = random.random() < 0.25
            day_offset = random.randint(0, days - 1)
            ts = start + timedelta(
                days=day_offset,
                hours=random.randint(8, 22),
                minutes=random.randint(0, 59))
            if ts > now:
                continue
            replied = random.random() < 0.7
            reply = None
            replied_at = None
            if replied:
                reply = random.choice(REPLIES_EN if is_en else REPLIES_ZH)
                replied_at = ts + timedelta(hours=random.randint(1, 30))
            db.add(Message(
                guest_name=random.choice(names_en if is_en else names_zh),
                content=random.choice(EN_MSGS if is_en else ZH_MSGS),
                contact=None,
                reply=reply,
                replied_by=1 if reply else None,
                replied_at=replied_at,
                is_hidden=random.random() < 0.04,
                created_at=ts,
            ))

        # -- 外部引用：约 28 条，80% 已核验 --
        for i in range(28):
            day_offset = random.randint(0, days - 1)
            ts = start + timedelta(days=day_offset,
                                   hours=random.randint(6, 23))
            if ts > now:
                continue
            verified = random.random() < 0.8
            platform = random.choice(PLATFORMS)
            slug = uuid.uuid4().hex[:10]
            db.add(ExternalReference(
                source_url=f"https://example-{platform[:2].lower()}.com/"
                           f"post/{slug}",
                source_platform=platform,
                target_path=random.choice(["/", "/designer", "/demo",
                                          "/deep-learning"]),
                title=f"转载：EVOLUTION AI 平台介绍 ({i + 1})",
                note=None,
                verified=verified,
                verified_by=1 if verified else None,
                verified_at=ts + timedelta(days=random.randint(1, 5))
                    if verified else None,
                created_at=ts,
            ))

        db.commit()
        pv = db.query(PageView).count()
        ms = db.query(Message).count()
        rf = db.query(ExternalReference).count()
        print(f"seed done: page_views={pv} messages={ms} "
              f"external_references={rf}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    random.seed(20261001)
    seed(days=args.days, reset=args.reset)
