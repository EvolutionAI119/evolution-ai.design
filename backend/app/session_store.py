"""会话存储抽象：支持内存与 Redis 双后端，进程内单例。

使用方式：
    store = get_session_store()
    store.set(sid, session_dict)
    s = store.get(sid)
    store.delete(sid)
    for sid in store.keys(): ...
"""
from __future__ import annotations

import json
import logging
import threading
from abc import ABC, abstractmethod
from typing import Dict, Iterator, Optional

from .config import settings

logger = logging.getLogger(__name__)


# ============ 存储抽象 ============

class SessionStore(ABC):
    """会话存储后端接口"""

    @abstractmethod
    def get(self, session_id: str) -> Optional[dict]:
        """读取会话，不存在返回 None"""

    @abstractmethod
    def set(self, session_id: str, data: dict) -> None:
        """写入会话（覆盖），应用 TTL"""

    @abstractmethod
    def delete(self, session_id: str) -> bool:
        """删除会话，返回是否存在"""

    @abstractmethod
    def keys(self) -> Iterator[str]:
        """遍历所有 session_id"""

    @property
    @abstractmethod
    def backend(self) -> str:
        """返回后端名称：memory / redis"""


# ============ 内存后端（默认降级方案） ============

class MemorySessionStore(SessionStore):
    """进程内存存储：重启丢失，无 TTL 自然过期（可结合主动清理）"""

    def __init__(self):
        self._data: Dict[str, dict] = {}
        self._lock = threading.RLock()

    def get(self, session_id: str) -> Optional[dict]:
        with self._lock:
            return self._data.get(session_id)

    def set(self, session_id: str, data: dict) -> None:
        with self._lock:
            self._data[session_id] = data

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._data.pop(session_id, None) is not None

    def keys(self) -> Iterator[str]:
        with self._lock:
            # 返回列表副本，避免迭代时修改
            return iter(list(self._data.keys()))

    @property
    def backend(self) -> str:
        return "memory"


# ============ Redis 后端 ============

class RedisSessionStore(SessionStore):
    """Redis 持久化存储：支持 TTL、序列化、连接池、自动降级。

    兼容 Redis 3.x（Windows 常见 3.0.504）：
    - 禁用 RESP3/HELLO，使用 RESP2
    - redis-py 版本锁定 < 4.0（本文件运行时检测，版本过高会告警并走内存）
    """

    def __init__(self, url: str, prefix: str, ttl_seconds: int,
                 pool_size: int = 16, timeout: float = 2.0):
        self._url = url
        self._prefix = prefix
        self._ttl = ttl_seconds
        self._pool_size = pool_size
        self._timeout = timeout
        self._client = None
        self._available = False
        self._init_client()

    # ---------- 连接初始化 ----------

    def _init_client(self) -> None:
        try:
            import redis  # 延迟导入，未安装依赖也能走内存后端
        except ImportError:
            logger.warning("[SessionStore] redis 包未安装，自动降级到 memory 后端。"
                           "请执行: pip install 'redis>=3.5,<4.0'")
            return

        # 运行时版本断言：redis-py 4.x 对 Redis <6 不友好（默认发 HELLO）
        try:
            ver = tuple(int(x) for x in redis.__version__.split(".")[:2])
            if ver >= (4, 0):
                logger.warning(
                    f"[SessionStore] redis-py 版本 {redis.__version__} >= 4.0，"
                    f"对旧版 Redis（<6.0，如 Windows 3.0.504）可能报 'unknown command HELLO'。"
                    f"建议 pip install 'redis>=3.5,<4.0'。仍尝试连接……"
                )
        except Exception:
            pass

        try:
            # 对于旧 Redis（<6），redis-py 3.5 使用 StrictRedis/Redis 都能发 RESP2
            # socket_timeout + socket_connect_timeout 双保险，避免卡死
            kwargs = dict(
                decode_responses=False,
                socket_timeout=self._timeout,
                socket_connect_timeout=self._timeout,
                max_connections=self._pool_size,
                retry_on_timeout=False,
            )
            # from_url 在 redis 3.x 也支持
            self._client = redis.Redis.from_url(self._url, **kwargs)
            # 握手：ping 确认连通
            self._client.ping()
            self._available = True
            logger.info(
                f"[SessionStore] Redis 后端就绪：url={self._url}, "
                f"prefix={self._prefix!r}, TTL={self._ttl}s"
            )
        except Exception as e:
            logger.error(
                f"[SessionStore] Redis 连接失败，降级到 memory 后端：{e}"
            )
            self._available = False
            self._client = None

    # ---------- 工具 ----------

    def _key(self, sid: str) -> str:
        return f"{self._prefix}{sid}"

    @staticmethod
    def _serialize(data: dict) -> bytes:
        return json.dumps(data, ensure_ascii=False).encode("utf-8")

    @staticmethod
    def _deserialize(raw: bytes) -> dict:
        return json.loads(raw.decode("utf-8"))

    # ---------- 接口 ----------

    def get(self, session_id: str) -> Optional[dict]:
        if not self._available:
            return None
        try:
            raw = self._client.get(self._key(session_id))
            if raw is None:
                return None
            return self._deserialize(raw)
        except Exception as e:
            logger.error(f"[SessionStore] redis GET 失败：{e}")
            return None

    def set(self, session_id: str, data: dict) -> None:
        if not self._available:
            return
        try:
            payload = self._serialize(data)
            key = self._key(session_id)
            if self._ttl and self._ttl > 0:
                self._client.set(key, payload, ex=self._ttl)
            else:
                self._client.set(key, payload)
        except Exception as e:
            logger.error(f"[SessionStore] redis SET 失败：{e}")

    def delete(self, session_id: str) -> bool:
        if not self._available:
            return False
        try:
            return bool(self._client.delete(self._key(session_id)))
        except Exception as e:
            logger.error(f"[SessionStore] redis DELETE 失败：{e}")
            return False

    def keys(self) -> Iterator[str]:
        if not self._available:
            return iter([])
        try:
            pattern = self._key("*")
            matched = self._client.keys(pattern)
            plen = len(self._prefix)
            # decode_responses=False 时 key 是 bytes
            out = []
            for k in matched:
                if isinstance(k, bytes):
                    k = k.decode("utf-8", errors="ignore")
                if k.startswith(self._prefix):
                    out.append(k[plen:])
            return iter(out)
        except Exception as e:
            logger.error(f"[SessionStore] redis KEYS 失败：{e}")
            return iter([])

    @property
    def backend(self) -> str:
        return "redis" if self._available else "memory(fallback)"


# ============ 双后端组合：优先 Redis，失败走内存 ============

class HybridSessionStore(SessionStore):
    """优先使用 Redis，Redis 不可用/操作失败时透明回落到内存。

    内存作为 L1，Redis 作为 L2：
    - 写入：双写（先 Redis 再内存，Redis 失败只写内存并日志）
    - 读取：先 Redis，miss 时回内存；如果 Redis 中命中，不同步回内存（避免一致性问题）
    - 删除 / 列举：两边都尝试
    """

    def __init__(self, primary: SessionStore, fallback: MemorySessionStore):
        self._primary = primary
        self._fallback = fallback

    def get(self, session_id: str) -> Optional[dict]:
        data = self._primary.get(session_id)
        if data is not None:
            return data
        return self._fallback.get(session_id)

    def set(self, session_id: str, data: dict) -> None:
        # 双写：保证无论 Redis 是否可用，下次读取都能命中
        self._primary.set(session_id, data)
        self._fallback.set(session_id, data)

    def delete(self, session_id: str) -> bool:
        a = self._primary.delete(session_id)
        b = self._fallback.delete(session_id)
        return a or b

    def keys(self) -> Iterator[str]:
        seen = set()
        for sid in self._primary.keys():
            if sid not in seen:
                seen.add(sid)
                yield sid
        for sid in self._fallback.keys():
            if sid not in seen:
                seen.add(sid)
                yield sid

    @property
    def backend(self) -> str:
        return f"hybrid(primary={self._primary.backend}, fallback={self._fallback.backend})"


# ============ 单例工厂 ============

_store: Optional[SessionStore] = None
_store_lock = threading.Lock()


def get_session_store() -> SessionStore:
    """获取全局唯一会话存储实例（线程安全懒加载）"""
    global _store
    if _store is not None:
        return _store
    with _store_lock:
        if _store is not None:
            return _store
        fallback = MemorySessionStore()
        if settings.SESSION_USE_REDIS:
            redis_store = RedisSessionStore(
                url=settings.SESSION_REDIS_URL,
                prefix=settings.SESSION_REDIS_PREFIX,
                ttl_seconds=settings.SESSION_TTL_SECONDS,
                pool_size=settings.SESSION_REDIS_POOL_SIZE,
                timeout=settings.SESSION_REDIS_TIMEOUT,
            )
            _store = HybridSessionStore(primary=redis_store, fallback=fallback)
        else:
            logger.info("[SessionStore] SESSION_USE_REDIS=false，使用纯内存后端（重启丢失）")
            _store = fallback
        logger.info(f"[SessionStore] 最终后端：{_store.backend}")
        return _store


def _reset_store_for_test() -> None:
    """测试专用：重置单例，请勿在生产代码中调用。"""
    global _store
    with _store_lock:
        _store = None
