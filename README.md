# flashcards-ai-lite

把一段学习文本一键变成记忆闪卡，并基于 **Leitner 盒间隔复习系统** 安排复习节奏。零第三方依赖，Python 3.10+ 直接运行。

## 功能简介

- **两种闪卡**
  - **填空卡（cloze）**：在关键句里遮蔽术语，正面是带 `____` 的句子，背面是术语；
  - **问答卡（qa）**：从「X 是指 Y」「X is Y」这类定义句式中自动抽取。
- **双模式生成**
  - 有 `OPENAI_API_KEY` 时，调用 OpenAI 兼容接口让 LLM 直接输出 JSON 闪卡；
  - **没有 key 也能完整使用**：自动降级到纯规则式抽取，开箱即用。
- **Leitner 间隔复习**：卡片放在 1~5 号盒子里，答对升一盒（复习间隔变长），答错打回 1 盒。各盒间隔为 1 / 3 / 7 / 14 / 30 天，复习状态持久化到本地 JSON。
- **命令行三个子命令**：`build`（生成）、`review`（复习到期卡）、`stats`（统计）。

## 快速开始

无需安装任何第三方包，克隆后即可运行：

```bash
git clone https://github.com/ljiang9/flashcards-ai-lite.git
cd flashcards-ai-lite
python3 -m flashcardslite --help
```

## 使用示例

准备一段学习笔记 `note.txt`：

```text
光合作用是植物利用光能，把二氧化碳和水合成有机物的过程。
机器学习是一门让计算机从数据中自动学习规律的学科。
深度学习是机器学习的一个分支，使用多层神经网络。
```

**1. 生成闪卡**

```bash
python3 -m flashcardslite build --file note.txt --preview 5
```

输出（无 key 时为规则式）：

```
[规则式] 卡组「default」：新增 6 张，共 6 张。
  - [qa] 什么是「光合作用」？  =>  植物利用光能，把二氧化碳和水合成有机物的过程
  - [cloze] ____ 是植物利用光能，把二氧化碳和水合成有机物的过程。  =>  光合作用
  ...
```

也可以直接传文本：

```bash
python3 -m flashcardslite build --text "递归是指函数在定义中调用自身的编程技巧。"
```

**2. 复习今天到期的卡片**

```bash
python3 -m flashcardslite review
```

按提示逐张看题、回忆、揭晓答案，然后回答 `y`（认识）或 `n`（忘记）。答对自动升盒，答错打回 1 盒。

**3. 查看统计**

```bash
python3 -m flashcardslite stats
```

输出示例：

```
卡组「default」：共 6 张，今天到期 6 张，已掌握（4-5 盒）0 张。
  1 盒（ 1 天间隔）:   6 张，到期   6 张  ######
  2 盒（ 3 天间隔）:   0 张，到期   0 张
  ...
```

## 没有 API key 怎么运行？

完全可以。本项目**默认就是规则式**：只要不设置 `OPENAI_API_KEY`，`build` 会自动用内置的中文/英文句式规则挖空、抽取问答卡，所有功能正常使用。

如果想启用 LLM 生成，设置环境变量即可（通过标准库 `urllib` 请求 OpenAI 兼容接口，无需任何 SDK）：

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"   # 可选，可换成其它兼容端点
export OPENAI_MODEL="gpt-4o-mini"                    # 可选
```

设置后若 LLM 调用失败，程序会自动降级回规则式并打印提示，不会中断。

## 数据存哪里？

卡片库存放在 `~/.flashcards_lite/store.json`，可用 `--data 路径` 指定其它位置（方便测试或多份数据）。

## 目录结构

```
flashcards-ai-lite/
├── flashcardslite/
│   ├── __main__.py     # 支持 python -m flashcardslite
│   ├── cli.py          # argparse：build / review / stats
│   ├── extractor.py    # 规则式挖空与问答卡抽取
│   ├── leiter.py       # Leitner 盒进退与到期计算
│   ├── store.py        # 本地 JSON 持久化
│   └── llm.py          # 可选 LLM（urllib，无 key 自动降级）
├── tests/              # unittest 测试
├── README.md
├── LICENSE
└── .gitignore
```

## 运行测试

```bash
python3 -m compileall flashcardslite
python3 -m unittest discover -s tests
```

## 许可证

本项目基于 [MIT 许可证](./LICENSE) 开源。
