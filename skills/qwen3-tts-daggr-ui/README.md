# qwen3-tts-daggr-ui

HuggingFace Space [prithivMLmods/Qwen3-TTS-Daggr-UI](https://huggingface.co/spaces/prithivMLmods/Qwen3-TTS-Daggr-UI)
的 Agent 技能：声音克隆、语音合成、音色设计、音频转写。匿名可用，无需 token / 登录。

这个 Space **不是 Gradio**——它走一条自定义 WebSocket 节点图协议，`gradio_client`
和 `/gradio_api/*` 完全无效。协议细节封装在 `scripts/` 里，直接用 CLI，不要手搓请求。

## 目录结构

```text
qwen3-tts-daggr-ui/
├─ SKILL.md              # 技能入口（AI 读这个）
├─ references/           # 认证 / 协议 / 数据模型 / 工作流 / 报错 / 示例
└─ scripts/              # qwen3tts.py CLI + client.py / daggr.py / exceptions.py
```

## 快速开始

```bash
pip install -r scripts/requirements.txt      # 只有 websockets>=12

python scripts/qwen3tts.py doctor            # 依赖 + Space 状态 + 四算子在线
python scripts/qwen3tts.py clone ref.wav -t "你好世界" -o out.wav --xvector true
python scripts/qwen3tts.py say   -t "Hello" --speaker Serena -o out.wav
python scripts/qwen3tts.py design -t "Hello" -d "warm young female voice" -o out.wav
python scripts/qwen3tts.py asr    audio.wav
```

四个算子（区分大小写）：`Voice Clone` / `Custom Voice` / `Voice Design` / `Qwen3 ASR`。

## 注意事项

- 推理在共享 T4 上跑，**期间服务端不推进度帧**，命令行会长时间静默——正常，别中断、别重试。
- 粗算耗时：约 35s 固定开销 + 约 0.37s/中文字；默认 `--timeout 600` 约撑 1500 字。
- Windows / Git Bash 下载产物时加 `MSYS_NO_PATHCONV=1`。
- 音频会上传到公开共享 Space，**机密音频不要走这条路**。
