"""Fixtures reutilizáveis dos testes do HeyHermes.

Princípios:
- `Settings` de teste NÃO lê o `.env` do usuário (`_env_file=None`) e aponta
  `reports_dir` para um tmp isolado — testes determinísticos e sem tocar no
  ambiente real.
- `opened` captura o que iria pro navegador, então nenhum teste abre janelas.
- `render_report` importa o script de `hermes-tools/` (que vive fora do pacote).
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

from heyhermes.agent.actions import HostActions
from heyhermes.core.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def make_settings(tmp_path: Path) -> Callable[..., Settings]:
    """Factory de `Settings` isolada; aceita overrides por keyword.

    Ex.: `make_settings(enable_host_actions=False)`.
    """

    def _make(**overrides) -> Settings:
        defaults = {
            "reports_dir": tmp_path,
            "enable_host_actions": True,
            "allow_open_url": True,
        }
        return Settings(_env_file=None, **{**defaults, **overrides})

    return _make


@pytest.fixture
def settings(make_settings: Callable[..., Settings]) -> Settings:
    """Um `Settings` de teste com os padrões seguros (host actions ligadas)."""
    return make_settings()


@pytest.fixture
def host_actions(settings: Settings) -> HostActions:
    return HostActions(settings)


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Captura os alvos passados a `webbrowser.open` sem abrir nada."""
    calls: list[str] = []
    from heyhermes.agent import actions

    monkeypatch.setattr(actions.webbrowser, "open", calls.append)
    return calls


@pytest.fixture(scope="session")
def render_report() -> ModuleType:
    """Importa `hermes-tools/render_report.py` (fora do pacote heyhermes)."""
    path = REPO_ROOT / "hermes-tools" / "render_report.py"
    spec = importlib.util.spec_from_file_location("render_report", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
