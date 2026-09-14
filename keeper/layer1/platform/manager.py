"""移植自 LangBot pkg/platform/botmgr.py 的精简运行时。

去掉 LangBot 的 Application / 持久化 / 流水线 / 多租户依赖，只保留：
  - RuntimeBot：一个平台适配器的运行实体
  - PlatformManager：加载/启动/停止多个 bot
消息处理由外部注入的 ``message_handler`` 回调完成（收到事件后由调用方决定如何回复）。
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import typing

import keeper.base.adapter as abstract_platform_adapter
import keeper.base.events as platform_events
from keeper.layer1.platform.logger import EventLogger

if typing.TYPE_CHECKING:
    import keeper.base.message as platform_message


MessageHandler = typing.Callable[
    [platform_events.Event, abstract_platform_adapter.AbstractMessagePlatformAdapter],
    typing.Awaitable[None],
]


class RuntimeBot:
    """运行时机器人：包装一个平台适配器并管理其生命周期。"""

    def __init__(
        self,
        name: str,
        adapter: abstract_platform_adapter.AbstractMessagePlatformAdapter,
        logger: EventLogger,
    ) -> None:
        self.name = name
        self.adapter = adapter
        self.logger = logger
        self.enable = True
        self._task: asyncio.Task | None = None
        self._shutdown_lock = asyncio.Lock()
        self._shutdown_complete = False

    async def initialize(
        self,
        message_handler: MessageHandler | None = None,
    ) -> None:
        """注册 LangBot 风格的事件监听器。"""

        async def on_friend_message(
            event: platform_events.FriendMessage,
            adapter: abstract_platform_adapter.AbstractMessagePlatformAdapter,
        ) -> None:
            await self.logger.info(
                f"[{self.name}] friend message: {event.message_chain}",
                message_session_id=f"person_{event.sender.id}",
            )
            if message_handler is not None:
                await message_handler(event, adapter)

        async def on_group_message(
            event: platform_events.GroupMessage,
            adapter: abstract_platform_adapter.AbstractMessagePlatformAdapter,
        ) -> None:
            await self.logger.info(
                f"[{self.name}] group message: {event.message_chain}",
                message_session_id=f"group_{event.group.id}",
            )
            if message_handler is not None:
                await message_handler(event, adapter)

        self.adapter.register_listener(
            platform_events.FriendMessage,
            on_friend_message,
        )
        self.adapter.register_listener(
            platform_events.GroupMessage,
            on_group_message,
        )

    async def run(self) -> None:
        """启动适配器（常驻任务）。"""

        async def exception_wrapper() -> None:
            try:
                await self.adapter.run_async()
            except asyncio.CancelledError:
                raise
            except Exception:
                await self.logger.error(
                    f"[{self.name}] adapter run failed",
                )

        self._task = asyncio.create_task(
            exception_wrapper(),
            name=f"keeper-bot-{self.name}",
        )

    async def shutdown(self) -> None:
        async with self._shutdown_lock:
            if self._shutdown_complete:
                return
            task = self._task
            self._task = None
            try:
                await asyncio.wait_for(self.adapter.kill(), timeout=15)
            finally:
                if task is not None and not task.done():
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
                        await asyncio.wait_for(task, timeout=5)
            self._shutdown_complete = True

    async def send_message(
        self,
        target_type: str,
        target_id: str,
        message: "platform_message.MessageChain",
    ) -> None:
        """主动发送消息。"""
        await self.adapter.send_message(target_type, target_id, message)

    async def reply_message(
        self,
        message_source: platform_events.MessageEvent,
        message: "platform_message.MessageChain",
        quote_origin: bool = False,
    ) -> None:
        """回复消息。"""
        await self.adapter.reply_message(message_source, message, quote_origin)


class PlatformManager:
    """平台管理器：加载多个 bot、统一启停。"""

    def __init__(
        self,
        adapter_classes: dict[str, type[abstract_platform_adapter.AbstractMessagePlatformAdapter]],
        message_handler: MessageHandler | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.adapter_classes = adapter_classes
        self.message_handler = message_handler
        self.logger = logger or logging.getLogger("keeper.layer1.platform")
        self.bots: list[RuntimeBot] = []

    async def load_bots(self, bot_configs: list[dict]) -> None:
        """从配置加载 bots。

        bot_configs 每项形如：
        {
            "name": "qq-bot-1",
            "adapter": "aiocqhttp",          # adapter_classes 的 key
            "config": { ... 平台配置 ... },   # 传给 adapter 的配置 dict
        }
        """
        for cfg in bot_configs:
            adapter_name = cfg.get("adapter", "")
            if adapter_name not in self.adapter_classes:
                self.logger.error("unknown adapter: %s", adapter_name)
                continue
            adapter_cls = self.adapter_classes[adapter_name]
            bot_name = cfg.get("name", adapter_name)
            logger = EventLogger(name=bot_name)
            try:
                adapter = adapter_cls(cfg.get("config", {}), logger)
            except Exception as exc:
                self.logger.error("failed to create adapter %s: %s", bot_name, exc)
                continue
            bot = RuntimeBot(name=bot_name, adapter=adapter, logger=logger)
            await bot.initialize(self.message_handler)
            self.bots.append(bot)
            self.logger.info("bot loaded: %s (%s)", bot_name, adapter_name)

    async def start(self) -> None:
        for bot in self.bots:
            await bot.run()
        self.logger.info("all bots started")

    async def shutdown(self) -> None:
        for bot in self.bots:
            try:
                await bot.shutdown()
            except Exception as exc:
                self.logger.error("failed to shutdown bot %s: %s", bot.name, exc)
        self.bots.clear()
        self.logger.info("all bots stopped")
