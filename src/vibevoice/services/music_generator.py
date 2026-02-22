"""
Music generation orchestration service for ACE-Step integration.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from ..config import config
from .music_process import music_process_manager
from .ollama_client import ollama_client

logger = logging.getLogger(__name__)


class MusicGenerator:
    """Orchestrates ACE-Step task submission, polling, and local file storage."""

    def __init__(self) -> None:
        self._task_cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _base_url(host: str, port: int) -> str:
        return f"http://{host}:{port}"

    @staticmethod
    def _unwrap_response(payload: dict[str, Any]) -> Any:
        code = payload.get("code")
        if code != 200:
            raise RuntimeError(payload.get("error") or f"ACE-Step API error (code={code})")
        return payload.get("data")

    @staticmethod
    def _normalize_status(raw_status: int) -> str:
        if raw_status == 1:
            return "succeeded"
        if raw_status == 2:
            return "failed"
        return "running"

    async def _acestep_post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        cfg = music_process_manager.ensure_running()
        music_process_manager.touch_activity()
        url = f"{self._base_url(cfg.host, cfg.port)}{path}"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload)
        music_process_manager.touch_activity()
        response.raise_for_status()
        return response.json()

    async def _acestep_get_bytes(self, path_or_url: str) -> bytes:
        cfg = music_process_manager.ensure_running()
        music_process_manager.touch_activity()
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            url = path_or_url
        else:
            url = f"{self._base_url(cfg.host, cfg.port)}{path_or_url}"
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.get(url)
        music_process_manager.touch_activity()
        response.raise_for_status()
        return response.content

    @staticmethod
    def _extract_extension(file_url: str, fallback: str = "mp3") -> str:
        parsed = urlparse(file_url)
        query_path = parse_qs(parsed.query).get("path", [""])[0]
        if query_path:
            suffix = Path(unquote(query_path)).suffix
            if suffix:
                return suffix.lstrip(".")
        suffix = Path(parsed.path).suffix
        if suffix:
            return suffix.lstrip(".")
        return fallback

    @staticmethod
    def _parse_result_payload(raw_result: Any) -> list[dict[str, Any]]:
        if isinstance(raw_result, list):
            return [x for x in raw_result if isinstance(x, dict)]
        if isinstance(raw_result, dict):
            return [raw_result]
        if isinstance(raw_result, str):
            text = raw_result.strip()
            if not text:
                return []
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                return []
            if isinstance(parsed, list):
                return [x for x in parsed if isinstance(x, dict)]
            if isinstance(parsed, dict):
                return [parsed]
        return []

    def _cache_task_result(self, task_id: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._task_cache[task_id] = payload

    def _get_cached_task_result(self, task_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            return self._task_cache.get(task_id)

    async def _download_and_store(
        self,
        task_id: str,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        out_dir = config.MUSIC_OUTPUT_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

        stored: list[dict[str, Any]] = []
        for idx, item in enumerate(items, 1):
            file_url = item.get("file")
            if not isinstance(file_url, str) or not file_url:
                continue

            ext = self._extract_extension(file_url, fallback="mp3")
            filename = f"music_{task_id}_{idx}.{ext}"
            out_path = out_dir / filename

            content = await self._acestep_get_bytes(file_url)
            out_path.write_bytes(content)
            stored.append(
                {
                    "filename": filename,
                    "audio_url": f"/api/v1/music/download/{filename}",
                    "file_path": str(out_path),
                    "seed_value": item.get("seed_value"),
                    "prompt": item.get("prompt"),
                    "lyrics": item.get("lyrics"),
                    "metas": item.get("metas") or {},
                    "dit_model": item.get("dit_model"),
                    "lm_model": item.get("lm_model"),
                }
            )
        return stored

    async def generate_music(self, params: dict[str, Any]) -> str:
        payload = await self._acestep_post("/release_task", params)
        data = self._unwrap_response(payload)
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected ACE-Step response format for task submission")
        task_id = data.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise RuntimeError("ACE-Step did not return a task_id")
        return task_id

    async def create_sample(
        self,
        query: str,
        instrumental: bool,
        vocal_language: Optional[str] = None,
        duration: Optional[float] = None,
        batch_size: int = 1,
    ) -> str:
        # NOTE:
        # ACE-Step's sample_mode can strongly rewrite user intent (e.g., language/duration drift).
        # For AudioMesh "Simple Mode", we keep intent constrained by using normal generation
        # with LM-assisted refinement and explicit user constraints.
        enriched_query = query.strip()
        if not instrumental:
            lang = (vocal_language or "en").strip().lower()
            enriched_query = (
                f"{enriched_query}. Keep vocals and lyrics in {lang}. "
                "Do not switch language."
            )
        if duration and duration > 0:
            enriched_query = (
                f"{enriched_query} Target duration: {int(duration)} seconds."
            )

        payload: dict[str, Any] = {
            "prompt": enriched_query,
            "thinking": True,
            "batch_size": max(1, min(batch_size, 4)),
            "instrumental": instrumental,
            "use_cot_caption": True,
            # When caller explicitly provides language/duration, do not let CoT rewrite those.
            "use_cot_language": False if (vocal_language and not instrumental) else True,
            "use_cot_metas": False if (duration and duration > 0) else True,
        }
        if vocal_language and not instrumental:
            payload["vocal_language"] = vocal_language
        if not instrumental:
            # Provide minimal structured lyrics to strongly bias toward vocal generation.
            # Without lyrics, ACE-Step may still produce instrumental tracks in simple mode.
            payload["lyrics"] = (
                "[Verse 1]\n"
                f"{query.strip()}\n"
                "[Chorus]\n"
                "Rowing with my homies, we keep moving with the flow.\n"
                "[Verse 2]\n"
                "On the river with the crew, we grind and let it show.\n"
                "[Chorus]\n"
                "Rowing with my homies, we keep moving with the flow."
            )
            payload["use_format"] = True
        if duration and duration > 0:
            payload["duration"] = duration

        return await self.generate_music(payload)

    async def get_status(self, task_id: str) -> dict[str, Any]:
        payload = await self._acestep_post("/query_result", {"task_id_list": [task_id]})
        data = self._unwrap_response(payload)
        if not isinstance(data, list) or not data:
            raise RuntimeError("ACE-Step returned an empty status response")
        task_data = data[0] if isinstance(data[0], dict) else {}
        raw_status = int(task_data.get("status", 0))
        status = self._normalize_status(raw_status)

        if status != "succeeded":
            return {
                "task_id": task_id,
                "status": status,
                "audios": [],
                "metadata": [],
                "error": task_data.get("error"),
            }

        cached = self._get_cached_task_result(task_id)
        if cached is not None:
            return cached

        raw_result = task_data.get("result")
        parsed_items = self._parse_result_payload(raw_result)
        local_items = await self._download_and_store(task_id, parsed_items)
        result = {
            "task_id": task_id,
            "status": "succeeded",
            "audios": [item["audio_url"] for item in local_items],
            "metadata": local_items,
            "error": None,
        }
        self._cache_task_result(task_id, result)
        return result

    async def generate_lyrics(
        self,
        description: str,
        genre: str,
        mood: str,
        language: str,
        duration_hint: Optional[str] = None,
    ) -> dict[str, str]:
        prompt = (
            "You are a songwriting assistant for a music generation app.\n"
            "Generate lyrics only and an optional style caption.\n\n"
            f"Description: {description}\n"
            f"Genre: {genre}\n"
            f"Mood: {mood}\n"
            f"Language: {language}\n"
            f"Duration hint: {duration_hint or 'auto'}\n\n"
            "Output format strictly:\n"
            "Caption: <short production/style tags for model prompt>\n"
            "Lyrics:\n"
            "[Verse 1]\n"
            "... lyrics ...\n"
            "[Chorus]\n"
            "... lyrics ...\n"
            "[Verse 2]\n"
            "... lyrics ...\n"
            "[Bridge]\n"
            "... lyrics ...\n"
            "[Chorus]\n"
            "... lyrics ...\n\n"
            "Do not include explanations."
        )

        response = ollama_client.client.post(
            f"{ollama_client.base_url}/api/generate",
            json={
                "model": ollama_client.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.8, "top_p": 0.9},
            },
        )
        response.raise_for_status()
        body = response.json().get("response", "").strip()
        if not body:
            raise RuntimeError("Lyrics generation returned an empty response")

        caption = ""
        lyrics = body
        lines = body.splitlines()
        if lines and lines[0].lower().startswith("caption:"):
            caption = lines[0].split(":", 1)[1].strip()
            remaining = "\n".join(lines[1:]).strip()
            if remaining.lower().startswith("lyrics:"):
                remaining = remaining.split(":", 1)[1].strip()
            lyrics = remaining.strip() or lyrics

        return {"caption": caption, "lyrics": lyrics}

    def health(self) -> dict[str, Any]:
        probe = music_process_manager.check_health_if_running()
        return {
            "available": bool(config.ACESTEP_REPO_DIR.exists()),
            "running": probe is not None,
            "service": "acestep",
            "host": config.ACESTEP_HOST,
            "port": config.ACESTEP_PORT,
        }


music_generator = MusicGenerator()
