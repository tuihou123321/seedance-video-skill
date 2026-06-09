#!/usr/bin/env python3
"""Create, poll, and download Seedance videos through Volcengine Ark."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "doubao-seedance-2-0-fast-260128"
API_KEY_ENV_ORDER = ("ARK_API_KEY", "SEEDANCE_API_KEY", "VOLCENGINE_API_KEY", "VOLC_API_KEY")

KNOWN_MODELS = {
    "seedance-2.0": "doubao-seedance-2-0-260128",
    "seedance-2.0-fast": "doubao-seedance-2-0-fast-260128",
    "seedance-1.5-pro": "doubao-seedance-1-5-pro-251215",
    "seedance-1.0-pro": "doubao-seedance-1-0-pro-250528",
    "seedance-1.0-lite-t2v": "doubao-seedance-1-0-lite-t2v-250428",
    "seedance-1.0-lite-i2v": "doubao-seedance-1-0-lite-i2v-250428",
}

TERMINAL_STATUSES = {"succeeded", "failed", "cancelled", "expired"}


class SeedanceError(RuntimeError):
    pass


def eprint(*values: Any) -> None:
    print(*values, file=sys.stderr)


def load_env_file(path: str | None) -> None:
    if not path:
        return
    env_path = Path(path).expanduser()
    if not env_path.exists():
        raise SeedanceError(f"Env file not found: {env_path}")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_api_key(env_name: str | None) -> str:
    if env_name:
        value = os.environ.get(env_name)
        if value:
            return value
        raise SeedanceError(f"Missing API key environment variable: {env_name}")
    for key in API_KEY_ENV_ORDER:
        value = os.environ.get(key)
        if value:
            return value
    expected = ", ".join(API_KEY_ENV_ORDER)
    raise SeedanceError(f"Missing API key. Set one of: {expected}")


def normalize_model(model: str | None) -> str:
    raw = model or os.environ.get("SEEDANCE_MODEL") or DEFAULT_MODEL
    return KNOWN_MODELS.get(raw, raw)


def parse_json_arg(value: str, label: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise SeedanceError(f"Invalid JSON for {label}: {exc}") from exc


def request_json(
    method: str,
    url: str,
    api_key: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
    retries: int = 3,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code in {429, 500, 502, 503, 504} and attempt < retries:
                time.sleep(min(2**attempt, 8))
                continue
            raise SeedanceError(f"HTTP {exc.code} from Ark API: {body}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(2**attempt, 8))
                continue
            break
    raise SeedanceError(f"Ark API request failed: {last_error}") from last_error


def build_content(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.content_json:
        content = parse_json_arg(args.content_json, "--content-json")
        if not isinstance(content, list):
            raise SeedanceError("--content-json must be a JSON array")
        return content

    if not args.prompt:
        raise SeedanceError("--prompt is required unless --content-json is provided")

    content: list[dict[str, Any]] = [{"type": "text", "text": args.prompt}]

    def add_image(url: str, role: str) -> None:
        content.append({"type": "image_url", "image_url": {"url": url}, "role": role})

    if args.first_frame_url:
        add_image(args.first_frame_url, "first_frame")
    if args.last_frame_url:
        add_image(args.last_frame_url, "last_frame")
    for url in args.reference_image_url or []:
        add_image(url, "reference_image")
    for url in args.reference_video_url or []:
        content.append({"type": "video_url", "video_url": {"url": url}, "role": "reference_video"})
    for url in args.reference_audio_url or []:
        content.append({"type": "audio_url", "audio_url": {"url": url}, "role": "reference_audio"})
    return content


def create_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": normalize_model(args.model),
        "content": build_content(args),
    }

    optional_fields = {
        "ratio": args.ratio,
        "resolution": args.resolution,
        "duration": args.duration,
        "frames": args.frames,
        "framespersecond": args.framespersecond,
        "seed": args.seed,
        "camerafixed": args.camerafixed,
        "watermark": args.watermark,
        "generate_audio": args.generate_audio,
    }
    for key, value in optional_fields.items():
        if value is not None:
            payload[key] = value

    if args.extra_json:
        extra = parse_json_arg(args.extra_json, "--extra-json")
        if not isinstance(extra, dict):
            raise SeedanceError("--extra-json must be a JSON object")
        payload.update(extra)

    return payload


def extract_task_id(result: dict[str, Any]) -> str:
    task_id = result.get("id") or result.get("task_id")
    if not task_id and isinstance(result.get("data"), dict):
        task_id = result["data"].get("id") or result["data"].get("task_id")
    if not task_id:
        raise SeedanceError(f"Could not find task id in response: {json.dumps(result, ensure_ascii=False)}")
    return str(task_id)


def extract_video_url(result: dict[str, Any]) -> str | None:
    content = result.get("content")
    if isinstance(content, dict) and content.get("video_url"):
        return str(content["video_url"])
    data = result.get("data")
    if isinstance(data, dict):
        data_content = data.get("content")
        if isinstance(data_content, dict) and data_content.get("video_url"):
            return str(data_content["video_url"])
    return None


def task_status(result: dict[str, Any]) -> str | None:
    status = result.get("status")
    if not status and isinstance(result.get("data"), dict):
        status = result["data"].get("status")
    return str(status) if status else None


def get_task(base_url: str, api_key: str, task_id: str, timeout: int) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/contents/generations/tasks/{task_id}"
    return request_json("GET", url, api_key=api_key, timeout=timeout)


def poll_task(args: argparse.Namespace, api_key: str, task_id: str) -> dict[str, Any]:
    deadline = time.time() + args.poll_timeout
    while True:
        result = get_task(args.base_url, api_key, task_id, args.http_timeout)
        status = task_status(result) or "unknown"
        eprint(f"task {task_id}: {status}")
        if status in TERMINAL_STATUSES:
            return result
        if time.time() >= deadline:
            raise SeedanceError(f"Polling timed out after {args.poll_timeout}s. Resume with: get {task_id}")
        time.sleep(args.poll_interval)


def download_url(url: str, output: str, timeout: int = 300) -> Path:
    output_path = Path(output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "seedance-video-skill/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            output_path.write_bytes(response.read())
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SeedanceError(f"Download failed: {exc}") from exc
    return output_path


def cmd_create(args: argparse.Namespace) -> int:
    load_env_file(args.env_file)
    payload = create_payload(args)
    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    api_key = get_api_key(args.api_key_env)
    url = f"{args.base_url.rstrip('/')}/contents/generations/tasks"
    result = request_json("POST", url, api_key=api_key, payload=payload, timeout=args.http_timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    task_id = extract_task_id(result)
    if args.poll:
        result = poll_task(args, api_key, task_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    video_url = extract_video_url(result)
    if args.output:
        if not video_url:
            raise SeedanceError(f"No video_url available yet. Query later with: get {task_id}")
        path = download_url(video_url, args.output)
        eprint(f"downloaded: {path}")
    elif video_url:
        eprint(f"video_url: {video_url}")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    load_env_file(args.env_file)
    api_key = get_api_key(args.api_key_env)
    result = get_task(args.base_url, api_key, args.task_id, args.http_timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    video_url = extract_video_url(result)
    if args.output:
        if not video_url:
            raise SeedanceError("No content.video_url in task result")
        path = download_url(video_url, args.output)
        eprint(f"downloaded: {path}")
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    load_env_file(args.env_file)
    api_key = get_api_key(args.api_key_env)
    url = f"{args.base_url.rstrip('/')}/contents/generations/tasks/{args.task_id}"
    result = request_json("DELETE", url, api_key=api_key, timeout=args.http_timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_models(_: argparse.Namespace) -> int:
    print(json.dumps({"default": DEFAULT_MODEL, "aliases": KNOWN_MODELS}, ensure_ascii=False, indent=2))
    return 0


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=os.environ.get("SEEDANCE_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key-env", default=None, help="Read API key from this environment variable only")
    parser.add_argument("--env-file", default=None, help="Optional local .env file to load before reading API key")
    parser.add_argument("--http-timeout", type=int, default=60)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Volcengine Ark Seedance video generation helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a Seedance video generation task")
    add_common_args(create)
    create.add_argument("--prompt", default=None)
    create.add_argument("--content-json", default=None, help="Exact JSON array for the Ark content field")
    create.add_argument("--extra-json", default=None, help="Extra top-level JSON object merged into request")
    create.add_argument("--model", default=None, help="Model ID, alias, or Ark endpoint name")
    create.add_argument("--ratio", default=None)
    create.add_argument("--resolution", default=None)
    create.add_argument("--duration", type=int, default=None)
    create.add_argument("--frames", type=int, default=None)
    create.add_argument("--framespersecond", type=int, default=None)
    create.add_argument("--seed", type=int, default=None)
    create.add_argument("--camerafixed", action="store_true", default=None)
    create.add_argument("--watermark", dest="watermark", action="store_true", default=False)
    create.add_argument("--no-watermark", dest="watermark", action="store_false")
    audio = create.add_mutually_exclusive_group()
    audio.add_argument("--generate-audio", dest="generate_audio", action="store_true")
    audio.add_argument("--no-generate-audio", dest="generate_audio", action="store_false")
    create.set_defaults(generate_audio=None)
    create.add_argument("--first-frame-url", default=None)
    create.add_argument("--last-frame-url", default=None)
    create.add_argument("--reference-image-url", action="append", default=[])
    create.add_argument("--reference-video-url", action="append", default=[])
    create.add_argument("--reference-audio-url", action="append", default=[])
    create.add_argument("--poll", action="store_true")
    create.add_argument("--poll-interval", type=int, default=15)
    create.add_argument("--poll-timeout", type=int, default=1800)
    create.add_argument("--output", default=None)
    create.add_argument("--dry-run", action="store_true")
    create.set_defaults(func=cmd_create)

    get = subparsers.add_parser("get", help="Query a Seedance task")
    add_common_args(get)
    get.add_argument("task_id")
    get.add_argument("--output", default=None)
    get.set_defaults(func=cmd_get)

    cancel = subparsers.add_parser("cancel", help="Cancel/delete a Seedance task")
    add_common_args(cancel)
    cancel.add_argument("task_id")
    cancel.set_defaults(func=cmd_cancel)

    models = subparsers.add_parser("models", help="List built-in model aliases")
    models.set_defaults(func=cmd_models)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except SeedanceError as exc:
        eprint(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
