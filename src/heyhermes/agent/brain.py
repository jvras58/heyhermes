"""O cérebro do agente: LLM + loop de tool-calling.

Três backends, escolhidos via BACKEND no .env:
  - ollama  -> LLM local via Ollama com as tools deste projeto (padrão)
  - openai  -> qualquer endpoint OpenAI-compatível com as tools deste projeto
  - hermes  -> hermes-agent da NousResearch via Docker (API OpenAI-compatível
               do gateway; as tools, memória e skills rodam do lado dele)
"""

import logging

from heyhermes.agent.tools import TOOL_SCHEMAS, execute_tool
from heyhermes.core.config import Settings

log = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5


class _OllamaBackend:
    def __init__(self, settings: Settings) -> None:
        import ollama

        self.settings = settings
        self.client = ollama.Client(host=settings.ollama_host)

    def chat(self, messages: list[dict]) -> str:
        s = self.settings
        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.chat(model=s.ollama_model, messages=messages, tools=TOOL_SCHEMAS)
            msg = response["message"]
            tool_calls = msg.get("tool_calls") or []
            messages.append(dict(msg))
            if not tool_calls:
                return msg.get("content", "") or ""
            for call in tool_calls:
                fn = call["function"]
                result = execute_tool(s, fn["name"], fn.get("arguments"))
                messages.append({"role": "tool", "name": fn["name"], "content": result})
        return "Desculpe, não consegui concluir a ação."


class _OpenAIBackend:
    def __init__(self, settings: Settings) -> None:
        from openai import OpenAI

        self.settings = settings
        self.client = OpenAI(base_url=settings.openai_base_url, api_key=settings.openai_api_key)

    def chat(self, messages: list[dict]) -> str:
        s = self.settings
        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.chat.completions.create(
                model=s.openai_model, messages=messages, tools=TOOL_SCHEMAS
            )
            msg = response.choices[0].message
            messages.append(msg.model_dump(exclude_none=True))
            if not msg.tool_calls:
                return msg.content or ""
            for call in msg.tool_calls:
                result = execute_tool(s, call.function.name, call.function.arguments)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
        return "Desculpe, não consegui concluir a ação."


class _HermesBackend:
    """hermes-agent (github.com/NousResearch/hermes-agent) via gateway Docker.

    O gateway expõe uma API OpenAI-compatível em /v1/chat/completions com o
    modelo "hermes-agent". O agente completo roda do lado do servidor — com as
    próprias tools (terminal, arquivos, web, memória, skills) — então aqui não
    enviamos tools: só o texto do usuário.
    """

    def __init__(self, settings: Settings) -> None:
        from openai import OpenAI

        self.settings = settings
        self.client = OpenAI(
            base_url=settings.hermes_base_url,
            api_key=settings.hermes_api_key,
            timeout=settings.hermes_timeout,
        )

    def chat(self, messages: list[dict]) -> str:
        response = self.client.chat.completions.create(
            model=self.settings.hermes_model,
            messages=messages,
        )
        return response.choices[0].message.content or ""


class Brain:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if settings.backend == "ollama":
            self.backend = _OllamaBackend(settings)
        elif settings.backend == "openai":
            self.backend = _OpenAIBackend(settings)
        else:
            self.backend = _HermesBackend(settings)
        self.history: list[dict] = []

    def ask(self, text: str) -> str:
        s = self.settings
        self.history.append({"role": "user", "content": text})
        # mantém só as últimas N mensagens para não estourar o contexto
        self.history = self.history[-s.max_history :]
        messages = [{"role": "system", "content": s.system_prompt}, *self.history]
        try:
            answer = self.backend.chat(messages)
        except Exception as exc:
            log.exception("Erro no backend %s", s.backend)
            return f"Tive um problema ao pensar na resposta: {exc}"
        # messages foi mutado pelo backend com tool calls; guarda só a resposta final
        self.history.append({"role": "assistant", "content": answer})
        return answer

    def reset(self) -> None:
        self.history.clear()
