"""Gravação do comando de voz e transcrição com Faster-Whisper."""

import logging

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from heyhermes.core.config import Settings

log = logging.getLogger(__name__)

FRAME_MS = 30  # janela usada na detecção de silêncio


class SpeechToText:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        log.info("Carregando Whisper '%s' (%s)…", settings.whisper_model, settings.whisper_device)
        self.model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )

    def record_command(self) -> np.ndarray:
        """Grava até o usuário parar de falar (detecção de silêncio por energia RMS).

        Retorna o áudio como float32 normalizado, pronto para o Whisper.
        """
        s = self.settings
        frame_samples = int(s.sample_rate * FRAME_MS / 1000)
        max_frames = int(s.max_command_seconds * 1000 / FRAME_MS)
        silence_frames_limit = int(s.silence_seconds * 1000 / FRAME_MS)

        frames: list[np.ndarray] = []
        silence_frames = 0
        started_talking = False

        with sd.InputStream(
            samplerate=s.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=frame_samples,
        ) as stream:
            for _ in range(max_frames):
                frame, _ = stream.read(frame_samples)
                frame = np.squeeze(frame)
                frames.append(frame)

                rms = float(np.sqrt(np.mean(frame.astype(np.float64) ** 2)))
                if rms >= s.silence_threshold:
                    started_talking = True
                    silence_frames = 0
                elif started_talking:
                    silence_frames += 1
                    if silence_frames >= silence_frames_limit:
                        break

        audio = np.concatenate(frames) if frames else np.zeros(0, dtype=np.int16)
        return audio.astype(np.float32) / 32768.0

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""
        segments, _info = self.model.transcribe(
            audio,
            language=self.settings.language,
            beam_size=5,
            vad_filter=True,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        log.info("Transcrição: %r", text)
        return text

    def listen_command(self) -> str:
        return self.transcribe(self.record_command())
