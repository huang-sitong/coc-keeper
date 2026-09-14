"""coc-keeper 命令行入口：加载配置并启动多平台消息收发。

示例：
    python -m keeper.top --config keeper.example.yaml
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

import yaml

from keeper.layer1.platform.sources.aiocqhttp import AiocqhttpAdapter
from keeper.layer1.platform.sources.mattermost import MattermostAdapter
from keeper.layer1.platform.sources.telegram import TelegramAdapter
from keeper.layer1.platform.manager import PlatformManager


def build_adapter_classes() -> dict:
    """目前注册已移植的适配器。后续新增适配器在这里登记。"""
    return {
        "aiocqhttp": AiocqhttpAdapter,
        "mattermost": MattermostAdapter,
        "telegram": TelegramAdapter,
    }


async def default_message_handler(event, adapter):
    """默认处理器：仅记录收到的消息，不自动回复。

    如需接入业务逻辑/LLM，请在这里实现，并通过 adapter.reply_message 回复。
    """
    logging.getLogger("keeper.handler").info(
        "received message: %s", str(event.message_chain)
    )


async def amain(config_path: str) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    manager = PlatformManager(
        adapter_classes=build_adapter_classes(),
        message_handler=default_message_handler,
    )
    await manager.load_bots(config.get("bots", []))
    await manager.start()

    print("coc-keeper started. Press Ctrl+C to stop.", flush=True)
    try:
        # 保持事件循环运行
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await manager.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="coc-keeper multi-platform message keeper")
    parser.add_argument("--config", default="keeper.example.yaml", help="YAML config file path")
    args = parser.parse_args()
    try:
        asyncio.run(amain(args.config))
    except KeyboardInterrupt:
        pass
    except FileNotFoundError:
        print(f"config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
