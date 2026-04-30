#!/usr/bin/env python3
"""
Clean WhatsApp for Termux.

A guided WhatsApp media cleaner with a simple multilingual interface.
It always shows a preview before changing files and keeps operation records
for files moved to the trash.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


if sys.version_info < (3, 10):
    sys.stderr.write(
        "Clean WhatsApp needs Python 3.10 or newer.\n"
        "In Termux, run: pkg install python\n"
    )
    sys.exit(1)


APP_NAME = "Clean WhatsApp"
LANGUAGES = {
    "en": "English",
    "pt": "Português do Brasil",
    "es": "Español",
    "fr": "Français",
}

KNOWN_MEDIA_BASES = [
    "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media",
    "/storage/emulated/0/Android/media/com.whatsapp.w4b/WhatsApp Business/Media",
    "/storage/emulated/0/WhatsApp/Media",
]

CONFIG_PATH = os.path.expanduser("~/.config/clean-whatsapp/config.json")
LOGS_DIR = os.path.expanduser("~/.local/share/clean-whatsapp/logs")

DEFAULTS = {
    "language": None,
    "media_base": KNOWN_MEDIA_BASES[0],
    "age_keep_days": 60,
    "age_trash_min": 61,
    "age_trash_max": 180,
    "include_private": False,
    "include_sent": True,
    "show_top_files": 10,
    "setup_complete": False,
}

EXTENSION_MAP = {
    "images": {"jpg", "jpeg", "png", "webp", "heic"},
    "animated_gifs": {"gif"},
    "video": {"mp4", "mkv", "mov", "3gp", "avi"},
    "audio": {"mp3", "m4a", "opus", "ogg", "amr"},
    "voice": {"opus", "m4a", "amr"},
    "stickers": {"webp"},
    "profile": {"jpg", "jpeg", "png", "webp"},
}

GLOBAL_MEDIA_EXTS = set().union(*EXTENSION_MAP.values())
EXCLUDE_NAMES = {".nomedia", "desktop.ini", "thumbs.db"}
CURRENT_LANGUAGE = "en"


TEXT = {
    "en": {
        "app_title": "Clean WhatsApp",
        "press_enter": "Press Enter to continue...",
        "yes_no_hint": "Answer Y for yes or N for no.",
        "yes_no_default_yes": "Y/n",
        "yes_no_default_no": "y/N",
        "invalid_option": "Invalid option. Choose one of the listed options.",
        "integer_required": "Enter a whole number.",
        "min_value": "Enter a number greater than or equal to {min_value}.",
        "confirm_exact": "To confirm, type exactly: {word}",
        "select_language_title": "Language",
        "select_language_intro": "Choose the language for Clean WhatsApp.",
        "choose_language": "Choose a language",
        "storage_missing_title": "Permission or folder not found",
        "folder_missing": "Folder not found: {media_base}",
        "permission_denied": "Permission denied while opening the folder.",
        "folder_error": "Error while opening the folder: {error}",
        "storage_fix_1": "In Termux, you usually need to run this command once:",
        "storage_fix_2": "Then close and reopen Termux if needed.",
        "configured_folder": "Configured folder:",
        "storage_fix_3": "If your WhatsApp uses another folder, change it in Settings > WhatsApp folder.",
        "media_path_title": "WhatsApp media folder",
        "media_path_intro": "The app will look for media inside this folder:",
        "common_folders": "Common folders:",
        "exists": "exists",
        "not_found": "not found",
        "other_path": "Type another path",
        "choose_folder": "Choose the folder",
        "custom_path": "Paste the full WhatsApp media folder path",
        "custom_ages_title": "Custom ages",
        "custom_ages_help": "Use numbers in days. Example: keep up to 30 days, move 31 to 90 days to trash, delete above 90 days.",
        "keep_until": "Keep files up to how many days old",
        "trash_from": "Move to trash starting at how many days old",
        "trash_until": "Move to trash up to how many days old",
        "age_order_error": "The order must be: keep first, then move to trash, then delete permanently.",
        "rules_title": "Cleanup rules",
        "rules_intro": "Choose a cleanup profile. You will always see a preview before any change.",
        "recommended": "recommended",
        "custom": "Custom",
        "choose": "Choose",
        "preset_safe_name": "Safe",
        "preset_safe_desc": "keeps 60 days, moves 61 to 180 days to trash, and only suggests deleting above 180 days",
        "preset_balanced_name": "Balanced",
        "preset_balanced_desc": "keeps 30 days, moves 31 to 90 days to trash, and only suggests deleting above 90 days",
        "preset_space_name": "Free more space",
        "preset_space_desc": "keeps 14 days, moves 15 to 45 days to trash, and only suggests deleting above 45 days",
        "folders_title": "Included folders",
        "sent_help": "The 'Sent' folder stores media you sent to other people.",
        "include_sent": "Include sent media",
        "private_help": "The 'Private' folder usually stores media hidden from the gallery. For safety, the default is not to include it.",
        "include_private": "Include hidden media",
        "top_files_count": "How many large files to show in the preview",
        "setup_title": "First setup",
        "setup_intro_1": "This app helps free up space by deleting or moving old WhatsApp media.",
        "setup_intro_2": "Nothing will be changed without a preview and your confirmation.",
        "current_config": "Current settings:",
        "folder": "Folder",
        "keep": "Keep",
        "until_days": "up to {days} days",
        "trash_range": "Move to trash: {min_days} to {max_days} days",
        "delete_above": "Suggest deleting: above {days} days",
        "include_sent_summary": "Include sent media",
        "include_private_summary": "Include hidden media",
        "yes": "yes",
        "no": "no",
        "language_summary": "Language",
        "days_word": "days",
        "preview_title": "Cleanup preview",
        "summary": "Summary:",
        "media_analyzed": "Media analyzed: {count} ({size})",
        "ignored": "Not included because of safety rules or settings: {count}",
        "permission_errors": "Files without read permission: {count}",
        "what_will_happen": "What will happen:",
        "by_media_type": "By media type:",
        "largest_candidates": "Large files that can be cleaned (showing {count}):",
        "no_changes": "No change was applied.",
        "cleanup_done": "Cleanup finished.",
        "moved_count": "Moved to trash: {count}",
        "deleted_count": "Deleted permanently: {count}",
        "processed_space": "Processed space: {size}",
        "operation_record": "Operation record: {path}",
        "cleanup_title": "Analyze and clean",
        "scanning": "Analyzing files. On phones with lots of media, this may take a few minutes...",
        "nothing_to_clean": "Nothing is old enough to clean with the current rules.",
        "preview_only": "This was only a preview. No file has been changed yet.",
        "apply_cleanup": "Do you want to apply any cleanup now",
        "move_to_trash": "Move {count} files ({size}) to trash",
        "also_delete": "Also permanently delete {count} files ({size})",
        "delete_warning": "Permanent deletion cannot be undone by this app. Files moved to trash can be restored; deleted files cannot.",
        "delete_word": "DELETE",
        "move_failed": "Failed to move: {path} -> {error}",
        "delete_failed": "Failed to delete: {path} -> {error}",
        "restore_reason_error": "error recorded during the operation",
        "restore_reason_deleted": "file was permanently deleted",
        "restore_reason_incomplete": "incomplete record",
        "restore_reason_missing": "file not found in trash",
        "restore_preview_title": "Restore preview",
        "can_restore": "Can be restored: {count}",
        "cannot_restore": "Cannot be restored: {count}",
        "more_files": "... and {count} more files",
        "skipped_items": "Items that will not be restored:",
        "restore_now": "Restore these files now",
        "restore_failed": "Failed to restore {path}: {error}",
        "restored_count": "Files restored: {count}",
        "restore_title": "Restore files",
        "no_records": "No cleanup records found.",
        "back": "Back",
        "choose_record": "Choose a record",
        "settings_title": "Settings",
        "menu_profile": "Use cleanup profile",
        "menu_ages": "Edit ages manually",
        "menu_folders": "Choose included folders",
        "menu_path": "Change WhatsApp folder",
        "menu_language": "Change language",
        "menu_setup": "Run first setup again",
        "menu_analyze": "Analyze and clean",
        "menu_settings": "Settings",
        "menu_restore": "Restore files from trash",
        "menu_help": "Help",
        "menu_exit": "Exit",
        "help_title": "Quick help",
        "help_1": "1. First use 'Analyze and clean' to see the preview.",
        "help_2": "2. Files in 'Move to trash' leave the WhatsApp folder, but can be restored from the menu.",
        "help_3": "3. Files in 'Delete permanently' are only removed if you type DELETE.",
        "help_4": "4. To be more conservative, choose the Safe profile in Settings.",
        "help_5": "5. If permission is denied, run in Termux: termux-setup-storage",
        "exiting": "Exiting.",
        "interrupted": "Interrupted.",
        "media_images": "Images",
        "media_gifs": "GIFs",
        "media_video": "Videos",
        "media_audio": "Audio",
        "media_voice": "Voice messages",
        "media_stickers": "Stickers",
        "media_profile": "Profile photos",
        "media_other": "Other media",
        "action_keep": "Keep",
        "action_trash": "Move to trash",
        "action_delete": "Delete permanently",
    },
    "pt": {
        "app_title": "Clean WhatsApp",
        "press_enter": "Pressione Enter para continuar...",
        "yes_no_hint": "Responda com S para sim ou N para não.",
        "yes_no_default_yes": "S/n",
        "yes_no_default_no": "s/N",
        "invalid_option": "Opção inválida. Escolha uma das opções mostradas.",
        "integer_required": "Digite um número inteiro.",
        "min_value": "Digite um número maior ou igual a {min_value}.",
        "confirm_exact": "Para confirmar, digite exatamente: {word}",
        "select_language_title": "Idioma",
        "select_language_intro": "Escolha o idioma do Clean WhatsApp.",
        "choose_language": "Escolha um idioma",
        "storage_missing_title": "Permissão ou pasta não encontrada",
        "folder_missing": "Pasta não encontrada: {media_base}",
        "permission_denied": "Permissão negada ao acessar a pasta.",
        "folder_error": "Erro ao acessar a pasta: {error}",
        "storage_fix_1": "No Termux, normalmente você precisa rodar este comando uma vez:",
        "storage_fix_2": "Depois feche e abra o Termux novamente, se necessário.",
        "configured_folder": "Pasta configurada:",
        "storage_fix_3": "Se o seu WhatsApp usa outra pasta, altere em Configurações > Pasta do WhatsApp.",
        "media_path_title": "Pasta de mídia do WhatsApp",
        "media_path_intro": "O app vai procurar mídias dentro desta pasta:",
        "common_folders": "Pastas comuns:",
        "exists": "existe",
        "not_found": "não encontrada",
        "other_path": "Digitar outro caminho",
        "choose_folder": "Escolha a pasta",
        "custom_path": "Cole o caminho completo da pasta de mídia do WhatsApp",
        "custom_ages_title": "Idades personalizadas",
        "custom_ages_help": "Use números em dias. Exemplo: manter até 30 dias, mover de 31 a 90 dias para a lixeira e apagar acima de 90 dias.",
        "keep_until": "Manter arquivos com até quantos dias",
        "trash_from": "Mover para lixeira a partir de quantos dias",
        "trash_until": "Mover para lixeira até quantos dias",
        "age_order_error": "A ordem precisa ser: manter primeiro, depois mover para a lixeira, depois apagar definitivamente.",
        "rules_title": "Regras de limpeza",
        "rules_intro": "Escolha um perfil de limpeza. Você sempre verá uma prévia antes de qualquer alteração.",
        "recommended": "recomendado",
        "custom": "Personalizado",
        "choose": "Escolha",
        "preset_safe_name": "Seguro",
        "preset_safe_desc": "mantém 60 dias, move de 61 a 180 dias para a lixeira e só sugere apagar acima de 180 dias",
        "preset_balanced_name": "Equilibrado",
        "preset_balanced_desc": "mantém 30 dias, move de 31 a 90 dias para a lixeira e só sugere apagar acima de 90 dias",
        "preset_space_name": "Liberar mais espaço",
        "preset_space_desc": "mantém 14 dias, move de 15 a 45 dias para a lixeira e só sugere apagar acima de 45 dias",
        "folders_title": "Pastas incluídas",
        "sent_help": "A pasta 'Sent' guarda mídias que você enviou para outras pessoas.",
        "include_sent": "Incluir mídias enviadas",
        "private_help": "A pasta 'Private' costuma guardar mídias ocultas da galeria. Por segurança, o padrão é não incluir.",
        "include_private": "Incluir mídias ocultas",
        "top_files_count": "Quantos arquivos grandes mostrar na prévia",
        "setup_title": "Primeira configuração",
        "setup_intro_1": "Este app ajuda a liberar espaço apagando ou movendo mídias antigas do WhatsApp.",
        "setup_intro_2": "Nada será alterado sem uma prévia e uma confirmação sua.",
        "current_config": "Configuração atual:",
        "folder": "Pasta",
        "keep": "Manter",
        "until_days": "até {days} dias",
        "trash_range": "Mover para lixeira: {min_days} a {max_days} dias",
        "delete_above": "Sugerir apagar: acima de {days} dias",
        "include_sent_summary": "Incluir mídias enviadas",
        "include_private_summary": "Incluir mídias ocultas",
        "yes": "sim",
        "no": "não",
        "language_summary": "Idioma",
        "days_word": "dias",
        "preview_title": "Prévia da limpeza",
        "summary": "Resumo:",
        "media_analyzed": "Mídias analisadas: {count} ({size})",
        "ignored": "Não incluídas por segurança ou configuração: {count}",
        "permission_errors": "Arquivos sem permissão de leitura: {count}",
        "what_will_happen": "O que será feito:",
        "by_media_type": "Por tipo de mídia:",
        "largest_candidates": "Arquivos maiores que podem ser limpos (mostrando {count}):",
        "no_changes": "Nenhuma alteração foi aplicada.",
        "cleanup_done": "Limpeza concluída.",
        "moved_count": "Movidos para lixeira: {count}",
        "deleted_count": "Apagados definitivamente: {count}",
        "processed_space": "Espaço processado: {size}",
        "operation_record": "Registro da operação: {path}",
        "cleanup_title": "Analisar e limpar",
        "scanning": "Analisando arquivos. Em celulares com muita mídia, isso pode levar alguns minutos...",
        "nothing_to_clean": "Nada antigo o suficiente para limpar com as regras atuais.",
        "preview_only": "Esta foi apenas a prévia. Nenhum arquivo foi alterado ainda.",
        "apply_cleanup": "Deseja aplicar alguma limpeza agora",
        "move_to_trash": "Mover {count} arquivos ({size}) para a lixeira",
        "also_delete": "Também apagar definitivamente {count} arquivos ({size})",
        "delete_warning": "Apagar definitivamente não pode ser desfeito por este app. Arquivos movidos para a lixeira podem ser restaurados; arquivos apagados não.",
        "delete_word": "APAGAR",
        "move_failed": "Falha ao mover: {path} -> {error}",
        "delete_failed": "Falha ao apagar: {path} -> {error}",
        "restore_reason_error": "erro registrado na operação",
        "restore_reason_deleted": "arquivo apagado definitivamente",
        "restore_reason_incomplete": "entrada incompleta",
        "restore_reason_missing": "arquivo não encontrado na lixeira",
        "restore_preview_title": "Prévia de restauração",
        "can_restore": "Podem ser restaurados: {count}",
        "cannot_restore": "Não podem ser restaurados: {count}",
        "more_files": "... e mais {count} arquivos",
        "skipped_items": "Itens que não serão restaurados:",
        "restore_now": "Restaurar estes arquivos agora",
        "restore_failed": "Falha ao restaurar {path}: {error}",
        "restored_count": "Arquivos restaurados: {count}",
        "restore_title": "Restaurar arquivos",
        "no_records": "Nenhum registro de limpeza encontrado.",
        "back": "Voltar",
        "choose_record": "Escolha um registro",
        "settings_title": "Configurações",
        "menu_profile": "Usar perfil de limpeza",
        "menu_ages": "Editar idades manualmente",
        "menu_folders": "Escolher pastas incluídas",
        "menu_path": "Alterar caminho do WhatsApp",
        "menu_language": "Alterar idioma",
        "menu_setup": "Refazer assistente inicial",
        "menu_analyze": "Analisar e limpar",
        "menu_settings": "Configurações",
        "menu_restore": "Restaurar arquivos da lixeira",
        "menu_help": "Ajuda",
        "menu_exit": "Sair",
        "help_title": "Ajuda rápida",
        "help_1": "1. Primeiro use 'Analisar e limpar' para ver a prévia.",
        "help_2": "2. Arquivos em 'Mover para lixeira' saem da pasta do WhatsApp, mas podem ser restaurados pelo menu.",
        "help_3": "3. Arquivos em 'Apagar definitivamente' só são removidos se você digitar APAGAR.",
        "help_4": "4. Para ser mais conservador, escolha o perfil Seguro em Configurações.",
        "help_5": "5. Se aparecer permissão negada, rode no Termux: termux-setup-storage",
        "exiting": "Saindo.",
        "interrupted": "Interrompido.",
        "media_images": "Imagens",
        "media_gifs": "GIFs",
        "media_video": "Vídeos",
        "media_audio": "Áudios",
        "media_voice": "Mensagens de voz",
        "media_stickers": "Figurinhas",
        "media_profile": "Fotos de perfil",
        "media_other": "Outras mídias",
        "action_keep": "Manter",
        "action_trash": "Mover para lixeira",
        "action_delete": "Apagar definitivamente",
    },
    "es": {},
    "fr": {},
}

TEXT["es"] = {
    **TEXT["en"],
    "select_language_title": "Idioma",
    "select_language_intro": "Elige el idioma de Clean WhatsApp.",
    "choose_language": "Elige un idioma",
    "press_enter": "Pulsa Enter para continuar...",
    "yes_no_hint": "Responde S para sí o N para no.",
    "yes_no_default_yes": "S/n",
    "yes_no_default_no": "s/N",
    "invalid_option": "Opción no válida. Elige una de las opciones mostradas.",
    "integer_required": "Escribe un número entero.",
    "min_value": "Escribe un número mayor o igual a {min_value}.",
    "confirm_exact": "Para confirmar, escribe exactamente: {word}",
    "storage_missing_title": "Permiso o carpeta no encontrada",
    "folder_missing": "Carpeta no encontrada: {media_base}",
    "permission_denied": "Permiso denegado al abrir la carpeta.",
    "folder_error": "Error al abrir la carpeta: {error}",
    "storage_fix_1": "En Termux, normalmente debes ejecutar este comando una vez:",
    "storage_fix_2": "Después cierra y abre Termux de nuevo si es necesario.",
    "configured_folder": "Carpeta configurada:",
    "storage_fix_3": "Si tu WhatsApp usa otra carpeta, cámbiala en Ajustes > Carpeta de WhatsApp.",
    "media_path_title": "Carpeta de medios de WhatsApp",
    "media_path_intro": "La app buscará medios dentro de esta carpeta:",
    "common_folders": "Carpetas comunes:",
    "exists": "existe",
    "not_found": "no encontrada",
    "other_path": "Escribir otra ruta",
    "choose_folder": "Elige la carpeta",
    "custom_path": "Pega la ruta completa de la carpeta de medios de WhatsApp",
    "custom_ages_title": "Edades personalizadas",
    "custom_ages_help": "Usa números en días. Ejemplo: conservar hasta 30 días, mover de 31 a 90 días a la papelera y borrar por encima de 90 días.",
    "keep_until": "Conservar archivos de hasta cuántos días",
    "trash_from": "Mover a la papelera desde cuántos días",
    "trash_until": "Mover a la papelera hasta cuántos días",
    "age_order_error": "El orden debe ser: conservar primero, luego mover a la papelera y después borrar definitivamente.",
    "rules_title": "Reglas de limpieza",
    "rules_intro": "Elige un perfil de limpieza. Siempre verás una vista previa antes de cualquier cambio.",
    "recommended": "recomendado",
    "custom": "Personalizado",
    "choose": "Elige",
    "preset_safe_name": "Seguro",
    "preset_safe_desc": "conserva 60 días, mueve de 61 a 180 días a la papelera y solo sugiere borrar por encima de 180 días",
    "preset_balanced_name": "Equilibrado",
    "preset_balanced_desc": "conserva 30 días, mueve de 31 a 90 días a la papelera y solo sugiere borrar por encima de 90 días",
    "preset_space_name": "Liberar más espacio",
    "preset_space_desc": "conserva 14 días, mueve de 15 a 45 días a la papelera y solo sugiere borrar por encima de 45 días",
    "folders_title": "Carpetas incluidas",
    "sent_help": "La carpeta 'Sent' guarda medios que enviaste a otras personas.",
    "include_sent": "Incluir medios enviados",
    "private_help": "La carpeta 'Private' suele guardar medios ocultos de la galería. Por seguridad, el valor predeterminado es no incluirla.",
    "include_private": "Incluir medios ocultos",
    "top_files_count": "Cuántos archivos grandes mostrar en la vista previa",
    "setup_title": "Primera configuración",
    "setup_intro_1": "Esta app ayuda a liberar espacio borrando o moviendo medios antiguos de WhatsApp.",
    "setup_intro_2": "Nada cambiará sin una vista previa y tu confirmación.",
    "current_config": "Configuración actual:",
    "folder": "Carpeta",
    "keep": "Conservar",
    "until_days": "hasta {days} días",
    "trash_range": "Mover a la papelera: {min_days} a {max_days} días",
    "delete_above": "Sugerir borrar: por encima de {days} días",
    "include_sent_summary": "Incluir medios enviados",
    "include_private_summary": "Incluir medios ocultos",
    "yes": "sí",
    "no": "no",
    "language_summary": "Idioma",
    "days_word": "días",
    "preview_title": "Vista previa de limpieza",
    "summary": "Resumen:",
    "media_analyzed": "Medios analizados: {count} ({size})",
    "ignored": "No incluidos por seguridad o configuración: {count}",
    "permission_errors": "Archivos sin permiso de lectura: {count}",
    "what_will_happen": "Qué se hará:",
    "by_media_type": "Por tipo de medio:",
    "largest_candidates": "Archivos grandes que se pueden limpiar (mostrando {count}):",
    "no_changes": "No se aplicó ningún cambio.",
    "cleanup_done": "Limpieza terminada.",
    "moved_count": "Movidos a la papelera: {count}",
    "deleted_count": "Borrados definitivamente: {count}",
    "processed_space": "Espacio procesado: {size}",
    "operation_record": "Registro de la operación: {path}",
    "cleanup_title": "Analizar y limpiar",
    "scanning": "Analizando archivos. En teléfonos con muchos medios, esto puede tardar unos minutos...",
    "nothing_to_clean": "No hay nada lo bastante antiguo para limpiar con las reglas actuales.",
    "preview_only": "Esto fue solo una vista previa. Ningún archivo ha cambiado todavía.",
    "apply_cleanup": "¿Quieres aplicar alguna limpieza ahora",
    "move_to_trash": "Mover {count} archivos ({size}) a la papelera",
    "also_delete": "También borrar definitivamente {count} archivos ({size})",
    "delete_warning": "El borrado definitivo no se puede deshacer con esta app. Los archivos movidos a la papelera se pueden restaurar; los borrados no.",
    "delete_word": "BORRAR",
    "move_failed": "Error al mover: {path} -> {error}",
    "delete_failed": "Error al borrar: {path} -> {error}",
    "restore_reason_error": "error registrado durante la operación",
    "restore_reason_deleted": "archivo borrado definitivamente",
    "restore_reason_incomplete": "registro incompleto",
    "restore_reason_missing": "archivo no encontrado en la papelera",
    "restore_preview_title": "Vista previa de restauración",
    "can_restore": "Se pueden restaurar: {count}",
    "cannot_restore": "No se pueden restaurar: {count}",
    "more_files": "... y {count} archivos más",
    "skipped_items": "Elementos que no se restaurarán:",
    "restore_now": "Restaurar estos archivos ahora",
    "restore_failed": "Error al restaurar {path}: {error}",
    "restored_count": "Archivos restaurados: {count}",
    "restore_title": "Restaurar archivos",
    "no_records": "No se encontraron registros de limpieza.",
    "back": "Volver",
    "choose_record": "Elige un registro",
    "settings_title": "Ajustes",
    "menu_profile": "Usar perfil de limpieza",
    "menu_ages": "Editar edades manualmente",
    "menu_folders": "Elegir carpetas incluidas",
    "menu_path": "Cambiar carpeta de WhatsApp",
    "menu_language": "Cambiar idioma",
    "menu_setup": "Ejecutar de nuevo la configuración inicial",
    "menu_analyze": "Analizar y limpiar",
    "menu_settings": "Ajustes",
    "menu_restore": "Restaurar archivos de la papelera",
    "menu_help": "Ayuda",
    "menu_exit": "Salir",
    "help_title": "Ayuda rápida",
    "help_1": "1. Primero usa 'Analizar y limpiar' para ver la vista previa.",
    "help_2": "2. Los archivos en 'Mover a la papelera' salen de la carpeta de WhatsApp, pero se pueden restaurar desde el menú.",
    "help_3": "3. Los archivos en 'Borrar definitivamente' solo se eliminan si escribes BORRAR.",
    "help_4": "4. Para ser más conservador, elige el perfil Seguro en Ajustes.",
    "help_5": "5. Si se deniega el permiso, ejecuta en Termux: termux-setup-storage",
    "exiting": "Saliendo.",
    "interrupted": "Interrumpido.",
    "media_images": "Imágenes",
    "media_gifs": "GIFs",
    "media_video": "Videos",
    "media_audio": "Audios",
    "media_voice": "Mensajes de voz",
    "media_stickers": "Stickers",
    "media_profile": "Fotos de perfil",
    "media_other": "Otros medios",
    "action_keep": "Conservar",
    "action_trash": "Mover a la papelera",
    "action_delete": "Borrar definitivamente",
}

TEXT["fr"] = {
    **TEXT["en"],
    "select_language_title": "Langue",
    "select_language_intro": "Choisissez la langue de Clean WhatsApp.",
    "choose_language": "Choisissez une langue",
    "press_enter": "Appuyez sur Entrée pour continuer...",
    "yes_no_hint": "Répondez O pour oui ou N pour non.",
    "yes_no_default_yes": "O/n",
    "yes_no_default_no": "o/N",
    "invalid_option": "Option non valide. Choisissez une des options affichées.",
    "integer_required": "Entrez un nombre entier.",
    "min_value": "Entrez un nombre supérieur ou égal à {min_value}.",
    "confirm_exact": "Pour confirmer, tapez exactement : {word}",
    "storage_missing_title": "Autorisation ou dossier introuvable",
    "folder_missing": "Dossier introuvable : {media_base}",
    "permission_denied": "Autorisation refusée lors de l'ouverture du dossier.",
    "folder_error": "Erreur lors de l'ouverture du dossier : {error}",
    "storage_fix_1": "Dans Termux, vous devez généralement exécuter cette commande une fois :",
    "storage_fix_2": "Ensuite, fermez puis rouvrez Termux si nécessaire.",
    "configured_folder": "Dossier configuré :",
    "storage_fix_3": "Si votre WhatsApp utilise un autre dossier, changez-le dans Paramètres > Dossier WhatsApp.",
    "media_path_title": "Dossier des médias WhatsApp",
    "media_path_intro": "L'app cherchera les médias dans ce dossier :",
    "common_folders": "Dossiers courants :",
    "exists": "existe",
    "not_found": "introuvable",
    "other_path": "Saisir un autre chemin",
    "choose_folder": "Choisissez le dossier",
    "custom_path": "Collez le chemin complet du dossier des médias WhatsApp",
    "custom_ages_title": "Âges personnalisés",
    "custom_ages_help": "Utilisez des nombres en jours. Exemple : garder jusqu'à 30 jours, déplacer de 31 à 90 jours vers la corbeille et supprimer au-delà de 90 jours.",
    "keep_until": "Garder les fichiers jusqu'à combien de jours",
    "trash_from": "Déplacer vers la corbeille à partir de combien de jours",
    "trash_until": "Déplacer vers la corbeille jusqu'à combien de jours",
    "age_order_error": "L'ordre doit être : garder d'abord, puis déplacer vers la corbeille, puis supprimer définitivement.",
    "rules_title": "Règles de nettoyage",
    "rules_intro": "Choisissez un profil de nettoyage. Vous verrez toujours un aperçu avant tout changement.",
    "recommended": "recommandé",
    "custom": "Personnalisé",
    "choose": "Choisissez",
    "preset_safe_name": "Sûr",
    "preset_safe_desc": "garde 60 jours, déplace de 61 à 180 jours vers la corbeille et suggère seulement de supprimer au-delà de 180 jours",
    "preset_balanced_name": "Équilibré",
    "preset_balanced_desc": "garde 30 jours, déplace de 31 à 90 jours vers la corbeille et suggère seulement de supprimer au-delà de 90 jours",
    "preset_space_name": "Libérer plus d'espace",
    "preset_space_desc": "garde 14 jours, déplace de 15 à 45 jours vers la corbeille et suggère seulement de supprimer au-delà de 45 jours",
    "folders_title": "Dossiers inclus",
    "sent_help": "Le dossier 'Sent' contient les médias que vous avez envoyés à d'autres personnes.",
    "include_sent": "Inclure les médias envoyés",
    "private_help": "Le dossier 'Private' contient souvent des médias cachés de la galerie. Par sécurité, il n'est pas inclus par défaut.",
    "include_private": "Inclure les médias cachés",
    "top_files_count": "Combien de gros fichiers afficher dans l'aperçu",
    "setup_title": "Première configuration",
    "setup_intro_1": "Cette app aide à libérer de l'espace en supprimant ou en déplaçant les anciens médias WhatsApp.",
    "setup_intro_2": "Rien ne sera modifié sans aperçu et sans votre confirmation.",
    "current_config": "Paramètres actuels :",
    "folder": "Dossier",
    "keep": "Garder",
    "until_days": "jusqu'à {days} jours",
    "trash_range": "Déplacer vers la corbeille : {min_days} à {max_days} jours",
    "delete_above": "Suggérer la suppression : au-delà de {days} jours",
    "include_sent_summary": "Inclure les médias envoyés",
    "include_private_summary": "Inclure les médias cachés",
    "yes": "oui",
    "no": "non",
    "language_summary": "Langue",
    "days_word": "jours",
    "preview_title": "Aperçu du nettoyage",
    "summary": "Résumé :",
    "media_analyzed": "Médias analysés : {count} ({size})",
    "ignored": "Non inclus pour sécurité ou paramètres : {count}",
    "permission_errors": "Fichiers sans autorisation de lecture : {count}",
    "what_will_happen": "Ce qui sera fait :",
    "by_media_type": "Par type de média :",
    "largest_candidates": "Gros fichiers pouvant être nettoyés ({count} affichés) :",
    "no_changes": "Aucun changement n'a été appliqué.",
    "cleanup_done": "Nettoyage terminé.",
    "moved_count": "Déplacés vers la corbeille : {count}",
    "deleted_count": "Supprimés définitivement : {count}",
    "processed_space": "Espace traité : {size}",
    "operation_record": "Journal de l'opération : {path}",
    "cleanup_title": "Analyser et nettoyer",
    "scanning": "Analyse des fichiers. Sur les téléphones avec beaucoup de médias, cela peut prendre quelques minutes...",
    "nothing_to_clean": "Aucun fichier n'est assez ancien pour être nettoyé avec les règles actuelles.",
    "preview_only": "Ceci n'était qu'un aperçu. Aucun fichier n'a encore été modifié.",
    "apply_cleanup": "Voulez-vous appliquer un nettoyage maintenant",
    "move_to_trash": "Déplacer {count} fichiers ({size}) vers la corbeille",
    "also_delete": "Supprimer aussi définitivement {count} fichiers ({size})",
    "delete_warning": "La suppression définitive ne peut pas être annulée par cette app. Les fichiers déplacés vers la corbeille peuvent être restaurés ; les fichiers supprimés ne le peuvent pas.",
    "delete_word": "SUPPRIMER",
    "move_failed": "Échec du déplacement : {path} -> {error}",
    "delete_failed": "Échec de la suppression : {path} -> {error}",
    "restore_reason_error": "erreur enregistrée pendant l'opération",
    "restore_reason_deleted": "fichier supprimé définitivement",
    "restore_reason_incomplete": "journal incomplet",
    "restore_reason_missing": "fichier introuvable dans la corbeille",
    "restore_preview_title": "Aperçu de restauration",
    "can_restore": "Peuvent être restaurés : {count}",
    "cannot_restore": "Ne peuvent pas être restaurés : {count}",
    "more_files": "... et {count} fichiers de plus",
    "skipped_items": "Éléments qui ne seront pas restaurés :",
    "restore_now": "Restaurer ces fichiers maintenant",
    "restore_failed": "Échec de la restauration de {path} : {error}",
    "restored_count": "Fichiers restaurés : {count}",
    "restore_title": "Restaurer des fichiers",
    "no_records": "Aucun journal de nettoyage trouvé.",
    "back": "Retour",
    "choose_record": "Choisissez un journal",
    "settings_title": "Paramètres",
    "menu_profile": "Utiliser un profil de nettoyage",
    "menu_ages": "Modifier les âges manuellement",
    "menu_folders": "Choisir les dossiers inclus",
    "menu_path": "Changer le dossier WhatsApp",
    "menu_language": "Changer la langue",
    "menu_setup": "Relancer la première configuration",
    "menu_analyze": "Analyser et nettoyer",
    "menu_settings": "Paramètres",
    "menu_restore": "Restaurer les fichiers de la corbeille",
    "menu_help": "Aide",
    "menu_exit": "Quitter",
    "help_title": "Aide rapide",
    "help_1": "1. Utilisez d'abord 'Analyser et nettoyer' pour voir l'aperçu.",
    "help_2": "2. Les fichiers dans 'Déplacer vers la corbeille' quittent le dossier WhatsApp, mais peuvent être restaurés depuis le menu.",
    "help_3": "3. Les fichiers dans 'Supprimer définitivement' ne sont supprimés que si vous tapez SUPPRIMER.",
    "help_4": "4. Pour être plus prudent, choisissez le profil Sûr dans Paramètres.",
    "help_5": "5. Si l'autorisation est refusée, exécutez dans Termux : termux-setup-storage",
    "exiting": "Fermeture.",
    "interrupted": "Interrompu.",
    "media_images": "Images",
    "media_gifs": "GIFs",
    "media_video": "Vidéos",
    "media_audio": "Audio",
    "media_voice": "Messages vocaux",
    "media_stickers": "Stickers",
    "media_profile": "Photos de profil",
    "media_other": "Autres médias",
    "action_keep": "Garder",
    "action_trash": "Déplacer vers la corbeille",
    "action_delete": "Supprimer définitivement",
}


PRESET_DATA = {
    "1": ("preset_safe_name", "preset_safe_desc", 60, 61, 180),
    "2": ("preset_balanced_name", "preset_balanced_desc", 30, 31, 90),
    "3": ("preset_space_name", "preset_space_desc", 14, 15, 45),
}

MEDIA_LABEL_KEYS = {
    "images": "media_images",
    "animated_gifs": "media_gifs",
    "video": "media_video",
    "audio": "media_audio",
    "voice": "media_voice",
    "stickers": "media_stickers",
    "profile": "media_profile",
    "other": "media_other",
}

ACTION_LABEL_KEYS = {
    "keep": "action_keep",
    "trash": "action_trash",
    "delete": "action_delete",
}


@dataclass
class FileRecord:
    src: str
    rel_path: str
    size: int
    mtime: float
    age_days: int
    action: str
    media_type: str


def set_language(language: str | None) -> None:
    global CURRENT_LANGUAGE
    CURRENT_LANGUAGE = language if language in LANGUAGES else "en"


def t(key: str, **kwargs) -> str:
    value = TEXT.get(CURRENT_LANGUAGE, TEXT["en"]).get(key, TEXT["en"].get(key, key))
    return value.format(**kwargs) if kwargs else value


def ensure_dirs() -> None:
    Path(CONFIG_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)


def load_config() -> Dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        cfg = {}

    for key, value in DEFAULTS.items():
        cfg.setdefault(key, value)
    return cfg


def save_config(cfg: Dict) -> None:
    ensure_dirs()
    data = {k: v for k, v in cfg.items() if not k.startswith("_")}
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def header(title: str) -> None:
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)


def pause() -> None:
    input("\n" + t("press_enter"))


def prompt_yes_no(msg: str, default_yes: bool = True) -> bool:
    suffix = t("yes_no_default_yes") if default_yes else t("yes_no_default_no")
    yes_values = {"y", "yes", "s", "sim", "si", "sí", "o", "oui"}
    no_values = {"n", "no", "nao", "não", "non"}
    while True:
        ans = input(f"{msg} [{suffix}]: ").strip().lower()
        if ans == "":
            return default_yes
        if ans in yes_values:
            return True
        if ans in no_values:
            return False
        print(t("yes_no_hint"))


def prompt_choice(msg: str, choices: Iterable[str], default: str) -> str:
    valid = set(choices)
    while True:
        ans = input(f"{msg} [{default}]: ").strip() or default
        if ans in valid:
            return ans
        print(t("invalid_option"))


def prompt_int(msg: str, default: int, min_value: int = 0) -> int:
    while True:
        raw = input(f"{msg} [{default}]: ").strip()
        if raw == "":
            return default
        try:
            value = int(raw)
        except ValueError:
            print(t("integer_required"))
            continue
        if value < min_value:
            print(t("min_value", min_value=min_value))
            continue
        return value


def strong_confirm(msg: str, word: str) -> bool:
    print("\n" + msg)
    print(t("confirm_exact", word=word))
    return input("> ").strip() == word


def human_size(n: int) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.1f}{unit}"
        value /= 1024.0
    return f"{value:.1f}TB"


def normalize_text(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def select_language(cfg: Dict) -> None:
    header(t("select_language_title"))
    print(t("select_language_intro") + "\n")
    codes = list(LANGUAGES.keys())
    for idx, code in enumerate(codes, start=1):
        print(f"{idx}) {LANGUAGES[code]}")
    current = cfg.get("language")
    default = str(codes.index(current) + 1) if current in codes else "1"
    choice = prompt_choice(t("choose_language"), {str(i) for i in range(1, len(codes) + 1)}, default)
    cfg["language"] = codes[int(choice) - 1]
    set_language(cfg["language"])
    save_config(cfg)


def detect_media_base(current: str | None = None) -> str:
    if current and os.path.exists(current):
        return current
    for path in KNOWN_MEDIA_BASES:
        if os.path.exists(path):
            return path
    return current or KNOWN_MEDIA_BASES[0]


def check_storage_access(media_base: str) -> Tuple[bool, str]:
    if not os.path.exists(media_base):
        return False, t("folder_missing", media_base=media_base)
    try:
        os.listdir(media_base)
    except PermissionError:
        return False, t("permission_denied")
    except Exception as exc:
        return False, t("folder_error", error=exc)
    return True, "OK"


def explain_storage_fix(media_base: str, reason: str) -> None:
    header(t("storage_missing_title"))
    print(reason)
    print("\n" + t("storage_fix_1"))
    print("  termux-setup-storage")
    print("\n" + t("storage_fix_2"))
    print("\n" + t("configured_folder"))
    print(f"  {media_base}")
    print("\n" + t("storage_fix_3"))


def configure_media_path(cfg: Dict) -> None:
    header(t("media_path_title"))
    detected = detect_media_base(cfg.get("media_base"))
    default_choice = "1"
    if detected in KNOWN_MEDIA_BASES:
        default_choice = str(KNOWN_MEDIA_BASES.index(detected) + 1)
    print(t("media_path_intro"))
    print(f"  {detected}")
    print("\n" + t("common_folders"))
    for idx, path in enumerate(KNOWN_MEDIA_BASES, start=1):
        marker = t("exists") if os.path.exists(path) else t("not_found")
        print(f"{idx}) {path} ({marker})")
    print(f"4) {t('other_path')}")

    choice = prompt_choice(t("choose_folder"), {"1", "2", "3", "4"}, default_choice)
    if choice in {"1", "2", "3"}:
        cfg["media_base"] = KNOWN_MEDIA_BASES[int(choice) - 1]
    else:
        custom = input(t("custom_path") + ": ").strip()
        if custom:
            cfg["media_base"] = custom
    save_config(cfg)


def apply_preset(cfg: Dict, key: str) -> None:
    _, _, keep, trash_min, trash_max = PRESET_DATA[key]
    cfg["age_keep_days"] = keep
    cfg["age_trash_min"] = trash_min
    cfg["age_trash_max"] = trash_max


def configure_custom_ages(cfg: Dict) -> None:
    header(t("custom_ages_title"))
    print(t("custom_ages_help"))
    while True:
        keep = prompt_int(t("keep_until"), int(cfg["age_keep_days"]), 0)
        trash_min = prompt_int(t("trash_from"), int(cfg["age_trash_min"]), keep + 1)
        trash_max = prompt_int(t("trash_until"), int(cfg["age_trash_max"]), trash_min)
        if keep < trash_min <= trash_max:
            cfg["age_keep_days"] = keep
            cfg["age_trash_min"] = trash_min
            cfg["age_trash_max"] = trash_max
            save_config(cfg)
            return
        print(t("age_order_error"))


def configure_preset_or_custom(cfg: Dict) -> None:
    header(t("rules_title"))
    print(t("rules_intro") + "\n")
    for key, (name_key, desc_key, *_limits) in PRESET_DATA.items():
        extra = f" ({t('recommended')})" if key == "1" else ""
        print(f"{key}) {t(name_key)}{extra}: {t(desc_key)}")
    print(f"4) {t('custom')}")

    choice = prompt_choice(t("choose"), {"1", "2", "3", "4"}, "1")
    if choice == "4":
        configure_custom_ages(cfg)
    else:
        apply_preset(cfg, choice)
        save_config(cfg)


def configure_included_folders(cfg: Dict) -> None:
    header(t("folders_title"))
    print(t("sent_help"))
    cfg["include_sent"] = prompt_yes_no(t("include_sent"), bool(cfg["include_sent"]))
    print("\n" + t("private_help"))
    cfg["include_private"] = prompt_yes_no(t("include_private"), bool(cfg["include_private"]))
    cfg["show_top_files"] = prompt_int(t("top_files_count"), int(cfg["show_top_files"]), 1)
    save_config(cfg)


def setup_wizard(cfg: Dict) -> None:
    header(t("setup_title"))
    print(t("setup_intro_1"))
    print(t("setup_intro_2"))

    cfg["media_base"] = detect_media_base(cfg.get("media_base"))
    configure_media_path(cfg)

    ok, reason = check_storage_access(cfg["media_base"])
    if not ok:
        explain_storage_fix(cfg["media_base"], reason)
        pause()

    configure_preset_or_custom(cfg)
    configure_included_folders(cfg)
    cfg["setup_complete"] = True
    save_config(cfg)


def get_relative_path(path: str, base: str) -> str:
    try:
        return str(Path(path).relative_to(Path(base)))
    except ValueError:
        return os.path.relpath(path, base)


def detect_media_type(parts: List[str], ext: str) -> str | None:
    normalized_parts = [normalize_text(part) for part in parts]
    for key, allowed_exts in EXTENSION_MAP.items():
        normalized_key = normalize_text(key)
        if any(normalized_key in part for part in normalized_parts):
            return key if ext in allowed_exts else None
    return "other" if ext in GLOBAL_MEDIA_EXTS else None


def action_for_age(age_days: int, cfg: Dict) -> str:
    keep_d = int(cfg["age_keep_days"])
    trash_min = int(cfg["age_trash_min"])
    trash_max = int(cfg["age_trash_max"])
    if age_days <= keep_d:
        return "keep"
    if trash_min <= age_days <= trash_max:
        return "trash"
    return "delete"


def scan_files(media_base: str, cfg: Dict) -> Tuple[List[FileRecord], Dict]:
    now = time.time()
    records: List[FileRecord] = []
    summary = {
        "total_files": 0,
        "total_size": 0,
        "ignored_files": 0,
        "permission_errors": 0,
        "by_action": {key: {"count": 0, "size": 0} for key in ACTION_LABEL_KEYS},
        "by_media": {},
    }

    for root, dirs, files in os.walk(media_base):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in files:
            path = os.path.join(root, filename)
            name = filename.lower()
            if name in EXCLUDE_NAMES or name.startswith("."):
                summary["ignored_files"] += 1
                continue

            try:
                stat = os.stat(path)
            except FileNotFoundError:
                continue
            except PermissionError:
                summary["permission_errors"] += 1
                continue

            rel_path = get_relative_path(path, media_base)
            parts = [part.lower() for part in Path(rel_path).parts]
            ext = Path(filename).suffix.lower().lstrip(".")
            media_type = detect_media_type(parts, ext)
            if media_type is None:
                summary["ignored_files"] += 1
                continue

            if not cfg.get("include_private", False) and "private" in parts:
                summary["ignored_files"] += 1
                continue
            if not cfg.get("include_sent", True) and "sent" in parts:
                summary["ignored_files"] += 1
                continue

            age_days = int((now - stat.st_mtime) / 86400)
            action = action_for_age(age_days, cfg)
            record = FileRecord(
                src=path,
                rel_path=rel_path,
                size=stat.st_size,
                mtime=stat.st_mtime,
                age_days=age_days,
                action=action,
                media_type=media_type,
            )
            records.append(record)

            summary["total_files"] += 1
            summary["total_size"] += stat.st_size
            summary["by_action"][action]["count"] += 1
            summary["by_action"][action]["size"] += stat.st_size
            media_bucket = summary["by_media"].setdefault(media_type, {"count": 0, "size": 0})
            media_bucket["count"] += 1
            media_bucket["size"] += stat.st_size

    return records, summary


def print_config_summary(cfg: Dict) -> None:
    print(t("current_config"))
    print(f"  {t('folder')}: {cfg['media_base']}")
    print(f"  {t('keep')}: {t('until_days', days=cfg['age_keep_days'])}")
    print(f"  {t('trash_range', min_days=cfg['age_trash_min'], max_days=cfg['age_trash_max'])}")
    print(f"  {t('delete_above', days=cfg['age_trash_max'])}")
    print(f"  {t('include_sent_summary')}: {t('yes') if cfg.get('include_sent') else t('no')}")
    print(f"  {t('include_private_summary')}: {t('yes') if cfg.get('include_private') else t('no')}")
    print(f"  {t('language_summary')}: {LANGUAGES.get(cfg.get('language'), LANGUAGES['en'])}")


def print_report(records: List[FileRecord], summary: Dict, cfg: Dict) -> None:
    header(t("preview_title"))
    print_config_summary(cfg)
    print("\n" + t("summary"))
    print("  " + t("media_analyzed", count=summary["total_files"], size=human_size(summary["total_size"])))
    print("  " + t("ignored", count=summary["ignored_files"]))
    if summary["permission_errors"]:
        print("  " + t("permission_errors", count=summary["permission_errors"]))

    print("\n" + t("what_will_happen"))
    for action, label_key in ACTION_LABEL_KEYS.items():
        bucket = summary["by_action"][action]
        print(f"  {t(label_key)}: {bucket['count']} ({human_size(bucket['size'])})")

    if summary["by_media"]:
        print("\n" + t("by_media_type"))
        for media_type, bucket in sorted(summary["by_media"].items(), key=lambda item: item[1]["size"], reverse=True):
            label = t(MEDIA_LABEL_KEYS.get(media_type, "media_other"))
            print(f"  {label}: {bucket['count']} ({human_size(bucket['size'])})")

    candidates = [r for r in records if r.action in {"trash", "delete"}]
    if candidates:
        print("\n" + t("largest_candidates", count=cfg["show_top_files"]))
        for idx, rec in enumerate(sorted(candidates, key=lambda r: r.size, reverse=True)[: int(cfg["show_top_files"])], start=1):
            action = t(ACTION_LABEL_KEYS[rec.action])
            print(f"  {idx}) {human_size(rec.size)} | {rec.age_days} {t('days_word')} | {action} | {rec.rel_path}")


def make_trash_dir(media_base: str) -> str:
    base_parent = os.path.dirname(media_base)
    timestamp = datetime.now().strftime("clean_whatsapp_trash_%Y%m%d_%H%M%S")
    dst = os.path.join(base_parent, timestamp)
    os.makedirs(dst, exist_ok=True)
    try:
        Path(os.path.join(dst, ".nomedia")).touch(exist_ok=True)
    except Exception:
        pass
    return dst


def write_log(entries: List[Dict], cfg: Dict, moved_count: int, deleted_count: int, total_bytes: int) -> str:
    ensure_dirs()
    log_path = os.path.join(LOGS_DIR, datetime.now().strftime("log_%Y%m%d_%H%M%S.json"))
    meta = {
        "timestamp": datetime.now().isoformat(),
        "media_base": cfg["media_base"],
        "cfg": cfg,
        "summary": {
            "moved_count": moved_count,
            "deleted_count": deleted_count,
            "bytes_processed": total_bytes,
        },
    }
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "entries": entries}, f, indent=2, ensure_ascii=False)
    return log_path


def perform_actions(records: List[FileRecord], cfg: Dict, apply_moves: bool, apply_deletes: bool) -> str:
    actionable = [r for r in records if (r.action == "trash" and apply_moves) or (r.action == "delete" and apply_deletes)]
    if not actionable:
        print("\n" + t("no_changes"))
        return ""

    trash_dir = None
    if apply_moves and any(r.action == "trash" for r in actionable):
        trash_dir = make_trash_dir(cfg["media_base"])

    log_entries = []
    moved_count = 0
    deleted_count = 0
    total_bytes = 0

    for rec in actionable:
        if rec.action == "trash":
            assert trash_dir is not None
            dst = os.path.join(trash_dir, rec.rel_path)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                shutil.move(rec.src, dst)
                moved_count += 1
                total_bytes += rec.size
                log_entries.append({"src": rec.src, "dst": dst, "planned_dst": dst, "action": "move", "size": rec.size, "mtime": rec.mtime, "error": None})
            except Exception as exc:
                print(t("move_failed", path=rec.rel_path, error=exc))
                log_entries.append({"src": rec.src, "dst": None, "planned_dst": dst, "action": "move", "size": rec.size, "mtime": rec.mtime, "error": str(exc)})

        elif rec.action == "delete":
            try:
                os.remove(rec.src)
                deleted_count += 1
                total_bytes += rec.size
                log_entries.append({"src": rec.src, "dst": None, "planned_dst": None, "action": "delete", "size": rec.size, "mtime": rec.mtime, "error": None})
            except Exception as exc:
                print(t("delete_failed", path=rec.rel_path, error=exc))
                log_entries.append({"src": rec.src, "dst": None, "planned_dst": None, "action": "delete", "size": rec.size, "mtime": rec.mtime, "error": str(exc)})

    log_path = write_log(log_entries, cfg, moved_count, deleted_count, total_bytes)
    print("\n" + t("cleanup_done"))
    print("  " + t("moved_count", count=moved_count))
    print("  " + t("deleted_count", count=deleted_count))
    print("  " + t("processed_space", size=human_size(total_bytes)))
    print("  " + t("operation_record", path=log_path))
    return log_path


def run_cleanup_flow(cfg: Dict) -> None:
    header(t("cleanup_title"))
    ok, reason = check_storage_access(cfg["media_base"])
    if not ok:
        explain_storage_fix(cfg["media_base"], reason)
        pause()
        return

    print(t("scanning"))
    records, summary = scan_files(cfg["media_base"], cfg)
    print_report(records, summary, cfg)

    trash_bucket = summary["by_action"]["trash"]
    delete_bucket = summary["by_action"]["delete"]
    if trash_bucket["count"] == 0 and delete_bucket["count"] == 0:
        print("\n" + t("nothing_to_clean"))
        pause()
        return

    print("\n" + t("preview_only"))
    if not prompt_yes_no(t("apply_cleanup"), default_yes=False):
        return

    apply_moves = False
    apply_deletes = False
    if trash_bucket["count"]:
        apply_moves = prompt_yes_no(t("move_to_trash", count=trash_bucket["count"], size=human_size(trash_bucket["size"])), default_yes=True)
    if delete_bucket["count"]:
        wants_delete = prompt_yes_no(t("also_delete", count=delete_bucket["count"], size=human_size(delete_bucket["size"])), default_yes=False)
        if wants_delete:
            apply_deletes = strong_confirm(t("delete_warning"), word=t("delete_word"))

    perform_actions(records, cfg, apply_moves, apply_deletes)
    pause()


def list_available_logs() -> List[str]:
    try:
        files = [os.path.join(LOGS_DIR, name) for name in os.listdir(LOGS_DIR) if name.endswith(".json")]
    except FileNotFoundError:
        return []
    return sorted(files, reverse=True)


def preview_restore_from_log(log_path: str) -> Tuple[List[Dict], List[Dict]]:
    with open(log_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    restorable = []
    skipped = []
    for entry in data.get("entries", []):
        reason = None
        if entry.get("error"):
            reason = t("restore_reason_error")
        if entry.get("action") != "move":
            reason = reason or t("restore_reason_deleted")

        actual_src = entry.get("dst") or entry.get("planned_dst")
        restore_to = entry.get("src")
        if not actual_src or not restore_to:
            reason = reason or t("restore_reason_incomplete")
        elif not os.path.exists(actual_src):
            reason = reason or t("restore_reason_missing")

        if reason:
            skipped.append({"entry": entry, "reason": reason})
        else:
            restorable.append({"entry": entry, "current_location": actual_src, "restore_to": restore_to})
    return restorable, skipped


def restore_from_log(log_path: str) -> None:
    restorable, skipped = preview_restore_from_log(log_path)
    header(t("restore_preview_title"))
    print(t("can_restore", count=len(restorable)))
    print(t("cannot_restore", count=len(skipped)))

    for idx, item in enumerate(restorable[:20], start=1):
        entry = item["entry"]
        print(f"  {idx}) {human_size(entry.get('size', 0))} | {item['restore_to']}")
    if len(restorable) > 20:
        print("  " + t("more_files", count=len(restorable) - 20))

    if skipped:
        print("\n" + t("skipped_items"))
        for item in skipped[:10]:
            print(f"  - {item['entry'].get('src')} ({item['reason']})")

    if not restorable:
        pause()
        return
    if not prompt_yes_no(t("restore_now"), default_yes=False):
        return

    restored = 0
    for item in restorable:
        src = item["current_location"]
        dst = item["restore_to"]
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.move(src, dst)
            restored += 1
        except Exception as exc:
            print(t("restore_failed", path=dst, error=exc))
    print("\n" + t("restored_count", count=restored))
    pause()


def run_restore_flow() -> None:
    header(t("restore_title"))
    logs = list_available_logs()
    if not logs:
        print(t("no_records"))
        pause()
        return

    for idx, path in enumerate(logs[:20], start=1):
        print(f"{idx}) {os.path.basename(path)}")
    print(f"0) {t('back')}")

    choice = prompt_int(t("choose_record"), 1, 0)
    if choice == 0:
        return
    if choice < 1 or choice > min(len(logs), 20):
        print(t("invalid_option"))
        pause()
        return
    restore_from_log(logs[choice - 1])


def run_settings_flow(cfg: Dict) -> None:
    while True:
        header(t("settings_title"))
        print_config_summary(cfg)
        print(f"\n1) {t('menu_profile')}")
        print(f"2) {t('menu_ages')}")
        print(f"3) {t('menu_folders')}")
        print(f"4) {t('menu_path')}")
        print(f"5) {t('menu_language')}")
        print(f"6) {t('menu_setup')}")
        print(f"0) {t('back')}")

        choice = prompt_choice(t("choose"), {"0", "1", "2", "3", "4", "5", "6"}, "0")
        if choice == "0":
            return
        if choice == "1":
            configure_preset_or_custom(cfg)
        elif choice == "2":
            configure_custom_ages(cfg)
        elif choice == "3":
            configure_included_folders(cfg)
        elif choice == "4":
            configure_media_path(cfg)
        elif choice == "5":
            select_language(cfg)
        elif choice == "6":
            setup_wizard(cfg)


def show_help() -> None:
    header(t("help_title"))
    print(t("help_1"))
    print(t("help_2"))
    print(t("help_3"))
    print(t("help_4"))
    print(t("help_5"))
    pause()


def main_menu() -> None:
    cfg = load_config()
    ensure_dirs()
    set_language(cfg.get("language"))
    if cfg.get("language") not in LANGUAGES:
        select_language(cfg)
    if not cfg.get("setup_complete"):
        setup_wizard(cfg)

    while True:
        header(t("app_title"))
        print_config_summary(cfg)
        print(f"\n1) {t('menu_analyze')}")
        print(f"2) {t('menu_settings')}")
        print(f"3) {t('menu_restore')}")
        print(f"4) {t('menu_help')}")
        print(f"0) {t('menu_exit')}")

        choice = prompt_choice(t("choose"), {"0", "1", "2", "3", "4"}, "1")
        if choice == "1":
            run_cleanup_flow(cfg)
        elif choice == "2":
            run_settings_flow(cfg)
        elif choice == "3":
            run_restore_flow()
        elif choice == "4":
            show_help()
        elif choice == "0":
            print(t("exiting"))
            return


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n" + t("interrupted"))
