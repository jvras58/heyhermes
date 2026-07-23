# Relatórios do banco + abrir o navegador por voz

Este guia liga o HeyHermes a um banco de dados e deixa o agente:

- **Gerar relatórios** a partir do que você pedir por voz — ele consulta o
  banco por um canal **somente-leitura e isolado**, monta um HTML bonito
  (tabela + gráfico) e **abre na sua tela**.
- **Abrir sites** no seu navegador quando você pedir.

```
você fala → agente usa tools MCP read-only (DBHub) → recebe as linhas
          → render_report.py monta /reports/nome.html → heyhermes abre no seu navegador
          → e fala um resumo com o Piper
```

## Por que MCP (e não o banco direto no agente)

A senha do banco **não fica** com o agente. Quem fala com o banco é um serviço
dedicado, o **DBHub** (`bytebase/dbhub`), rodando no container `db-mcp`:

- **A credencial vive só no `db-mcp`.** O agente nunca vê o DSN nem a senha.
- **`execute_sql` é somente-leitura** (configurado em
  [`dbhub.toml`](../hermes-tools/dbhub/dbhub.toml)) — o agente não altera dados.
- O agente recebe só **duas ferramentas MCP**: `search_objects` (procurar
  tabelas/colunas) e `execute_sql` (rodar um SELECT).
- O [`render_report.py`](../hermes-tools/render_report.py), que roda do lado do
  agente, **não tem acesso a banco nenhum** — só transforma linhas (JSON) em HTML.

O hermes tem cliente MCP nativo e fala **Streamable HTTP**; o DBHub expõe
exatamente isso em `http://db-mcp:8080/mcp` (na rede interna do compose, sem
porta publicada).

## A ponte container ↔ Windows (abrir na tela)

As tools do hermes rodam dentro do container, então para **mostrar algo na sua
tela** o agente emite diretivas no texto, que o heyhermes executa no host:

| Peça | Onde | O quê |
|---|---|---|
| `db-mcp` (DBHub) | container | acesso read-only ao banco; guarda o DSN |
| `./hermes-tools` → `/hermes-tools` | mount (ro) | o [`render_report.py`](../hermes-tools/render_report.py) |
| `./reports` → `/reports` | mount | o HTML gerado aparece no host |
| `[[ABRIR_RELATORIO x.html]]` / `[[ABRIR_SITE url]]` | texto | o heyhermes remove da fala e abre no Windows |

Ver [`agent/actions.py`](../src/heyhermes/agent/actions.py).

## Setup

### Opção A — banco de exemplo (testar sem ter um banco)

Sobe uma mini-loja Postgres (`clientes` / `produtos` / `vendas`) já semeada.

**1.** No `.env` da raiz:

```env
HEYHERMES_PG_DSN=postgres://hermes:hermes@demo-db:5432/loja?sslmode=disable
```

**2.** Suba a stack demo (banco + DBHub + hermes):

```powershell
docker compose --profile demo up -d
```

**3.** Registre o servidor MCP no hermes (uma única vez). Responda **n** para
autenticação e **Enter** para habilitar as tools:

```powershell
docker compose exec hermes hermes mcp add banco --url http://db-mcp:8080/mcp
```

Pronto. Rode `uv run heyhermes` e peça, por voz:

- *"Me mostra o faturamento por categoria."*
- *"Quais os cinco clientes que mais compraram?"*

O demo é efêmero (sem volume): `docker compose --profile demo down` + `up`
recarrega o seed de [`hermes-tools/demo/seed.sql`](../hermes-tools/demo/seed.sql).

### Opção B — seu banco

**1.** No `.env` (banco no seu Windows usa `host.docker.internal`):

```env
HEYHERMES_PG_DSN=postgres://usuario:senha@host.docker.internal:5432/meubanco
```

**2.** Suba com o profile `db` e registre o MCP (só na 1ª vez):

```powershell
docker compose --profile db up -d
docker compose exec hermes hermes mcp add banco --url http://db-mcp:8080/mcp
```

O registro (`banco`) fica salvo no hermes; nas próximas vezes basta o
`docker compose --profile db up -d`.

> **Postgres no Windows aceitando o Docker:** `listen_addresses = '*'` no
> `postgresql.conf` e uma linha no `pg_hba.conf` liberando a faixa do Docker
> (ex.: `host all all 172.16.0.0/12 scram-sha-256`). Reinicie o Postgres.

## Trocando de banco

O DBHub é **multi-banco**, então trocar de engine é **só trocar o DSN** — nada
de mexer em código:

| Banco | `HEYHERMES_PG_DSN` |
|---|---|
| **PostgreSQL** | `postgres://usuario:senha@host.docker.internal:5432/banco` |
| **MySQL / MariaDB** | `mysql://usuario:senha@host.docker.internal:3306/banco` |
| **SQL Server** | `sqlserver://usuario:senha@host.docker.internal:1433/banco` |
| **SQLite** | `sqlite:///opt/data/meu.db` (monte o arquivo no `db-mcp`) |

Depois de mudar o DSN: `docker compose --profile db up -d` (recria o `db-mcp`).
O registro MCP no hermes continua valendo (mesmo endereço `db-mcp:8080`).

## Como usar (por voz)

Diga a wake word, espere o "Sim?" e peça:

- *"Me mostra o total de vendas por categoria neste mês."* → o agente procura as
  tabelas (`search_objects`), roda o SELECT (`execute_sql`), gera o relatório,
  **abre na sua tela** e fala: *"As vendas somaram X, com eletrônicos na frente."*
- *"Abre o site da Nous Research."* → abre no seu navegador.

Não precisa saber SQL nem os nomes das tabelas — quem descobre é o agente.

## Segurança

- **Credencial isolada:** a senha do banco vive só no `db-mcp`; o agente nunca a
  vê. `execute_sql` roda **somente-leitura** ([`dbhub.toml`](../hermes-tools/dbhub/dbhub.toml)).
- **Defesa em profundidade (recomendado):** conecte com um **usuário de banco
  só-leitura** e/ou aponte para uma **réplica de leitura** — assim, mesmo com
  qualquer furo, a produção não corre risco.
- **Rede:** o DBHub **não autentica clientes HTTP**, por isso ele fica só na
  rede interna do compose (sem porta publicada) e com `--allowed-hosts db-mcp`.
- **Abrir na tela:** o heyhermes só abre arquivos de `./reports` (bloqueia path
  traversal) e URLs `http(s)`. Desligue com `ENABLE_HOST_ACTIONS=false` ou só as
  URLs com `ALLOW_OPEN_URL=false`.

## Problemas comuns

**O agente diz que não tem a ferramenta do banco** — confira
`docker compose exec hermes hermes mcp list` (deve mostrar `banco ✓ enabled`).
Se o `db-mcp` estiver fora, suba: `docker compose --profile db up -d`. Depois de
registrar, **comece uma sessão nova** (as tools entram no início da sessão).

**O `db-mcp` não conecta no banco** — veja `docker logs heyhermes-db-mcp`. Quase
sempre é o DSN: use o esquema `postgres://` (não `postgresql://`),
`host.docker.internal` para banco no Windows, e `?sslmode=disable` se o banco não
usa SSL.

**O relatório não abre na tela** — veja o log do heyhermes: se aparecer
`Abrindo relatório no navegador`, a ponte funcionou. Se o agente não emitiu
`[[ABRIR_RELATORIO ...]]`, o modelo é fraco para o protocolo — use um
provedor/modelo mais forte (README, "Trocando o modelo"). Modelos 7B costumam se
atrapalhar orquestrando várias tools MCP + o render.
