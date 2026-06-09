# Official Volcengine Ark Seedance API Notes

Sources checked on 2026-06-05:

- Volcengine Ark API reference index: https://www.volcengine.com/docs/82379/1520757
- Create video generation task API: https://www.volcengine.com/docs/82379/1393047
- Query video generation task API: https://www.volcengine.com/docs/82379/1521309
- Seedance SDK/tutorial page: https://www.volcengine.com/docs/82379/1366799
- Ark API Key setup: https://www.volcengine.com/docs/82379/1541594
- Ark Base URL/auth: https://www.volcengine.com/docs/82379/1298459

## Endpoint And Auth

Base URL:

```text
https://ark.cn-beijing.volces.com/api/v3
```

Create task:

```http
POST /contents/generations/tasks
Authorization: Bearer $ARK_API_KEY
Content-Type: application/json
```

Query task:

```http
GET /contents/generations/tasks/{task_id}
Authorization: Bearer $ARK_API_KEY
```

The official SDK examples use:

```python
from volcenginesdkarkruntime import Ark

client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=os.environ.get("ARK_API_KEY"),
)

task = client.content_generation.tasks.create(...)
result = client.content_generation.tasks.get(task_id=task.id)
```

The bundled script uses the same REST contract with Python stdlib instead of requiring the SDK.

## Request Shape

Minimal text-to-video:

```json
{
  "model": "doubao-seedance-2-0-260128",
  "content": [
    {
      "type": "text",
      "text": "A cinematic product video, camera slowly pushes in"
    }
  ],
  "ratio": "16:9",
  "duration": 5,
  "watermark": false
}
```

Image input item:

```json
{
  "type": "image_url",
  "image_url": {
    "url": "https://example.com/start.jpg"
  },
  "role": "first_frame"
}
```

Common image roles:

- `first_frame`: use the image as the opening frame.
- `last_frame`: use the image as the closing frame.
- `reference_image`: use the image as a visual reference.

For first/last-frame control, do not mix `reference_image` items in the same task unless the current official docs explicitly permit that combination.

## Common Top-Level Parameters

- `model`: model ID or Ark endpoint name.
- `content`: array of text/image/video/audio content items.
- `ratio`: `adaptive`, `16:9`, `4:3`, `1:1`, `3:4`, `9:16`, `21:9`.
- `resolution`: `480p`, `720p`, `1080p`, model dependent.
- `duration`: seconds, model dependent.
- `frames`: optional frame count, model dependent.
- `framespersecond`: commonly `24`.
- `seed`: optional integer for repeatability.
- `camerafixed`: optional boolean.
- `watermark`: optional boolean.
- `generate_audio`: optional boolean, model dependent.

## Response Shape

Create returns a task object or at least an `id` field. Query returns fields similar to:

```json
{
  "id": "cgt-...",
  "model": "doubao-seedance-...",
  "status": "succeeded",
  "content": {
    "video_url": "https://..."
  },
  "error": null
}
```

Statuses to handle:

- `queued` / `running`: continue polling.
- `succeeded`: use `content.video_url`.
- `failed`: inspect `error.code` and `error.message`.
- `cancelled` / `expired`: stop and report status.

## Model Defaults

The script defaults to `doubao-seedance-2-0-fast-260128` for iteration speed. Use `--model doubao-seedance-2-0-260128` for quality-oriented final output, or pass any current official model ID/Ark endpoint name.

Model names change over time. Prefer checking the current Volcengine Ark model list before hardcoding a new production workflow.
