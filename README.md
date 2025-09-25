# Limpador de Mídia do WhatsApp (Termux)

Este repositório contém uma ferramenta em Python para Termux que analisa e ajuda a limpar mídias antigas do WhatsApp em:

`/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media`

Resumo das funcionalidades
- Análise por idade com relatório (modo simulação / dry-run por padrão).
- Política de retenção por idade configurável (padrões: manter até X dias, mover entre Y–Z dias para Trash, excluir acima de Z dias com confirmação forte).
- Movimentação para uma Lixeira timestamped (pasta `whatsapp_clean_trash_YYYYMMDD_HHMMSS`).
- Exclusões permanentes somente após confirmação explícita (digitar `YES`).
- Geração de logs JSON com `entries` e `meta` para permitir restauração.
- Pré-visualização de restauração: lista entradas recuperáveis a partir de um log antes de executar a restauração.
- Filtragem por pasta/extension mapping (detecta pastas tipo "WhatsApp Images", "WhatsApp Video" etc. usando correspondência por substring) e fallback para uma whitelist global de extensões.

Requisitos
- Python 3.10 ou superior (o script usa anotações e sintaxe modernas). Verifique com:

```powershell
python3 --version
```

Ambiente Termux (pré-requisitos)
1. Abra o Termux.
2. Conceda permissão de armazenamento (necessário para acessar `/storage`):

```powershell
termux-setup-storage
```

3. Instale o Python (se necessário):

```powershell
pkg install python
```

Instalação do repositório
- Copie o repositório para o diretório home do Termux (via `git clone`, `termux-share` ou `adb`).

Como usar (fluxo básico)
1. Executar em modo análise (dry-run, recomendado):

```powershell
python3 scripts/clean_whatsapp.py
```

- O menu interativo permitirá:
	- Analisar e gerar relatório (sem alterações quando em dry-run).
	- Ver estatísticas por faixa de idade e maiores arquivos.
	- Escolher aplicar movimentações (mover arquivos entre Y–Z dias para Trash) e/ou exclusões (> Z dias) — os prompts mostram os valores atuais de configuração.
	- Pré-visualizar restaurações a partir de logs antes de aplicar.

2. Restauração a partir de log (menu):
- A opção de restauração agora lista logs disponíveis em `~/.local/share/whatsapp_clean/logs/`, permite pré-visualizar quais entradas são restauráveis e executa a restauração somente após confirmação.

Arquivos de configuração e logs
- Configuração persistente: `~/.config/whatsapp_clean/config.json` (valores como `age_keep_days`, `age_trash_min`, `age_trash_max`, `include_private`, `include_sent`, `auto_prune`).
- Logs: `~/.local/share/whatsapp_clean/logs/` (arquivos JSON gerados por operações que moveram/excluíram itens).

Política de segurança e comportamento seguro
- Por padrão o script roda em dry-run: nada será movido/excluído até que o usuário confirme.
- Exclusões permanentes exigem confirmação forte (digitar `YES`).
- A varredura ignora nomes sensíveis (ex.: `.nomedia`) e arquivos sem extensão reconhecida.
- A restauração só é possível para arquivos que foram movidos para a Lixeira (ou que ainda existam no `planned_dst`); deletes permanentes não são recuperáveis.

Detecção de pastas e extensões
- O script usa `EXTENSION_MAP` para mapear tipos de pasta para extensões permitidas (ex.: `images` → `jpg`, `png`, `webp`).
- A detecção de pasta faz correspondência por substring nas partes do caminho (por exemplo, "WhatsApp Images" corresponde a `images`).
- Se a pasta não for reconhecida, o script usa uma whitelist global (`GLOBAL_MEDIA_EXTS`).

Boas práticas antes de executar
- Sempre rode a análise (dry-run) primeiro e revise o relatório.
- Faça backup de arquivos importantes antes de aplicar exclusões.
- Em dispositivos com Android 11+ o acesso a certos caminhos pode ser restrito mesmo após `termux-setup-storage`.

Comandos úteis
- Verificar versão do Python:

```powershell
python3 --version
```

- Conceder permissão em Termux:

```powershell
termux-setup-storage
```

- Checar sintaxe do script (opcional):

```powershell
python3 -m py_compile scripts/clean_whatsapp.py
```

- Executar o script (modo interativo):

```powershell
python3 scripts/clean_whatsapp.py
```

Melhorias e próximos passos
- Adicionar testes automatizados (pequeno harness que simula uma árvore de pastas do WhatsApp e valida `scan_files` / `perform_actions` em dry-run).
- Registrar checksums nos logs para validação de integridade durante restauração (opcional).
- Adicionar uma opção "safe-verbose" que liste arquivos ignorados e motivos antes da aplicação.

Contato / contribuições
- Pull requests e issues são bem-vindos. Para contribuições, siga as práticas padrão de git (branch por recurso, commits pequenos).

## Licença

Este projeto é distribuído sob a **Licença MIT** - um software livre e de código aberto que permite uso, modificação e distribuição sem restrições. Você pode usar este código para qualquer finalidade, inclusive comercial, desde que mantenha os créditos originais. O software é fornecido "como está", sem garantias de qualquer tipo.

**Autor:** Daniel Ito Isaia
