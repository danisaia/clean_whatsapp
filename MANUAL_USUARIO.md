# Manual rápido do usuário

Este app ajuda a liberar espaço no celular limpando mídias antigas do WhatsApp pelo Termux.

Ele sempre mostra uma prévia antes de mexer nos arquivos. Nada é apagado sem confirmação.

## 1. Atualizar o app

Abra o Termux e entre na pasta do projeto:

```bash
cd clean_whatsapp
```

Atualize para a versão mais recente:

```bash
git pull origin main
```

## 2. Instalar o atalho

Rode este comando uma vez:

```bash
bash instalar-atalho.sh
```

Depois disso, para abrir o app, basta digitar:

```bash
limpar-whatsapp
```

## 3. Primeira configuração

Na primeira vez, o app vai perguntar:

- Qual pasta do WhatsApp deve ser usada.
- Qual perfil de limpeza você prefere.
- Se deve incluir mídias enviadas.
- Se deve incluir mídias ocultas.

Para começar com segurança, escolha o perfil `Seguro`.

## 4. Fazer uma limpeza

No menu principal, escolha:

```text
1) Analisar e limpar
```

O app vai mostrar uma prévia com:

- Arquivos que serão mantidos.
- Arquivos que podem ir para a lixeira.
- Arquivos que podem ser apagados definitivamente.
- Quanto espaço pode ser liberado.
- Quais são os maiores arquivos encontrados.

Leia a prévia com calma. Depois escolha se deseja aplicar a limpeza.

## 5. Lixeira e restauração

Arquivos movidos para a lixeira podem ser restaurados depois.

Para restaurar, escolha no menu:

```text
3) Restaurar arquivos da lixeira
```

Arquivos apagados definitivamente não podem ser restaurados pelo app.

## 6. Ajustar as regras

Para mudar os dias de limpeza ou as pastas incluídas, escolha:

```text
2) Configurações
```

Você pode:

- Trocar o perfil de limpeza.
- Editar os dias manualmente.
- Incluir ou remover mídias enviadas.
- Incluir ou remover mídias ocultas.
- Corrigir o caminho da pasta do WhatsApp.

## 7. Se aparecer erro de permissão

Rode no Termux:

```bash
termux-setup-storage
```

Depois feche e abra o Termux novamente.

## 8. Comandos úteis

Abrir o app:

```bash
limpar-whatsapp
```

Abrir sem instalar atalho, dentro da pasta do projeto:

```bash
./limpar-whatsapp
```

Atualizar o app:

```bash
git pull origin main
```

## Dica de segurança

Na dúvida, não apague definitivamente. Mova para a lixeira primeiro e restaure depois se precisar.
