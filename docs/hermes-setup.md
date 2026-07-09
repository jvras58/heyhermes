# Guia: configurando o hermes-agent (Docker)

Passo a passo completo do cérebro do HeyHermes — o
[hermes-agent da NousResearch](https://github.com/NousResearch/hermes-agent)
rodando em container, com API OpenAI-compatível e dashboard web.

## Visão geral

```
uv run heyhermes ──HTTP──> localhost:8642 (API do hermes) ──> LLM (Ollama do host ou provedor)
navegador       ──HTTP──> localhost:9119 (dashboard web)
```

Tudo do hermes (config, chaves, sessões, memórias, skills) fica em
`./hermes-data/`, montado em `/opt/data` no container. Esse diretório está no
`.gitignore` — ele contém segredos.

## 1. Pré-requisitos

- **Docker Desktop** rodando
- **Ollama** no host com um modelo puxado (`ollama pull qwen2.5:7b`) — ou uma
  chave de provedor (Nous Portal, OpenRouter, OpenAI…)

## 2. Chave da API (`HERMES_API_KEY`)

O heyhermes fala com o hermes por uma API autenticada. A chave vive no `.env`
da raiz e é usada **dos dois lados**: o compose injeta como `API_SERVER_KEY`
no container, e o heyhermes manda como `Authorization: Bearer`.

Ela é só uma string aleatória longa (mínimo 8 caracteres) — gere a sua:

```powershell
# PowerShell: 48 caracteres hexadecimais aleatórios
-join ((1..48) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
```

```bash
# Linux/macOS: mesmo resultado com openssl
openssl rand -hex 24
```

E coloque no `.env`:

```env
HERMES_API_KEY=cole-aqui-a-chave-gerada
```

> Não é uma chave de provedor/serviço externo — você mesmo a inventa, e ela só
> protege a API local. Se trocar, rode `docker compose up -d --force-recreate`
> para o container pegar o valor novo.

## 3. Subir o container

```powershell
docker compose up -d          # primeira vez baixa a imagem (~2 GB)
docker compose logs -f hermes # acompanhe até ver "Hermes Gateway Starting"
```

Teste rápido da API:

```powershell
$key = "sua-HERMES_API_KEY"
Invoke-RestMethod -Uri http://localhost:8642/v1/models -Headers @{Authorization="Bearer $key"}
# deve listar o modelo "hermes-agent"
```

```bash
# Linux/macOS (curl)
curl -H "Authorization: Bearer sua-HERMES_API_KEY" http://localhost:8642/v1/models
```

## 4. Modelo / provedor LLM

O hermes exige **mínimo de 64K tokens de contexto**. A config fica em
`hermes-data/config.yaml`.

### Opção A — Ollama local (padrão deste projeto)

```yaml
model:
  default: qwen2.5:7b                              # modelo do Ollama
  provider: custom
  base_url: http://host.docker.internal:11434/v1   # Ollama do host Windows
  context_length: 65536
  ollama_num_ctx: 65536
```

Após editar: `docker compose restart hermes`.

> Modelos 7B funcionam mas se atrapalham com o prompt agêntico do hermes
> (respostas confusas, tools ignoradas). Use o maior que sua máquina aguentar.

### Opção B — Provedor forte (recomendado)

O wizard interativo configura Nous Portal (OAuth), OpenRouter, OpenAI etc.:

```powershell
docker compose run --rm hermes model
docker compose restart hermes
```

Ou direto, sem wizard:

```powershell
docker compose run --rm hermes config set OPENROUTER_API_KEY sua-chave
```

## 5. Dashboard web

O dashboard (chat com o agente, sessões, memórias e skills) fica em
**http://localhost:9119/login** e **se recusa a subir sem autenticação**.
Usamos o provider de senha (`basic_auth`), que você configura assim:

**Passo 1 — escolha um usuário e uma senha.** O usuário é qualquer nome que
você queira usar no login (não precisa existir no Windows nem em lugar
nenhum). A senha, gere aleatória como na seção 2 ou invente uma forte.

**Passo 2 — gere o hash da senha** dentro do container (o hermes guarda só o
hash, nunca a senha em texto):

```powershell
docker exec -w /opt/hermes hermes /opt/hermes/.venv/bin/python -c `
  "from plugins.dashboard_auth.basic import hash_password; print(hash_password('SUA-SENHA'))"
```

**Passo 3 — registre em `hermes-data/config.yaml`** e reinicie:

```yaml
dashboard:
  basic_auth:
    username: seu-usuario        # o nome escolhido no passo 1
    password_hash: scrypt$...    # a saída do passo 2
```

```powershell
docker compose restart hermes
```

**Passo 4 (opcional) — anote a senha em texto no `.env`** para não esquecer
(o `.env` está no `.gitignore`, então não vaza pro git):

```env
HERMES_DASHBOARD_PASSWORD=sua-senha-em-texto
```

> Essa variável é só uma anotação sua — nem o container nem o heyhermes a
> leem; quem autentica de verdade é o hash do `config.yaml`.

> Se cair num erro 500 em `/auth/login`, use a URL `/login` direto — a rota
> com erro é o fluxo OAuth, que não se aplica ao login por senha.

Para **trocar a senha**, repita os passos 2 e 3 com a senha nova.

## 6. Comandos do dia a dia

| Ação | Comando |
|---|---|
| Ver logs | `docker compose logs -f hermes` |
| Reiniciar (após mudar config) | `docker compose restart hermes` |
| Atualizar o hermes | `docker compose pull; docker compose up -d` |
| Wizard completo de setup | `docker compose run --rm hermes setup` |
| Trocar modelo/provedor | `docker compose run --rm hermes model` |
| Setar config avulsa | `docker compose run --rm hermes config set CHAVE valor` |
| Diagnóstico | `docker compose run --rm hermes doctor` |

## 7. Problemas comuns

**"context window ... below the minimum 64,000"** — aumente
`context_length` e `ollama_num_ctx` para `65536` no `config.yaml` (seção 4A) e
reinicie.

**API retorna 401** — a `HERMES_API_KEY` do `.env` não bate com a do
container. Rode `docker compose up -d --force-recreate` para reinjetar.

**Hermes não alcança o Ollama** — dentro do container, `localhost` é o
próprio container; o host é `host.docker.internal`. Confirme também que o
Ollama está rodando (`ollama list`).

**Respostas misturando idiomas / ignorando tools** — limitação do modelo
pequeno; troque para um modelo maior ou provedor forte (seção 4B).

**Tools agem "no lugar errado"** — as tools do hermes (terminal, arquivos)
rodam **dentro do container**, não no Windows. Isso é proposital (sandbox).
