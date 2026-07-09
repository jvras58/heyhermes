"""Loop principal: wake word -> gravação -> transcrição -> agente -> voz."""

import logging
import sys

# console do Windows usa cp1252 por padrão; respostas do LLM podem ter unicode
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from heyhermes.agent.brain import Brain
from heyhermes.audio.stt import SpeechToText
from heyhermes.audio.tts import TextToSpeech
from heyhermes.audio.wake_word import WakeWordListener
from heyhermes.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
log = logging.getLogger("heyhermes")


def _matches(text: str, phrases: list[str]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def main() -> None:
    log.info("Inicializando HeyHermes (backend: %s)…", settings.backend)
    tts = TextToSpeech(settings)
    stt = SpeechToText(settings)
    wake = WakeWordListener(settings)
    brain = Brain(settings)

    tts.say("Hermes online.")
    log.info("Aguardando wake word (%s)…", ", ".join(settings.wake_words))

    try:
        while True:
            wake.listen()
            tts.say(settings.ack_phrase)

            command = stt.listen_command()
            if not command:
                tts.say("Não entendi nada, pode repetir?")
                wake.cooldown()
                continue

            # comandos pré-definidos (não passam pelo LLM)
            if _matches(command, settings.exit_commands):
                tts.say("Até logo!")
                break
            if _matches(command, settings.cancel_commands):
                wake.cooldown()
                continue

            answer = brain.ask(command)
            tts.say(answer or "Feito.")
            wake.cooldown()
    except KeyboardInterrupt:
        log.info("Encerrando…")


if __name__ == "__main__":
    main()
