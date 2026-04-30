# Limpador de mídia do WhatsApp para Termux

Este projeto é um app simples de terminal para Android/Termux que ajuda a liberar espaço removendo mídias antigas do WhatsApp com prévia, confirmação e possibilidade de restauração dos arquivos movidos para a lixeira.

Ele foi pensado para ser conservador:

- Mostra uma prévia antes de alterar qualquer arquivo.
- Usa perfis de limpeza fáceis de entender.
- Move arquivos antigos para uma lixeira antes de apagar definitivamente, quando configurado.
- Só apaga definitivamente após confirmação explícita digitando `APAGAR`.
- Gera registros para restaurar arquivos que foram movidos para a lixeira.

## Onde ele procura as mídias

O app tenta detectar automaticamente pastas comuns:

```text
/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media
/storage/emulated/0/Android/media/com.whatsapp.w4b/WhatsApp Business/Media
/storage/emulated/0/WhatsApp/Media
```

Se o seu celular usar outro caminho, você pode alterar isso pelo menu `Configurações`.

## Instalação no Termux

1. Instale o Termux.

2. Abra o Termux e conceda acesso ao armazenamento:

```bash
termux-setup-storage
```

3. Instale Python e Git, se necessário:

```bash
pkg update
pkg install python git
```

4. Baixe ou copie este projeto para o Termux.

5. Rode o app:

```bash
python3 scripts/clean_whatsapp.py
```

Na primeira execução, o app abre um assistente para escolher a pasta do WhatsApp, o perfil de limpeza e quais pastas devem ser incluídas.

## Abrir sem digitar o comando completo

Depois de atualizar ou instalar o projeto, entre na pasta dele e rode uma vez:

```bash
bash instalar-atalho.sh
```

Depois disso, você poderá abrir o app de qualquer pasta digitando apenas:

```bash
limpar-whatsapp
```

Se preferir não instalar o atalho, também dá para abrir pela pasta do projeto assim:

```bash
./limpar-whatsapp
```

Se aparecer "Permission denied" ao usar `./limpar-whatsapp`, rode:

```bash
chmod +x limpar-whatsapp instalar-atalho.sh
```

## Como usar

No menu principal:

```text
1) Analisar e limpar
2) Configurações
3) Restaurar arquivos da lixeira
4) Ajuda
0) Sair
```

Use primeiro `Analisar e limpar`. O app vai mostrar:

- Quantos arquivos serão mantidos.
- Quantos podem ser movidos para a lixeira.
- Quantos podem ser apagados definitivamente.
- O tamanho total por ação.
- Os maiores arquivos candidatos à limpeza.

Depois da prévia, você escolhe se quer aplicar ou não.

## Perfis de limpeza

Você pode escolher um perfil em `Configurações > Usar perfil de limpeza`:

- `Seguro`: mantém 60 dias, move 61-180 dias para lixeira e só sugere apagar acima de 180 dias.
- `Equilibrado`: mantém 30 dias, move 31-90 dias para lixeira e só sugere apagar acima de 90 dias.
- `Liberar mais espaço`: mantém 14 dias, move 15-45 dias para lixeira e só sugere apagar acima de 45 dias.

Também existe modo personalizado para editar os dias manualmente.

## Pastas opcionais

Em `Configurações > Escolher pastas incluídas`:

- `Sent`: mídias que você enviou para outras pessoas. Por padrão, fica incluída.
- `Private`: mídias ocultas da galeria. Por segurança, fica desativada por padrão.

## Restauração

Arquivos movidos para a lixeira podem ser restaurados pelo menu:

```text
3) Restaurar arquivos da lixeira
```

O app lista os registros disponíveis e mostra uma prévia antes de restaurar.

Importante: arquivos apagados definitivamente não podem ser restaurados por este app.

## Arquivos de configuração e registros

Configuração:

```text
~/.config/whatsapp_clean/config.json
```

Registros:

```text
~/.local/share/whatsapp_clean/logs/
```

Lixeira criada ao lado da pasta `Media` do WhatsApp:

```text
whatsapp_clean_trash_YYYYMMDD_HHMMSS
```

## Segurança

Antes de usar em arquivos importantes:

- Rode a análise e leia a prévia.
- Prefira o perfil `Seguro` na primeira execução.
- Faça backup se houver mídias muito importantes.
- Evite ativar `Private` sem entender o impacto.

Em Android 11 ou superior, o acesso a algumas pastas pode variar conforme o aparelho e as permissões concedidas ao Termux.

## Verificar sintaxe

```bash
python3 -m py_compile scripts/clean_whatsapp.py
```

## Licença

Distribuído sob a Licença MIT.

**Autor:** Daniel Ito Isaia
