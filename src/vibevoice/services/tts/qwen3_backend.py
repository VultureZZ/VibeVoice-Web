"""
Qwen3-TTS backend using the official qwen-tts package.

Uses CustomVoice model for built-in speakers and Base model for voice cloning.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...config import config
from .base import SpeakerRef, TTSBackend
from .segments import TranscriptSegment

logger = logging.getLogger(__name__)

# Map our default voice names (Alice, Frank, etc.) to Qwen3 CustomVoice speaker names.
# Qwen3 1.7B CustomVoice speakers: Vivian, Serena, Uncle_Fu, Dylan, Eric, Ryan, Aiden, Ono_Anna, Sohee
QWEN3_DEFAULT_VOICE_MAPPING = {
    "Alice": "Vivian",
    "Frank": "Ryan",
    "Mary": "Serena",
    "Carter": "Aiden",
    "Maya": "Sohee",
}

# Map short language codes to Qwen3 language names
QWEN3_LANGUAGE_MAP = {
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "de": "German",
    "fr": "French",
    "ru": "Russian",
    "pt": "Portuguese",
    "es": "Spanish",
    "it": "Italian",
}


def _get_qwen3_language(lang: str) -> str:
    """Map short code (e.g. en) to Qwen3 language name (e.g. English)."""
    normalized = (lang or "en").strip().lower()
    return QWEN3_LANGUAGE_MAP.get(normalized, "English")


class Qwen3Backend(TTSBackend):
    """
    TTS backend using Qwen3-TTS (CustomVoice for built-in, Base for cloning).

    Lazy-loads CustomVoice and Base models on first use.
    Caches voice_clone_prompt per ref_audio_path for custom voices.
    """

    def __init__(
        self,
        custom_voice_model: Optional[str] = None,
        base_model: Optional[str] = None,
        device_map: Optional[str] = None,
        dtype: Optional[str] = None,
    ) -> None:
        self._custom_voice_model = (
            custom_voice_model or getattr(config, "QWEN_TTS_CUSTOM_VOICE_MODEL", None)
            or "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
        )
        self._base_model = (
            base_model or getattr(config, "QWEN_TTS_BASE_MODEL", None)
            or "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
        )
        self._voice_design_model = (
            getattr(config, "QWEN_TTS_VOICE_DESIGN_MODEL", None)
            or "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
        )
        self._device_map = device_map or getattr(config, "QWEN_TTS_DEVICE", "cuda:0")
        self._dtype_str = dtype or getattr(config, "QWEN_TTS_DTYPE", "bfloat16")
        self._custom_voice_model_instance: Any = None
        self._base_model_instance: Any = None
        self._voice_design_model_instance: Any = None
        self._clone_prompt_cache: Dict[str, Any] = {}

    def _model_kwargs(self):
        """Build common kwargs for from_pretrained (device, dtype, attn). Only use flash_attention_2 if installed."""
        import torch
        dtype = getattr(torch, self._dtype_str, torch.bfloat16)
        kwargs = {"device_map": self._device_map, "dtype": dtype}
        if self._dtype_str in ("float16", "bfloat16"):
            try:
                import flash_attn  # noqa: F401
                kwargs["attn_implementation"] = "flash_attention_2"
            except ImportError:
                logger.debug("flash_attn not installed; using default attention")
        return kwargs

    def _get_custom_voice_model(self):
        if self._custom_voice_model_instance is None:
            from qwen_tts import Qwen3TTSModel

            logger.info("Loading Qwen3-TTS CustomVoice model: %s", self._custom_voice_model)
            self._custom_voice_model_instance = Qwen3TTSModel.from_pretrained(
                self._custom_voice_model,
                **self._model_kwargs(),
            )
        return self._custom_voice_model_instance

    def _get_base_model(self):
        if self._base_model_instance is None:
            from qwen_tts import Qwen3TTSModel

            logger.info("Loading Qwen3-TTS Base model: %s", self._base_model)
            self._base_model_instance = Qwen3TTSModel.from_pretrained(
                self._base_model,
                **self._model_kwargs(),
            )
        return self._base_model_instance

    def _get_voice_design_model(self):
        if self._voice_design_model_instance is None:
            from qwen_tts import Qwen3TTSModel

            logger.info("Loading Qwen3-TTS VoiceDesign model: %s", self._voice_design_model)
            self._voice_design_model_instance = Qwen3TTSModel.from_pretrained(
                self._voice_design_model,
                **self._model_kwargs(),
            )
        return self._voice_design_model_instance

    def _get_or_create_clone_prompt(self, ref_audio_path: Path, ref_text: Optional[str]) -> Any:
        """Get cached voice_clone_prompt or create and cache it."""
        cache_key = str(ref_audio_path)
        if ref_text:
            cache_key += "|" + ref_text[:200]
        if cache_key in self._clone_prompt_cache:
            return self._clone_prompt_cache[cache_key]
        model = self._get_base_model()
        ref_audio = str(ref_audio_path) if ref_audio_path else None
        if not ref_audio or not Path(ref_audio).exists():
            raise FileNotFoundError(f"Reference audio not found: {ref_audio}")
        kwargs = {"ref_audio": ref_audio, "x_vector_only_mode": not ref_text}
        if ref_text:
            kwargs["ref_text"] = ref_text
        prompt = model.create_voice_clone_prompt(**kwargs)
        self._clone_prompt_cache[cache_key] = prompt
        return prompt

    def _generate_segment(
        self,
        text: str,
        speaker_ref: SpeakerRef,
        language: str,
    ) -> tuple:
        """Generate audio for one segment. Returns (wav_array, sample_rate)."""
        import numpy as np

        qwen_lang = _get_qwen3_language(language)
        if not text or not text.strip():
            return np.array([], dtype=np.float32), 24000

        instruct = (speaker_ref.instruct or "").strip() if getattr(speaker_ref, "instruct", None) else ""

        if getattr(speaker_ref, "use_voice_design", False) and getattr(
            speaker_ref, "voice_design_instructions", None
        ):
            model = self._get_voice_design_model()
            instructions = (speaker_ref.voice_design_instructions or "").strip()
            wavs, sr = model.generate_voice_design(
                text=text.strip(),
                language=qwen_lang,
                instructions=instructions,
            )
            return wavs[0], sr
        if speaker_ref.use_custom_voice:
            model = self._get_custom_voice_model()
            speaker_name = speaker_ref.speaker_id or "Ryan"
            wavs, sr = model.generate_custom_voice(
                text=text.strip(),
                language=qwen_lang,
                speaker=speaker_name,
                instruct=instruct,
            )
            return wavs[0], sr
        else:
            model = self._get_base_model()
            if speaker_ref.voice_clone_prompt is not None:
                prompt = speaker_ref.voice_clone_prompt
            elif speaker_ref.ref_audio_path and speaker_ref.ref_audio_path.exists():
                prompt = self._get_or_create_clone_prompt(
                    speaker_ref.ref_audio_path,
                    speaker_ref.ref_text,
                )
            else:
                raise ValueError(
                    "Custom voice segment requires ref_audio_path or voice_clone_prompt"
                )
            wavs, sr = model.generate_voice_clone(
                text=text.strip(),
                language=qwen_lang,
                voice_clone_prompt=prompt,
            )
            return wavs[0], sr

    def generate(
        self,
        segments: List[TranscriptSegment],
        speaker_refs: List[SpeakerRef],
        language: str,
        output_path: Path,
    ) -> Path:
        """Generate speech from segments and concatenate into one WAV."""
        import numpy as np
        import soundfile as sf

        if not segments:
            raise ValueError("No segments to generate")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        all_wavs: List[np.ndarray] = []
        sample_rate = 24000

        for seg in segments:
            if seg.speaker_index >= len(speaker_refs):
                raise ValueError(
                    f"Segment speaker_index {seg.speaker_index} out of range (have {len(speaker_refs)} speaker_refs)"
                )
            ref = speaker_refs[seg.speaker_index]
            wav, sr = self._generate_segment(seg.text, ref, language)
            if wav is not None and len(wav) > 0:
                if not all_wavs:
                    sample_rate = sr
                elif sr != sample_rate:
                    logger.warning("Segment sample rate %s != %s; using first segment sr", sr, sample_rate)
                all_wavs.append(wav.astype(np.float32))

        if not all_wavs:
            raise RuntimeError("No audio generated from segments")

        concatenated = np.concatenate(all_wavs)
        sf.write(str(output_path), concatenated, sample_rate)
        logger.info("Wrote Qwen3-TTS output: %s (%s samples, %s Hz)", output_path, len(concatenated), sample_rate)
        return output_path


def resolve_speaker_to_qwen3_ref(
    speaker_name: str,
    voice_manager: Any,
    clone_prompt_cache: Optional[Dict[str, Any]] = None,
) -> SpeakerRef:
    """
    Resolve a speaker name (from our API) to a SpeakerRef for Qwen3Backend.

    - If speaker is a default (Alice, Frank, etc.), map to Qwen3 CustomVoice speaker.
    - If speaker is a custom voice, return SpeakerRef with ref_audio_path and optional ref_text.
    """
    from .base import SpeakerRef

    normalized = voice_manager.normalize_voice_name(speaker_name)
    qwen_speaker = QWEN3_DEFAULT_VOICE_MAPPING.get(normalized)
    if qwen_speaker is not None:
        return SpeakerRef(use_custom_voice=True, speaker_id=qwen_speaker)

    voice_data = voice_manager.get_voice_by_name(normalized) or voice_manager.get_voice_by_name(speaker_name)
    if not voice_data:
        raise ValueError(f"Voice not found: {speaker_name}")

    voice_type = voice_data.get("type", "custom")

    if voice_type == "voice_design":
        profile = voice_data.get("profile") or {}
        instructions = profile.get("voice_design_prompt") or voice_data.get("voice_design_prompt") or ""
        if not (instructions and isinstance(instructions, str) and instructions.strip()):
            raise ValueError(f"VoiceDesign voice '{speaker_name}' has no voice_design_prompt")
        return SpeakerRef(
            use_custom_voice=False,
            use_voice_design=True,
            voice_design_instructions=instructions.strip(),
        )

    if voice_type != "custom":
        raise ValueError(f"Voice not found or not custom: {speaker_name}")

    voice_id = voice_data.get("id")
    if not voice_id:
        raise ValueError(f"Custom voice has no id: {speaker_name}")

    path = voice_manager.get_voice_path(voice_id)
    if path is None or not path.exists():
        raise ValueError(f"Voice file not found for: {speaker_name}")

    ref_text = None
    if voice_data and isinstance(voice_data.get("profile"), dict):
        profile = voice_data["profile"]
        if isinstance(profile.get("transcript"), str):
            ref_text = profile["transcript"]

    return SpeakerRef(
        use_custom_voice=False,
        ref_audio_path=path,
        ref_text=ref_text or None,
    )
