---
name: seedance-video
description: Generate, query, and download AI videos with ByteDance Doubao Seedance models through the official Volcengine Ark API using an API Key. Use when the user mentions Seedance, doubao-seedance, Volcengine Ark video generation, 火山引擎视频生成, 方舟视频生成 API, 文生视频, 图生视频, 首帧/尾帧生成视频, reference image/video/audio video generation, or asks to create scripts/workflows that call Seedance with ARK_API_KEY.
---

# Seedance Video

Use the official Volcengine Ark video generation API for Seedance tasks. The skill never stores credentials; read the key from environment variables.

## Quick Start

Require an Ark API Key:

```bash
export ARK_API_KEY="your-volcengine-ark-api-key"
```

Generate and download a text-to-video result:

```bash
python scripts/seedance_video.py create \
  --prompt "A close-up cinematic shot of a coffee cup on a rainy window, steam rising slowly" \
  --ratio 9:16 \
  --duration 5 \
  --poll \
  --output ./outputs/seedance.mp4
```

Generate from a first-frame image URL:

```bash
python scripts/seedance_video.py create \
  --prompt "The character slowly turns toward the camera, subtle smile, soft lighting" \
  --first-frame-url "https://example.com/start.png" \
  --ratio adaptive \
  --duration 5 \
  --poll \
  --output ./outputs/i2v.mp4
```

Query an existing task:

```bash
python scripts/seedance_video.py get cgt-xxxx --output ./outputs/result.mp4
```

## Workflow

1. Check `ARK_API_KEY`; fall back to `SEEDANCE_API_KEY`, `VOLCENGINE_API_KEY`, or `VOLC_API_KEY` only when `ARK_API_KEY` is absent.
2. Pick a model. Default to `SEEDANCE_MODEL` when set, otherwise use `doubao-seedance-2-0-fast-260128`. Pass `--model` for another official model or endpoint name.
3. Build `content`:
   - Text-to-video: one `{"type":"text","text":"..."}` item.
   - First-frame image-to-video: add an `image_url` item with `role: "first_frame"`.
   - First/last-frame image-to-video: add `first_frame` and `last_frame` image items.
   - Reference mode: add one or more `reference_image`, `reference_video`, or `reference_audio` items.
4. Create the task with `POST /contents/generations/tasks`.
5. Poll with `GET /contents/generations/tasks/{task_id}` until `succeeded` or `failed`.
6. When status is `succeeded`, download `content.video_url` if the user asked for a local file.

## Script

Use `scripts/seedance_video.py` for deterministic API calls:

```bash
# Show supported defaults and examples.
python scripts/seedance_video.py models

# Print request JSON without calling the API.
python scripts/seedance_video.py create \
  --prompt "A product reveal shot" \
  --dry-run

# Use explicit first and last frames.
python scripts/seedance_video.py create \
  --prompt "Smooth transformation from sketch to final product" \
  --first-frame-url "https://example.com/start.jpg" \
  --last-frame-url "https://example.com/end.jpg" \
  --poll \
  --output ./outputs/transition.mp4
```

Important flags:

- `--base-url`: default `https://ark.cn-beijing.volces.com/api/v3`.
- `--model`: model ID or Ark endpoint name.
- `--ratio`: `adaptive`, `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, or `21:9`.
- `--resolution`: commonly `480p`, `720p`, or `1080p`; support depends on the model.
- `--duration`: seconds; support depends on the model.
- `--generate-audio` / `--no-generate-audio`: include only when user explicitly wants audio control.
- `--watermark` / `--no-watermark`: default sends `false`.
- `--extra-json`: merge advanced top-level request fields.
- `--content-json`: override the generated `content` array with exact JSON.

## Cost And Safety

- Confirm before generating expensive batches, long videos, 1080p videos, or audio-heavy runs.
- Do not paste, save, or commit API Keys. Use environment variables or a local shell session.
- Prefer `--dry-run` before the first paid call.
- If the API returns access, balance, quota, or model-not-enabled errors, ask the user to check Ark console model access and account balance.

## References

Read `references/official-api.md` when implementing new parameters, debugging payloads, or checking the latest official endpoint notes.
