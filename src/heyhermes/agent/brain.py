"""O cérebro do agente: hermes-agent (NousResearch) via Docker.

O gateway do hermes expõe uma API OpenAI-compatível em /v1/chat/completions
com o modelo "hermes-agent". O agente completo roda do lado do servidor — com
as próprias tools (terminal, arquivos, web, memória, skills) — então daqui só
enviamos o texto do usuário e devolvemos a resposta para a voz.

Para trocar o modelo/provedor do LLM, configure o próprio hermes (ver README).
"""

import logging

from openai import OpenAI

from heyhermes.core.config import Settings

log = logging.getLogger(__name__)


class Brain:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OpenAI(
            base_url=settings.hermes_base_url,
            api_key=settings.hermes_api_key,
            timeout=settings.hermes_timeout,
        )
        self.history: list[dict] = []

    def ask(self, text: str) -> str:
        s = self.settings
        self.history.append({"role": "user", "content": text})
        self.history = self.history[-s.max_history :]
        messages = [{"role": "system", "content": s.system_prompt}, *self.history]
        try:
            response = self.client.chat.completions.create(model=s.hermes_model, messages=messages)
            answer = response.choices[0].message.content or ""
        except Exception as exc:
            log.exception("Erro ao consultar o hermes-agent")
            return f"Tive um problema ao pensar na resposta: {exc}"
        self.history.append({"role": "assistant", "content": answer})
        return answer

    def ask_stream(self, text: str):
        s = self.settings
        self.history.append({"role": "user", "content": text})
        self.history = self.history[-s.max_history :]
        messages = [{"role": "system", "content": s.system_prompt}, *self.history]

        full_answer = ""
        try:
            response = self.client.chat.completions.create(
                model=s.hermes_model,
                messages=messages,
                stream=True,
            )
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    full_answer += content
                    yield content
        except Exception as exc:
            log.exception("Erro ao consultar o hermes-agent")
            full_answer = f"Erro: {exc}"
            yield full_answer

        self.history.append({"role": "assistant", "content": full_answer})

    def reset(self) -> None:
        self.history.clear()
