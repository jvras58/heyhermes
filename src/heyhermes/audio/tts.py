"""Sintetização de voz com o Piper (100% local).

A reprodução é em streaming: cada chunk sintetizado vai direto para a saída de
áudio, então a fala começa antes de a frase inteira estar pronta.
"""

import logging

import sounddevice as sd
from piper import PiperVoice

from heyhermes.core.config import Settings

log = logging.getLogger(__name__)


class TextToSpeech:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        model_path = settings.piper_dir / f"{settings.piper_voice}.onnx"
        if not model_path.exists():
            raise FileNotFoundError(
                f"Voz do Piper não encontrada em {model_path}.\n"
                f"Baixe com:\n"
                f"  uv run python -m piper.download_voices {settings.piper_voice} "
                f'--data-dir "{settings.piper_dir}"'
            )
        log.info("Carregando voz Piper '%s'…", settings.piper_voice)
        self.voice = PiperVoice.load(str(model_path))

    def say(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        log.info("Falando: %r", text)
        with sd.RawOutputStream(
            samplerate=self.voice.config.sample_rate, channels=1, dtype="int16"
        ) as stream:
            for chunk in self.voice.synthesize(text):
                stream.write(chunk.audio_int16_bytes)

    def say_stream(self, text_generator) -> None:
        buffer = ""
        punctuation = (".", "!", "?", ",", "\n")

        with sd.RawOutputStream(
            samplerate=self.voice.config.sample_rate, channels=1, dtype="int16"
        ) as stream:
            for token in text_generator:
                buffer += token

                if any(buffer.endswith(symbol) for symbol in punctuation):
                    chunk_text = buffer.strip()
                    if chunk_text:
                        log.debug("Sintetizando chunk: %r", chunk_text)
                        for audio_chunk in self.voice.synthesize(chunk_text):
                            stream.write(audio_chunk.audio_int16_bytes)
                    buffer = ""

            if buffer.strip():
                for audio_chunk in self.voice.synthesize(buffer.strip()):
                    stream.write(audio_chunk.audio_int16_bytes)
