# Estendendo o HeyHermes: prefira MCPs plugáveis

> **Princípio deste projeto:** para dar novas capacidades ao agente (banco,
> e-mail, calendário, APIs, casa inteligente…), **prefira plugar um servidor
> MCP no hermes** a escrever uma **tool direta** — um script que o agente roda
> no próprio terminal, com as credenciais no ambiente dele.

O acesso ao banco (ver [relatorios-e-navegador.md](relatorios-e-navegador.md))
começou como tool direta (`db_report.py` com o DSN no container do agente) e foi
**migrado para MCP** (DBHub). Este documento explica por quê e como repetir o
padrão — a ideia é que **outras pessoas adicionem ferramentas com 1–2 comandos**,
sem mexer no código do HeyHermes.

## Por que MCP em vez de tool direta

| | MCP plugável | Tool direta (script no terminal do agente) |
|---|---|---|
| **Credencial** | fica no servidor MCP; o agente nunca vê | fica no env do agente; exposta ao shell |
| **Adicionar** | `hermes mcp add …` (sem tocar no código) | escrever script + montar + instruir o prompt |
| **Escopo/segurança** | modos read-only/restrito prontos | você mesmo implementa a trava |
| **Reuso** | centenas de MCPs prontos, protocolo padrão | específico do projeto |
| **Ligar/desligar** | por servidor e por tool, no hermes | tudo ou nada |

Ou seja: MCP isola o segredo, é padrão, e **qualquer um pluga mais ferramentas
sem dificuldade**.

## O padrão em 3 passos

**1. Suba o servidor MCP.** Duas formas:

- **Container próprio** (melhor isolamento) — adicione um serviço no
  [`compose.yml`](../compose.yml), atrás de um `profile`, com o segredo no env.
  Foi o que fizemos com o `db-mcp` (DBHub).
- **stdio local** — o hermes sobe o processo:
  ```powershell
  docker compose exec hermes hermes mcp add nome --command uvx --args pacote-mcp --env CHAVE=valor
  ```

**2. Registre no hermes** (HTTP/Streamable):

```powershell
docker compose exec hermes hermes mcp add <nome> --url http://<servico>:<porta>/mcp
```

Ou pegue um **pronto do catálogo aprovado** pela Nous:

```powershell
docker compose exec hermes hermes mcp catalog        # lista
docker compose exec hermes hermes mcp install <nome> # um clique
docker compose exec hermes hermes mcp list           # confere
```

> As tools novas entram **no início de uma sessão** — comece uma conversa nova
> depois de registrar.

**3. (Opcional) Mostrar algo na tela.** Se a ferramenta gera um artefato para o
usuário ver, reuse a ponte de host: grave em `/reports` e emita
`[[ABRIR_RELATORIO arquivo.html]]`, ou abra um site com `[[ABRIR_SITE url]]`.
Ver [`agent/actions.py`](../src/heyhermes/agent/actions.py).

## Requisito de transporte (importante)

O cliente MCP do hermes fala **Streamable HTTP** (endpoint `/mcp`). Servidores
que só expõem **SSE legado** respondem **405 Method Not Allowed** e não
conectam. Ao escolher um MCP por HTTP, garanta `--transport http` (ou
equivalente). Transporte **stdio** também funciona (o hermes sobe o processo).

## Quando uma tool direta ainda faz sentido

Nem tudo vira MCP. Mantenha como script simples quando for:

- **Ação local do host** que precisa rodar fora do container — ex.: abrir o
  navegador do Windows (a ponte `[[ABRIR_...]]` + `HostActions`). Um MCP no
  container não alcançaria sua tela.
- **Utilitário puro, sem segredo e sem serviço externo** — ex.: o
  [`render_report.py`](../hermes-tools/render_report.py), que só formata dados em
  HTML e **não acessa nada sensível**.

**Regra prática:** se envolve credencial, serviço externo ou "conectar em algo",
prefira MCP. Se é formatação/utilitário local sem segredo, um script serve.

## Onde achar MCPs

- Catálogo aprovado: `hermes mcp catalog` / `hermes mcp install <nome>`
- [awesome-hermes-agent](https://github.com/0xNyk/awesome-hermes-agent)
- Registries públicos de MCP (Postgres, GitHub, Slack, Notion, Google, etc.)

## Checklist para contribuir uma ferramenta

- [ ] Existe um MCP pronto para isso? Prefira ele.
- [ ] O segredo fica no servidor MCP (env), nunca no prompt nem no HeyHermes.
- [ ] Usa modo read-only/restrito quando faz sentido.
- [ ] Transporte Streamable HTTP (`/mcp`) ou stdio.
- [ ] Documentou o `hermes mcp add` e, se for container, o serviço + `profile`
      no `compose.yml`.
- [ ] Se mostra algo na tela do usuário, reusou `/reports` + diretivas `[[…]]`.
