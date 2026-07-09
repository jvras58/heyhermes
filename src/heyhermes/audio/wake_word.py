"""Loop de escuta da wake word com openWakeWord.

Usa o modelo pré-treinado "hey_jarvis" por padrão. Para "hey hermes" é preciso
treinar um modelo customizado (notebook oficial do openWakeWord) e apontar o
caminho do .onnx em WAKE_WORDS no .env.
"""

import logging
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from openwakeword.model import Model

from heyhermes.core.config import Settings

log = logging.getLogger(__name__)

# openWakeWord trabalha com frames de 80 ms a 16 kHz
FRAME_SAMPLES = 1280


def _ensure_pretrained_models(names: list[str]) -> None:
    """Baixa os modelos pré-treinados do openWakeWord na primeira execução."""
    pretrained = [n for n in names if not n.endswith(".onnx")]
    if not pretrained:
        return
    try:
        from openwakeword.utils import download_models

        download_models()
    except Exception as exc:  # sem internet, mas os modelos podem já existir
        log.warning("Não foi possível baixar modelos do openWakeWord: %s", exc)


class WakeWordListener:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        _ensure_pretrained_models(settings.wake_words)

        models: list[str] = []
        for name in settings.wake_words:
            if name.endswith(".onnx"):
                path = Path(name)
                if not path.is_absolute():
                    path = Path.cwd() / path
                if not path.exists():
                    raise FileNotFoundError(f"Modelo de wake word não encontrado: {path}")
                models.append(str(path))
            else:
                models.append(name)

        self.model = Model(wakeword_models=models, inference_framework="onnx")

    def listen(self) -> str:
        """Bloqueia até detectar uma wake word e retorna o nome dela."""
        s = self.settings
        self.model.reset()
        with sd.InputStream(
            samplerate=s.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=FRAME_SAMPLES,
        ) as stream:
            while True:
                frame, _overflowed = stream.read(FRAME_SAMPLES)
                self.model.predict(np.squeeze(frame))
                for name, buffer in self.model.prediction_buffer.items():
                    if buffer and buffer[-1] >= s.wake_threshold:
                        log.info("Wake word detectada: %s (%.2f)", name, buffer[-1])
                        self.model.reset()
                        return name

    def cooldown(self) -> None:
        time.sleep(self.settings.wake_cooldown)
