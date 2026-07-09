"""As "mãos" do agente: tools locais no formato OpenAI/Ollama function-calling."""

import json
import logging
import subprocess
import webbrowser
from datetime import datetime

from heyhermes.core.config import Settings

log = logging.getLogger(__name__)


_DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
         "sexta-feira", "sábado", "domingo"]
_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
          "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _tool_get_current_datetime(settings: Settings, args: dict) -> str:
    now = datetime.now()
    return (
        f"Hoje é {_DIAS[now.weekday()]}, {now.day} de {_MESES[now.month - 1]} "
        f"de {now.year} e agora são {now:%H:%M}."
    )


def _tool_open_application(settings: Settings, args: dict) -> str:
    app = str(args.get("name", "")).strip()
    if not app:
        return "Erro: nome do aplicativo vazio."
    # 'start' resolve executáveis no PATH e apps registrados no Windows
    subprocess.Popen(f'start "" "{app}"', shell=True)
    return f"Aplicativo '{app}' aberto."


def _tool_open_website(settings: Settings, args: dict) -> str:
    url = str(args.get("url", "")).strip()
    if not url:
        return "Erro: URL vazia."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Site {url} aberto no navegador."


def _tool_run_powershell(settings: Settings, args: dict) -> str:
    if not settings.allow_shell:
        return "Execução de comandos está desabilitada (ALLOW_SHELL=false)."
    command = str(args.get("command", "")).strip()
    if not command:
        return "Erro: comando vazio."
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (result.stdout or result.stderr or "").strip()
        return output[:2000] or f"Comando finalizado com código {result.returncode}."
    except subprocess.TimeoutExpired:
        return "Erro: o comando excedeu o tempo limite de 30 segundos."


_HANDLERS = {
    "get_current_datetime": _tool_get_current_datetime,
    "open_application": _tool_open_application,
    "open_website": _tool_open_website,
    "run_powershell": _tool_run_powershell,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Retorna a data e a hora atuais.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Abre um aplicativo no computador do usuário (ex.: notepad, spotify, code).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Nome ou executável do aplicativo, ex.: 'notepad' ou 'spotify'.",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "Abre uma URL no navegador padrão do usuário.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL completa ou domínio, ex.: 'youtube.com'."}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_powershell",
            "description": (
                "Executa um comando PowerShell no computador do usuário e retorna a saída. "
                "Use apenas para pedidos explícitos de sistema (volume, arquivos, processos)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Comando PowerShell a executar."}
                },
                "required": ["command"],
            },
        },
    },
]


def execute_tool(settings: Settings, name: str, arguments: dict | str | None) -> str:
    """Executa uma tool pelo nome e retorna o resultado como texto."""
    handler = _HANDLERS.get(name)
    if handler is None:
        return f"Erro: tool desconhecida '{name}'."
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            return f"Erro: argumentos inválidos para '{name}'."
    try:
        result = handler(settings, arguments or {})
        log.info("Tool %s(%s) -> %r", name, arguments, result[:200])
        return result
    except Exception as exc:
        log.exception("Falha na tool %s", name)
        return f"Erro ao executar '{name}': {exc}"
