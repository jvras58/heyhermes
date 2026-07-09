"""Captura de microfone na taxa nativa do dispositivo, reamostrada para 16 kHz.

Alguns drivers (ex.: Intel Smart Sound) ignoram a taxa pedida e entregam a
nativa mesmo assim — o áudio chega "esticado" e fica ininteligível para o
Whisper e o openWakeWord. Abrir na taxa nativa e reamostrar por software
funciona em qualquer dispositivo.
"""

import logging

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly

from heyhermes.core.config import Settings

log = logging.getLogger(__name__)


class MicStream:
    """Context manager que entrega frames int16 já na taxa alvo (16 kHz).

    `frame_samples` é o tamanho do frame na taxa alvo (ex.: 1280 = 80 ms).
    """

    def __init__(self, settings: Settings, frame_samples: int) -> None:
        self.device = settings.input_device
        info = sd.query_devices(self.device, "input")
        self.native_rate = int(info["default_samplerate"])
        self.target_rate = settings.sample_rate
        self.gain = settings.input_gain
        self.frame_samples = frame_samples
        self.native_block = round(self.native_rate * frame_samples / self.target_rate)
        log.info(
            "Microfone '%s': %d Hz nativo -> %d Hz (ganho %.1fx)",
            info["name"],
            self.native_rate,
            self.target_rate,
            self.gain,
        )
        self._stream: sd.InputStream | None = None

    def __enter__(self) -> "MicStream":
        self._stream = sd.InputStream(
            device=self.device,
            samplerate=self.native_rate,
            channels=1,
            dtype="int16",
            blocksize=self.native_block,
        )
        self._stream.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        assert self._stream is not None
        self._stream.stop()
        self._stream.close()
        self._stream = None

    def read(self) -> np.ndarray:
        """Lê um frame e retorna int16 mono na taxa alvo."""
        assert self._stream is not None, "use MicStream dentro de um bloco with"
        frame, overflowed = self._stream.read(self.native_block)
        if overflowed:
            log.warning("Buffer do microfone estourou; frames podem ter sido perdidos.")
        audio = np.squeeze(frame).astype(np.float32)
        if self.native_rate != self.target_rate:
            audio = resample_poly(audio, self.target_rate, self.native_rate)
        if self.gain != 1.0:
            audio *= self.gain
        return np.clip(audio, -32768, 32767).astype(np.int16)
