# 算子、端口与数据模型

## 四个可执行算子（`schema <node>` 是实时权威来源）

| 算子（node_name） | node_id | 输入端口 | 输出端口 |
|---|---|---|---|
| Voice Clone | `Voice_Clone` | `ref_audio`(audio), `ref_text`, `target_text`, `language`, `use_xvector_only`(checkbox), `model_size` | `cloned_audio`, `status` |
| Custom Voice | `Custom_Voice` | `text`, `language`, `speaker`, `instruct`, `model_size` | `tts_audio`, `status` |
| Voice Design | `Voice_Design` | `text`, `language`, `voice_description` | `generated_audio`, `status` |
| Qwen3 ASR | `Qwen3_ASR` | `audio_upload`(audio), `lang_disp` | `detected_lang`, `transcription`, `status` |

节点名带空格且区分大小写，必须精确匹配。节点图里另外还有一批 INPUT 节点
（id 形如 `Voice_Clone__ref_audio`），它们是参数载体，`type` 不是 `FN`，**不能
直接 run**。

## 必填端口（本地强制，服务端不校验）

服务端对漏传参数**不报错**：实测漏传 `text` 仍返回 `status:"Success"` 并给出一个
可下载的 wav（算子自带默认值）。少参的唯一后果是"产出的音频不是你想要的"，
没有任何信号提示。因此必填只能声明在客户端并本地拦截：

| 算子 | 必填 |
|---|---|
| Custom Voice | `text` |
| Voice Design | `text`, `voice_description` |
| Voice Clone | `ref_audio`, `target_text` |
| Qwen3 ASR | `audio_upload` |

`ref_text` **不是必填**——它只在 ICL 模式（`use_xvector_only=False`）下参与对齐；
x-vector 模式仅取说话人向量，逐字稿可以不精确甚至留空。

## 枚举值（区分大小写；写错只在跑完一整次 GPU 推理后才暴露）

- `model_size`：`0.6B` | `1.7B`（默认 `1.7B`）
- `speaker`：`Aiden` `Dylan` `Eric` `Ono_anna` `Ryan` `Serena` `Sohee` `Uncle_fu` `Vivian`
- `language` / `lang_disp`：`Auto` + 30 种。Voice Clone 的 `language` 下拉实测为
  `Auto Chinese English Japanese Korean French German Spanish Portuguese Russian`；
  Custom Voice / Voice Design 同该列表；ASR 的 `lang_disp` 列表更长，含
  `Cantonese Indonesian Thai Vietnamese Turkish` 等。
  **权威列表用 `schema <node>` 实时取**，不要凭记忆写。

## 控件类型（决定取值怎么规整）

- `audio`：本地文件路径 → 编码成 data URL；`data:` / `http(s):` 透传。
- `checkbox`：`use_xvector_only`。CLI / JSON 传来的 `"false"` 在 Python 里是**真值**，
  原样发出会静默打开开关，必须显式收敛成 bool。
- `dropdown`：闭合枚举集合，客户端提前比对，错了立刻报而不是等推理跑完。
- `textbox`：原样传字符串。

## RunResult 结构

| 字段 | 含义 |
|---|---|
| `ok` | `status.strip().lower() == "success"` —— **唯一可信的成功信号** |
| `status` | 服务端原文。失败时是 `Text required`、`Error: Unsupported speakers: [...]` 这类文案 |
| `audio` | 产物服务端路径 `/file/tmp/<uuid>.wav`，按 `cloned_audio`/`generated_audio`/`tts_audio`/`audio` 顺序取第一个 |
| `text` | ASR 转写文本（取 `transcription`，其次 `detected_lang`） |
| `saved_to` | 落盘路径（仅当传了 `-o`） |
| `execution_time_ms` | 服务端报告的推理耗时 |
| `run_id` | 可用于 `cancel` |
| `outputs` | 全部输出端口原样 |

## 产物音频规格

24000 Hz / 单声道 / 16-bit PCM WAV。下载后可用 `wave` 模块直接读取校验
（声道数、采样率、时长、RMS）。RMS 过低说明是静音——那也是"失败"的一种。
