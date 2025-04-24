# AutoVoiceCollation

## 介绍
AutoVoiceCollation是一个基于SenseVoice的自动语音识别（ASR）和文本处理工具，旨在帮助用户快速整理和润色语音转录文本。支持：

- b站视频语音识别
- 本地音频文件语音识别
- LLM自动润色（目前支持deepseek与gemini）
- 自动导出文本文件、PDF或图片

## Quick Start

* 克隆代码
```bash
git clone https://github.com/LogicShao/AutoVoiceCollation
cd AutoVoiceCollation
```

* 创建虚拟环境
```bash
python -m venv venv
```

* 激活虚拟环境

Windows:
```bash
venv\Scripts\activate
```

Linux:
```bash
source venv/bin/activate
```

* 安装依赖
```bash
pip install -r requirements.txt
```

* 运行
```bash
cd src
python main.py
```

## 配置
- `config.py`：配置文件，包含了模型选择等参数。
- `config.ini`：配置文件，请配置你的api密钥。
文件类似于：
```ini
[deepseek]
api_key = sk-xxxxxxxxx

[gemini]
api_key = xxxxxxxx
```

## TODO
- [ ] TODO: 增加对于emoji的支持（情绪识别）
- [ ] TODO: 增加b站cookies的支持
