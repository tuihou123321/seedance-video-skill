# Seedance Video Skill

用火山引擎方舟 Ark API Key 调用 Doubao Seedance，支持文生视频、首帧图生视频、首尾帧图生视频、多模态参考视频生成、任务查询和视频下载。

这个仓库是一套 Codex / Agent skill，也可以直接把 `scripts/seedance_video.py` 当成命令行工具使用。脚本只使用 Python 标准库，不会保存你的 API Key。

## 功能

- 文生视频：输入提示词生成视频。
- 图生视频：支持首帧、首尾帧控制。
- 参考素材：支持参考图片、参考视频、参考音频 URL。
- 任务管理：创建任务、轮询任务、查询任务、取消任务。
- 本地下载：任务成功后自动保存 `video_url` 到本地文件。
- 安全配置：从环境变量或本地 `.env` 文件读取 API Key，不写入仓库。

## 获取火山引擎 API Key

1. 打开火山方舟控制台 API Key 页面：
   https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
2. 登录火山引擎账号，并确认已经开通火山方舟。
3. 在控制台左上角选择你的资源项目 Project。
4. 创建 API Key。建议按项目隔离权限，需要更安全时使用自定义权限和 IP 白名单。
5. 确认已开通要调用的 Seedance 模型，并保证账户余额或资源包满足模型开通与调用要求。

官方文档入口：

- API Key 获取与配置：https://www.volcengine.com/docs/82379/1541594
- API Key 管理：https://www.volcengine.com/docs/82379/1361424
- Base URL 与鉴权：https://www.volcengine.com/docs/82379/1298459
- Seedance 视频生成 API：https://www.volcengine.com/docs/82379/1393047

## 配置 API Key

推荐使用环境变量：

```bash
export ARK_API_KEY="your-volcengine-ark-api-key"
```

如果你想长期生效：

```bash
echo 'export ARK_API_KEY="your-volcengine-ark-api-key"' >> ~/.zshrc
source ~/.zshrc
```

也可以在项目根目录创建本地 `.env` 文件：

```bash
ARK_API_KEY=your-volcengine-ark-api-key
```

然后调用脚本时加：

```bash
python scripts/seedance_video.py create --env-file .env --prompt "A product reveal shot" --dry-run
```

注意：不要把真实 API Key 提交到 GitHub。仓库已通过 `.gitignore` 忽略 `.env` 和生成的视频文件。

## 作为 Codex Skill 使用

把仓库放到你的 Codex skills 目录，例如：

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/tuihou123321/seedance-video-skill.git ~/.codex/skills/seedance-video
```

然后在 Codex 里可以这样说：

```text
用 seedance-video 生成一个 5 秒竖屏产品短视频：一杯咖啡在雨夜窗边冒热气，电影感，慢推镜头。
```

这个 skill 会优先读取 `ARK_API_KEY`。如果没有设置，也会尝试读取：

- `SEEDANCE_API_KEY`
- `VOLCENGINE_API_KEY`
- `VOLC_API_KEY`

## 命令行使用

查看内置模型别名：

```bash
python scripts/seedance_video.py models
```

先 dry-run 检查请求体，不产生费用：

```bash
python scripts/seedance_video.py create \
  --prompt "A cinematic product reveal shot, slow camera push in, soft studio light" \
  --ratio 9:16 \
  --duration 5 \
  --dry-run
```

文生视频，并等待结果下载：

```bash
python scripts/seedance_video.py create \
  --prompt "A close-up cinematic shot of a coffee cup on a rainy window, steam rising slowly" \
  --ratio 9:16 \
  --duration 5 \
  --poll \
  --output ./outputs/seedance.mp4
```

首帧图生视频：

```bash
python scripts/seedance_video.py create \
  --prompt "The character slowly turns toward the camera, subtle smile, soft lighting" \
  --first-frame-url "https://example.com/start.png" \
  --ratio adaptive \
  --duration 5 \
  --poll \
  --output ./outputs/i2v.mp4
```

首尾帧图生视频：

```bash
python scripts/seedance_video.py create \
  --prompt "Smooth transformation from sketch to final product, clean commercial style" \
  --first-frame-url "https://example.com/start.jpg" \
  --last-frame-url "https://example.com/end.jpg" \
  --ratio 16:9 \
  --duration 5 \
  --poll \
  --output ./outputs/transition.mp4
```

查询已有任务并下载：

```bash
python scripts/seedance_video.py get cgt-xxxx --output ./outputs/result.mp4
```

取消或删除任务：

```bash
python scripts/seedance_video.py cancel cgt-xxxx
```

## 常用参数

- `--base-url`：默认 `https://ark.cn-beijing.volces.com/api/v3`。
- `--model`：模型 ID、内置别名或 Ark Endpoint ID。
- `--ratio`：`adaptive`、`16:9`、`9:16`、`1:1`、`4:3`、`3:4`、`21:9`。
- `--resolution`：常见为 `480p`、`720p`、`1080p`，实际取决于模型支持。
- `--duration`：视频秒数，实际取决于模型支持。
- `--generate-audio` / `--no-generate-audio`：按需控制是否生成音频。
- `--watermark` / `--no-watermark`：默认发送 `false`。
- `--extra-json`：合并高级顶层字段。
- `--content-json`：完全自定义 Ark API 的 `content` 数组。

## 默认模型

脚本默认使用：

```text
doubao-seedance-2-0-fast-260128
```

也可以用别名：

```bash
python scripts/seedance_video.py create \
  --model seedance-2.0 \
  --prompt "A premium product launch video" \
  --ratio 16:9 \
  --duration 5 \
  --poll \
  --output ./outputs/final.mp4
```

模型 ID 会变化，生产环境请以火山方舟控制台和官方文档为准。

## 费用与安全建议

- 首次调用先用 `--dry-run` 检查请求。
- 长视频、1080p、有声视频、批量生成都可能产生更高费用。
- 不要在 README、脚本、issue、聊天记录中粘贴真实 API Key。
- 如果遇到权限、余额、配额、模型未开通错误，先检查方舟控制台里的模型开通、账户余额、资源包和 API Key 权限。
