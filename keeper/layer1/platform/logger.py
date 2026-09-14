"""移植自 LangBot pkg/platform/logger.py 的精简 EventLogger。

LangBot 的 EventLogger 依赖 Application/Storage/ExecutionContext；
这里去掉这些依赖，只保留“内存日志 + Python logging”能力，便于在
coc-keeper 中直接使用。
"""
from __future__ import annotations

import enum
import logging
import time
import traceback
import typing

import pydantic

import keeper.base.message as platform_message
import keeper.base.event_logger as abstract_platform_event_logger


class EventLogLevel(enum.Enum):
    """日志级别"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class EventLog(pydantic.BaseModel):
    seq_id: int
    """日志序号"""

    timestamp: int
    """日志时间戳"""

    level: EventLogLevel
    """日志级别"""

    text: str
    """日志文本"""

    message_session_id: typing.Optional[str] = None
    """消息会话ID"""

    def to_json(self) -> dict:
        return {
            "seq_id": self.seq_id,
            "timestamp": self.timestamp,
            "level": self.level.value,
            "text": self.text,
            "message_session_id": self.message_session_id,
        }


MAX_LOG_COUNT = 200
DELETE_COUNT_PER_TIME = 50
MAX_LOG_TEXT_CHARS = 20000


class EventLogger(abstract_platform_event_logger.AbstractEventLogger):
    """适配到 coc-keeper 的事件日志器：写 Python logging + 内存环形日志。"""

    def __init__(self, name: str, logger: logging.Logger | None = None):
        self.name = name
        self.logs: list[EventLog] = []
        self.seq_id_inc = 0
        self._logger = logger or logging.getLogger(f"keeper.{name}")

    async def get_logs(
        self,
        from_seq_id: int,
        max_count: int,
    ) -> tuple[list[EventLog], int]:
        """获取日志，从 from_seq_id 开始获取 max_count 条。"""
        if len(self.logs) == 0:
            return [], 0

        if from_seq_id <= -1:
            from_seq_id = self.logs[-1].seq_id

        min_seq_id_in_logs = self.logs[0].seq_id
        max_seq_id_in_logs = self.logs[-1].seq_id

        if from_seq_id < min_seq_id_in_logs:
            return [], len(self.logs)

        if from_seq_id > max_seq_id_in_logs and from_seq_id - max_count > max_seq_id_in_logs:
            return [], len(self.logs)

        end_index = 1
        for i, log in enumerate(self.logs):
            if log.seq_id >= from_seq_id:
                end_index = i + 1
                break

        start_index = max(0, end_index - max_count)
        if max_count > 0:
            return self.logs[start_index:end_index], len(self.logs)
        return [], len(self.logs)

    async def _truncate_logs(self) -> None:
        if len(self.logs) > MAX_LOG_COUNT:
            self.logs = self.logs[DELETE_COUNT_PER_TIME:]

    async def _add_log(
        self,
        level: EventLogLevel,
        text: str,
        images: typing.Optional[list[platform_message.Image]] = None,
        message_session_id: typing.Optional[str] = None,
        no_throw: bool = True,
    ) -> None:
        try:
            text = str(text)
            if len(text) > MAX_LOG_TEXT_CHARS:
                marker = "\n[log truncated]"
                text = text[: MAX_LOG_TEXT_CHARS - len(marker)] + marker

            if message_session_id is None:
                message_session_id = ""
            if not isinstance(message_session_id, str):
                message_session_id = str(message_session_id)

            self.logs.append(
                EventLog(
                    seq_id=self.seq_id_inc,
                    timestamp=int(time.time()),
                    level=level,
                    text=text,
                    message_session_id=message_session_id,
                )
            )
            self.seq_id_inc += 1
            await self._truncate_logs()

            # 同时输出到 Python logging
            getattr(self._logger, level.value)(text)
        except Exception as e:
            if not no_throw:
                raise e
            traceback.print_exc()

    async def info(
        self,
        text: str,
        images: typing.Optional[list[platform_message.Image]] = None,
        message_session_id: typing.Optional[str] = None,
        no_throw: bool = True,
    ) -> None:
        await self._add_log(
            level=EventLogLevel.INFO,
            text=text,
            images=images,
            message_session_id=message_session_id,
            no_throw=no_throw,
        )

    async def debug(
        self,
        text: str,
        images: typing.Optional[list[platform_message.Image]] = None,
        message_session_id: typing.Optional[str] = None,
        no_throw: bool = True,
    ) -> None:
        await self._add_log(
            level=EventLogLevel.DEBUG,
            text=text,
            images=images,
            message_session_id=message_session_id,
            no_throw=no_throw,
        )

    async def warning(
        self,
        text: str,
        images: typing.Optional[list[platform_message.Image]] = None,
        message_session_id: typing.Optional[str] = None,
        no_throw: bool = True,
    ) -> None:
        await self._add_log(
            level=EventLogLevel.WARNING,
            text=text,
            images=images,
            message_session_id=message_session_id,
            no_throw=no_throw,
        )

    async def error(
        self,
        text: str,
        images: typing.Optional[list[platform_message.Image]] = None,
        message_session_id: typing.Optional[str] = None,
        no_throw: bool = True,
    ) -> None:
        await self._add_log(
            level=EventLogLevel.ERROR,
            text=text,
            images=images,
            message_session_id=message_session_id,
            no_throw=no_throw,
        )
