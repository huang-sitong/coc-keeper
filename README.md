# coc-keeper

多平台消息收发 keeper，消息收发模块移植自 [LangBot](https://github.com/langbot-app/LangBot) 并做适配。

## 目录结构

```text
keeper/
├── base/          # 平台包依赖的公共模型/契约（对应 langbot-plugin SDK）
│   ├── message.py       # MessageChain 及消息组件
│   ├── events.py        # FriendMessage / GroupMessage / FeedbackEvent
│   ├── entities.py      # Friend / Group / GroupMember / Permission
│   ├── adapter.py       # AbstractMessagePlatformAdapter / Converter
│   ├── event_logger.py  # 日志接口
│   └── utils/           # httpclient / image 等基础工具
├── layer1/
│   └── platform/   # 整个平台消息收发包（对应 LangBot pkg/platform）
│       ├── logger.py        # EventLogger 实现
│       ├── manager.py       # RuntimeBot / PlatformManager
│       └── sources/         # 具体平台适配器
│           ├── aiocqhttp.py # OneBot v11（QQ）
│           ├── mattermost.py
│           └── telegram.py
└── top/           # 应用入口/脚本层
    └── __main__.py      # CLI，调用 platform 包
```

## 快速开始

```bash
uv sync
cp keeper.example.yaml keeper.yaml
# 编辑 keeper.yaml 填入你的平台配置
uv run coc-keeper --config keeper.yaml
```

## 新增一个平台适配器

1. 在 `keeper/layer1/platform/sources/` 下新增适配器文件，继承 `keeper.base.adapter.AbstractMessagePlatformAdapter`。
2. 实现 `send_message`、`reply_message`、`register_listener`、`unregister_listener`、`run_async`、`kill`。
3. 在 `keeper/top/__main__.py::build_adapter_classes()` 中登记。
4. 在 `keeper.example.yaml` 增加对应配置示例。

## 依赖方向

```text
top  →  layer1.platform  →  base
应用层      平台运行时          公共契约/模型
```

`base` 只放平台包依赖的 API/entity 等 model；`layer1/platform` 是完整平台包；`top` 只写调用脚本。

## 说明

- 本仓库只移植“消息收发”相关模块，不包含 LangBot 的 LLM 流水线、Web UI、数据库、多租户、插件运行时。
- 后续可继续移植 Telegram、Slack、飞书、钉钉等适配器。
