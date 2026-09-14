"""coc-keeper 移植自检：消息模型 + 运行时事件分发。"""
import asyncio

import keeper.base.adapter as abstract
import keeper.base.entities as entities
import keeper.base.events as events
import keeper.base.message as message
from keeper.layer1.platform.logger import EventLogger
from keeper.layer1.platform.manager import RuntimeBot


class FakeAdapter(abstract.AbstractMessagePlatformAdapter):
    listeners: dict = {}
    sent: list = []

    def __init__(self, config, logger):
        super().__init__(config=config, logger=logger)
        self.listeners = {}
        self.sent = []

    async def send_message(self, target_type, target_id, chain):
        self.sent.append(("send", target_type, target_id, chain))

    async def reply_message(self, source, chain, quote_origin=False):
        self.sent.append(("reply", source, chain, quote_origin))

    def register_listener(self, event_type, callback):
        self.listeners[event_type] = callback

    def unregister_listener(self, event_type, callback):
        self.listeners.pop(event_type, None)

    async def run_async(self):
        await asyncio.sleep(3600)

    async def kill(self):
        return True


def test_message_chain_roundtrip():
    chain = message.MessageChain(
        [
            message.Plain(text="hello"),
            message.At(target=123, display="foo"),
            message.Image(url="https://example.com/a.jpg"),
        ]
    )
    dumped = chain.model_dump()
    restored = message.MessageChain.model_validate(dumped)
    assert str(restored) == "hello@foo[Image]"


def test_runtime_event_dispatch():
    adapter = FakeAdapter({}, EventLogger("fake"))
    received = []

    async def handler(event, adp):
        received.append(event)
        await adp.reply_message(
            event,
            message.MessageChain([message.Plain(text="pong")]),
            quote_origin=True,
        )

    async def run():
        bot = RuntimeBot("fake", adapter, EventLogger("fake"))
        await bot.initialize(handler)
        ev = events.FriendMessage(
            sender=entities.Friend(id=1, nickname="n", remark=""),
            message_chain=message.MessageChain([message.Plain(text="hi")]),
            time=123.0,
        )
        cb = adapter.listeners[events.FriendMessage]
        await cb(ev, adapter)
        assert received[0] is ev
        assert adapter.sent[0][0] == "reply"

    asyncio.run(run())


if __name__ == "__main__":
    test_message_chain_roundtrip()
    test_runtime_event_dispatch()
    print("all tests passed")
