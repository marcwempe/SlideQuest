from __future__ import annotations

import queue
import tempfile
import threading
import time
import wave
from pathlib import Path
import os
from typing import Callable, NamedTuple

from PySide6.QtCore import QLocale, QObject, Signal

from huggingface_hub import snapshot_download
from tqdm.auto import tqdm

from slidequest.services.project_service import ProjectStorageService
from slidequest.utils.media import slugify

try:  # pragma: no cover - optional heavy deps
    import numpy as np
except Exception:  # pragma: no cover - best-effort fallback without deps
    np = None  # type: ignore[assignment]

try:  # pragma: no cover - optional heavy deps
    import sounddevice as sd
except Exception:  # pragma: no cover - best-effort fallback without deps
    sd = None  # type: ignore[assignment]

try:  # pragma: no cover - optional heavy deps
    from faster_whisper import WhisperModel
except Exception:  # pragma: no cover - best-effort fallback without deps
    WhisperModel = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    from pyannote.audio import Pipeline
except Exception:  # pragma: no cover
    Pipeline = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    import webrtcvad
except Exception:  # pragma: no cover
    webrtcvad = None  # type: ignore[assignment]

RECORDER_KIND = "recordings"


class RecordingResult(NamedTuple):
    slide_index: int
    audio_path: str
    transcript_path: str
    transcript_text: str
    duration_seconds: float


class LiveTranscriptionService(QObject):
    """Capture microphone audio and maintain rolling Whisper transcripts."""

    transcript_updated = Signal(int, str)
    recording_failed = Signal(str)
    recording_completed = Signal(object)

    def __init__(
        self,
        project_service: ProjectStorageService,
        *,
        model_name: str = "large-v3",
        sample_rate: int = 16_000,
        chunk_seconds: int = 5,
        min_chunk_seconds: float = 1.0,
        silence_threshold: float = 0.015,
        silence_trigger_seconds: float = 0.4,
        vad_aggressiveness: int = 2,
    ) -> None:
        super().__init__()
        self._project_service = project_service
        self._model_name = model_name
        self._sample_rate = sample_rate
        self._chunk_seconds = max(1, chunk_seconds)
        self._min_chunk_seconds = max(0.2, min_chunk_seconds)
        self._silence_threshold = max(0.0001, silence_threshold)
        self._silence_trigger_seconds = max(0.1, silence_trigger_seconds)
        self._vad: webrtcvad.Vad | None = None
        if webrtcvad is not None:
            level = max(0, min(3, int(vad_aggressiveness)))
            try:
                self._vad = webrtcvad.Vad(level)
            except Exception:
                self._vad = None
        self._channels = 1
        deps_ready = (
            np is not None
            and sd is not None
            and WhisperModel is not None
        )
        self._deps_ready = bool(deps_ready)
        self._model: WhisperModel | None = None
        self._stream: sd.InputStream | None = None
        self._transcription_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._frame_queue: queue.Queue | None = None
        self._write_lock = threading.Lock()
        self._wave_handle: wave.Wave_write | None = None
        self._session_dir: Path | None = None
        self._temp_audio_path: Path | None = None
        self._temp_transcript_path: Path | None = None
        self._transcript_segments: list[str] = []
        self._session_segments: list[tuple[float, float, str]] = []
        self._processed_duration = 0.0
        self._session_slide_index: int | None = None
        self._session_title: str = ""
        self._started_at: float | None = None
        self._language_hint = self._resolve_language_hint()
        self._active_compute_type: str | None = None
        self._last_model_error: str | None = None
        sanitized_name = model_name.replace("/", "-")
        self._model_slug = f"whisper-{sanitized_name}"
        self._model_dir = self._project_service.base_dir / "models" / self._model_slug
        self._model_repo_id = f"Systran/faster-whisper-{model_name}"
        if not self._has_local_model():
            legacy_dir = self._discover_existing_model_dir()
            if legacy_dir is not None:
                self._model_dir = legacy_dir
        self._stop_async_thread: threading.Thread | None = None
        self._diarization_pipeline: Pipeline | None = None
        self._diarization_token = os.environ.get("PYANNOTE_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    @property
    def is_available(self) -> bool:
        return self._deps_ready

    @property
    def is_recording(self) -> bool:
        return self._stream is not None

    @property
    def current_slide_index(self) -> int | None:
        return self._session_slide_index

    @property
    def requires_model_download(self) -> bool:
        return not self._has_local_model()

    def start(self, slide_index: int, slide_title: str, transcript_path: str | None = None) -> str | None:
        if not self._deps_ready or np is None or sd is None:
            raise RuntimeError(
                "Live-Transkription ist nicht verfügbar. "
                "Bitte installiere numpy, sounddevice und faster-whisper."
            )
        if self.requires_model_download:
            raise RuntimeError("Whisper-Modell ist noch nicht installiert.")
        if self.is_recording:
            self.stop()
        self._session_slide_index = slide_index
        self._session_title = slide_title or f"Folie-{slide_index + 1}"
        self._started_at = time.time()
        slug = slugify(self._session_title)
        self._session_dir = Path(tempfile.mkdtemp(prefix="slidequest-recording-"))
        self._temp_audio_path = self._session_dir / f"{slug}.wav"
        self._temp_transcript_path = Path(transcript_path) if transcript_path else self._session_dir / f"{slug}.md"
        self._transcript_segments = []
        self._session_segments = []
        self._processed_duration = 0.0
        self._frame_queue = queue.Queue()
        self._stop_event.clear()
        self._initialize_wave_file()
        self._write_transcript_header()
        self._start_stream()
        self._transcription_thread = threading.Thread(
            target=self._transcription_loop,
            daemon=True,
        )
        self._transcription_thread.start()
        return str(self._temp_transcript_path)

    def stop(self) -> RecordingResult | None:
        if not self.is_recording:
            return None
        self._stop_event.set()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
        self._stream = None
        if self._transcription_thread is not None:
            self._transcription_thread.join(timeout=15)
            self._transcription_thread = None
        with self._write_lock:
            if self._wave_handle is not None:
                try:
                    self._wave_handle.close()
                except Exception:
                    pass
            self._wave_handle = None
        result = self._persist_session()
        self._cleanup_session()
        return result

    def stop_async(self) -> None:
        if self._stop_async_thread and self._stop_async_thread.is_alive():
            return

        def worker() -> None:
            result = self.stop()
            self.recording_completed.emit(result)

        thread = threading.Thread(target=worker, daemon=True)
        self._stop_async_thread = thread
        thread.start()

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _start_stream(self) -> None:
        assert sd is not None and np is not None
        self._stream = sd.InputStream(  # type: ignore[call-arg]
            samplerate=self._sample_rate,
            channels=self._channels,
            dtype="float32",
            callback=self._handle_audio_chunk,
        )
        self._stream.start()

    def _initialize_wave_file(self) -> None:
        if self._temp_audio_path is None:
            return
        handle = wave.open(str(self._temp_audio_path), "wb")
        handle.setnchannels(self._channels)
        handle.setsampwidth(2)
        handle.setframerate(self._sample_rate)
        self._wave_handle = handle

    def _handle_audio_chunk(
        self,
        indata,
        _frames,
        _time,
        status,
    ) -> None:
        if np is None or self._frame_queue is None:
            return
        if status:
            # PortAudio may warn via status; skip noisy UI updates.
            pass
        chunk = np.copy(indata)
        self._frame_queue.put(chunk)
        self._write_frames(chunk)

    def _write_frames(self, chunk) -> None:
        if np is None or self._wave_handle is None:
            return
        pcm = self._float_to_pcm(chunk)
        with self._write_lock:
            try:
                self._wave_handle.writeframes(pcm)
            except Exception:
                self.recording_failed.emit(
                    "Aufnahme konnte nicht geschrieben werden."
                )
                self._stop_event.set()

    def _transcription_loop(self) -> None:
        frame_queue = self._frame_queue
        if np is None or frame_queue is None:
            return
        buffer = np.empty((0, self._channels), dtype="float32")
        silence_run = 0.0
        while not self._stop_event.is_set() or not frame_queue.empty():
            try:
                chunk = frame_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            buffer = np.concatenate((buffer, chunk))
            duration = len(buffer) / float(self._sample_rate)
            voice_active = self._detect_voice_activity(chunk)
            if voice_active is None:
                mono = chunk.mean(axis=1)
                energy = float(np.sqrt(np.mean(mono * mono))) if mono.size else 0.0
                silence_run = silence_run + len(chunk) / float(self._sample_rate) if energy < self._silence_threshold else 0.0
            else:
                silence_run = 0.0 if voice_active else silence_run + len(chunk) / float(self._sample_rate)
            should_flush = duration >= self._chunk_seconds
            if duration >= self._min_chunk_seconds and silence_run >= self._silence_trigger_seconds:
                should_flush = True
            if self._stop_event.is_set():
                should_flush = should_flush or duration > 0.5
            if should_flush:
                self._run_transcription(buffer)
                buffer = np.empty((0, self._channels), dtype="float32")
                silence_run = 0.0

    def _run_transcription(self, buffer) -> None:
        chunk_duration = len(buffer) / float(self._sample_rate)
        chunk_start = self._processed_duration
        self._processed_duration += chunk_duration
        if np is None or buffer.size == 0:
            return
        mono = buffer.mean(axis=1)
        temp_file: Path | None = None
        try:
            fd, tmp_path = tempfile.mkstemp(
                suffix=".wav",
                prefix="slidequest-chunk-",
            )
            os.close(fd)
            temp_file = Path(tmp_path)
            with wave.open(tmp_path, "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(self._sample_rate)
                mono_frame = mono.reshape(-1, 1)
                handle.writeframes(self._float_to_pcm(mono_frame))
            text, segments = self._transcribe_file(temp_file, chunk_start)
            if text:
                self._append_transcript_segment(text.strip())
                self._session_segments.extend(segments)
        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink(missing_ok=True)

    def _transcribe_file(self, path: Path, start_offset: float) -> tuple[str, list[tuple[float, float, str]]]:
        model = self._load_model()
        if model is None:
            self.recording_failed.emit(
                "Whisper-Modell konnte nicht geladen werden."
                + (
                    f"\n{self._last_model_error}"
                    if self._last_model_error
                    else ""
                )
            )
            self._stop_event.set()
            return "", []
        try:
            segments, _info = model.transcribe(
                str(path),
                beam_size=5,
                language=self._language_hint,
            )
        except Exception:
            return "", []
        text_parts: list[str] = []
        timed_segments: list[tuple[float, float, str]] = []
        for segment in segments:
            content = getattr(segment, "text", "").strip()
            if not content:
                continue
            start = float(getattr(segment, "start", 0.0)) + start_offset
            end = float(getattr(segment, "end", start))
            timed_segments.append((start, end, content))
            text_parts.append(content)
        full_text = " ".join(text_parts).strip()
        return full_text, timed_segments

    def _load_model(self):
        if self._model is not None or WhisperModel is None:
            return self._model
        source = self._model_source_path()
        errors: list[str] = []
        for compute_type in self._candidate_compute_types():
            try:
                self._model = WhisperModel(
                    source,
                    device="auto",
                    compute_type=compute_type,
                )
                self._active_compute_type = compute_type
                self._last_model_error = None
                break
            except Exception as exc:  # pragma: no cover - runtime dependent
                errors.append(f"{compute_type}: {exc}")
                self._model = None
        if self._model is None:
            self._last_model_error = "\n".join(errors) if errors else "Unbekannter Initialisierungsfehler."
        return self._model

    def _append_transcript_segment(self, text: str) -> None:
        if not text:
            return
        self._transcript_segments.append(text)
        self._flush_transcript_file()
        if self._session_slide_index is not None:
            self.transcript_updated.emit(
                self._session_slide_index,
                self.transcript_text,
            )

    def _write_transcript_header(self) -> None:
        if self._temp_transcript_path is None:
            return
        if self._temp_transcript_path.exists():
            existing = self._temp_transcript_path.read_text(encoding="utf-8")
            if existing.strip():
                return
        title = self._session_title or "Unbenannte Folie"
        header = f"# Live-Transkript – {title}\n\n"
        self._temp_transcript_path.write_text(header, encoding="utf-8")

    def _flush_transcript_file(self) -> None:
        if self._temp_transcript_path is None:
            return
        content = "\n\n".join(self._transcript_segments).strip()
        title = self._session_title or "Unbenannte Folie"
        header = f"# Live-Transkript – {title}\n\n"
        body = f"{header}{content}\n" if content else header
        self._temp_transcript_path.write_text(body, encoding="utf-8")

    def _persist_session(self) -> RecordingResult | None:
        if (
            self._temp_audio_path is None
            or self._temp_transcript_path is None
            or self._session_slide_index is None
            or not self._temp_audio_path.exists()
            or not self._temp_transcript_path.exists()
        ):
            return None
        self._flush_transcript_file()
        try:
            audio_ref = self._project_service.import_file(
                RECORDER_KIND,
                str(self._temp_audio_path),
            )
            transcript_ref = self._resolve_or_import_transcript()
        finally:
            self._cleanup_temp_files()
        duration = 0.0
        if self._started_at is not None:
            duration = max(0.0, time.time() - self._started_at)
        diarized_text = self.transcript_text
        diarized_output = self._apply_diarization(audio_ref, transcript_ref)
        if diarized_output:
            diarized_text = diarized_output
        return RecordingResult(
            slide_index=self._session_slide_index,
            audio_path=audio_ref,
            transcript_path=transcript_ref,
            transcript_text=diarized_text,
            duration_seconds=duration,
        )

    def _cleanup_temp_files(self) -> None:
        if self._session_dir and self._session_dir.exists():
            for entry in self._session_dir.glob("*"):
                entry.unlink(missing_ok=True)
            self._session_dir.rmdir()

    def _cleanup_session(self) -> None:
        self._frame_queue = None
        self._stop_event.clear()
        self._session_dir = None
        self._temp_audio_path = None
        self._temp_transcript_path = None
        self._session_slide_index = None
        self._session_title = ""
        self._started_at = None
        self._transcript_segments = []
        self._session_segments = []
        self._processed_duration = 0.0

    def _float_to_pcm(self, chunk):
        if np is None:
            return b""
        data = np.clip(chunk, -1.0, 1.0)
        pcm = (data * 32767).astype("<i2")
        return pcm.tobytes()

    @property
    def transcript_text(self) -> str:
        return "\n\n".join(self._transcript_segments).strip()

    def _resolve_language_hint(self) -> str | None:
        locale = QLocale.system().language()
        language_map: dict[QLocale.Language, str] = {
            QLocale.Language.German: "de",
            QLocale.Language.English: "en",
        }
        return language_map.get(locale, None)

    def download_model(self, progress_callback: Callable[[int, int], None] | None = None) -> None:
        if not self._deps_ready:
            raise RuntimeError("Audio-Abhängigkeiten fehlen – Download nicht möglich.")
        if not self.requires_model_download:
            return
        self._model_dir.mkdir(parents=True, exist_ok=True)
        callback = progress_callback

        class _ProgressBar(tqdm):
            def __init__(self_inner, *args, **kwargs):
                kwargs.pop("leave", None)
                super().__init__(*args, leave=False, **kwargs)

            def update(self_inner, n=1):  # type: ignore[override]
                super().update(n)
                if callback and self_inner.total:
                    callback(int(self_inner.n), int(self_inner.total))

        snapshot_download(
            repo_id=self._model_repo_id,
            local_dir=str(self._model_dir),
            local_dir_use_symlinks=False,
            allow_patterns=("*.bin", "*.json", "*.txt", "*.model"),
            resume_download=True,
            tqdm_class=_ProgressBar if callback else None,
        )

    def _has_local_model(self) -> bool:
        if not self._model_dir.exists():
            return False
        return any(self._model_dir.glob("*.bin"))

    def _model_source_path(self) -> str:
        if self._model_dir.exists() and self._has_local_model():
            return str(self._model_dir)
        legacy = self._discover_existing_model_dir()
        if legacy is not None:
            self._model_dir = legacy
            return str(self._model_dir)
        return self._model_name

    def _discover_existing_model_dir(self) -> Path | None:
        suffix = Path("SlideQuest") / "models" / self._model_slug
        roots: list[Path] = []
        base = self._project_service.base_dir
        parent = base.parent
        if parent and parent.exists():
            roots.append(parent)
        grandparent = parent.parent if parent else None
        if grandparent and grandparent.exists():
            roots.append(grandparent)
        visited: set[Path] = set()
        for root in roots:
            try:
                children = list(root.iterdir())
            except OSError:
                continue
            for child in children:
                candidate = (child / suffix).resolve()
                if candidate in visited or candidate == self._model_dir:
                    continue
                visited.add(candidate)
                if candidate.exists() and any(candidate.glob("*.bin")):
                    return candidate
        return None

    @staticmethod
    def _candidate_compute_types() -> list[str]:
        return [
            "int8_float16",
            "int8_float32",
            "int8",
            "int16",
            "float16",
            "float32",
        ]

    def _detect_voice_activity(self, chunk) -> bool | None:
        if self._vad is None or np is None:
            return None
        mono = chunk.mean(axis=1)
        if mono.size <= 0:
            return False
        pcm = np.clip(mono, -1.0, 1.0)
        pcm_bytes = (pcm * 32767).astype("<i2").tobytes()
        frame_length = int(self._sample_rate * 0.02)  # 20 ms
        bytes_per_frame = frame_length * 2
        if len(pcm_bytes) < bytes_per_frame:
            pcm_bytes = pcm_bytes.ljust(bytes_per_frame, b"\0")
        speech_detected = False
        for start in range(0, len(pcm_bytes) - bytes_per_frame + 1, bytes_per_frame):
            frame = pcm_bytes[start : start + bytes_per_frame]
            try:
                if self._vad.is_speech(frame, self._sample_rate):
                    speech_detected = True
                    break
            except Exception:
                continue
        return speech_detected

    def _apply_diarization(self, audio_ref: str, transcript_ref: str) -> str | None:
        if Pipeline is None or not self._session_segments or not audio_ref:
            return None
        pipeline = self._load_diarization_pipeline()
        if pipeline is None:
            return None
        try:
            audio_path = str(self._project_service.resolve_asset_path(audio_ref))
            diarization = pipeline(audio_path)
        except Exception:
            return None
        speaker_segments: list[tuple[float, float, str]] = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker_segments.append((turn.start, turn.end, speaker))
        if not speaker_segments:
            return None
        speaker_labels = self._map_speakers_to_text(speaker_segments)
        body_lines = []
        for (_, _, text), speaker in zip(self._session_segments, speaker_labels):
            speaker_name = f"Sprecher {speaker}" if isinstance(speaker, int) else speaker
            body_lines.append(f"**{speaker_name}**: {text.strip()}")
        title = self._session_title or "Unbenannte Folie"
        final_text = "# Live-Transkript – {title}\n\n".format(title=title)
        final_text += "\n\n".join(body_lines).strip() + "\n"
        transcript_abs = self._project_service.resolve_asset_path(transcript_ref)
        transcript_abs.write_text(final_text, encoding="utf-8")
        return final_text

    def _load_diarization_pipeline(self) -> Pipeline | None:
        if self._diarization_pipeline is not None:
            return self._diarization_pipeline
        if Pipeline is None:
            return None
        token = self._diarization_token
        if not token:
            return None
        try:
            self._diarization_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=token)
        except Exception:
            self._diarization_pipeline = None
        return self._diarization_pipeline

    def _map_speakers_to_text(self, diar_segments: list[tuple[float, float, str]]) -> list[str | int]:
        labels: list[str | int] = []
        for start, end, text in self._session_segments:
            labels.append(self._dominant_speaker(start, end, diar_segments))
        return labels

    @staticmethod
    def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
        return max(0.0, min(a_end, b_end) - max(a_start, b_start))

    def _dominant_speaker(
        self,
        seg_start: float,
        seg_end: float,
        diar_segments: list[tuple[float, float, str]],
    ) -> str | int:
        overlaps: dict[str, float] = {}
        for d_start, d_end, speaker in diar_segments:
            ov = self._overlap(seg_start, seg_end, d_start, d_end)
            if ov <= 0:
                continue
            overlaps[speaker] = overlaps.get(speaker, 0.0) + ov
        if not overlaps:
            return "Unbekannt"
        speaker = max(overlaps.items(), key=lambda item: item[1])[0]
        return speaker

    def _resolve_or_import_transcript(self) -> str:
        assert self._temp_transcript_path is not None
        path = self._temp_transcript_path
        try:
            relative = path.relative_to(self._project_service.project_dir)
            return relative.as_posix()
        except ValueError:
            pass
        return self._project_service.import_file("notes", str(path))
