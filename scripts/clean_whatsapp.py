#!/usr/bin/env python3
"""
Limpador de mídia do WhatsApp para Termux.

O foco deste script é ser seguro e compreensível para usuários que não estão
acostumados com terminal: ele sempre mostra uma prévia antes de alterar
arquivos, usa perfis de limpeza e mantém registros para restauração dos itens
movidos para a lixeira.
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
        "Este app precisa de Python 3.10 ou mais novo.\n"
        "No Termux, rode: pkg install python\n"
    )
    sys.exit(1)


KNOWN_MEDIA_BASES = [
    "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media",
    "/storage/emulated/0/Android/media/com.whatsapp.w4b/WhatsApp Business/Media",
    "/storage/emulated/0/WhatsApp/Media",
]

CONFIG_PATH = os.path.expanduser("~/.config/whatsapp_clean/config.json")
LOGS_DIR = os.path.expanduser("~/.local/share/whatsapp_clean/logs")

DEFAULTS = {
    "media_base": KNOWN_MEDIA_BASES[0],
    "age_keep_days": 60,
    "age_trash_min": 61,
    "age_trash_max": 180,
    "include_private": False,
    "include_sent": True,
    "show_top_files": 10,
    "setup_complete": False,
}

PRESETS = {
    "1": {
        "name": "Seguro",
        "description": "mantém 60 dias, move de 61 a 180 dias para a lixeira e só sugere apagar acima de 180 dias",
        "age_keep_days": 60,
        "age_trash_min": 61,
        "age_trash_max": 180,
    },
    "2": {
        "name": "Equilibrado",
        "description": "mantém 30 dias, move de 31 a 90 dias para a lixeira e só sugere apagar acima de 90 dias",
        "age_keep_days": 30,
        "age_trash_min": 31,
        "age_trash_max": 90,
    },
    "3": {
        "name": "Liberar mais espaço",
        "description": "mantém 14 dias, move de 15 a 45 dias para a lixeira e só sugere apagar acima de 45 dias",
        "age_keep_days": 14,
        "age_trash_min": 15,
        "age_trash_max": 45,
    },
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

MEDIA_LABELS = {
    "images": "Imagens",
    "animated_gifs": "GIFs",
    "video": "Vídeos",
    "audio": "Áudios",
    "voice": "Mensagens de voz",
    "stickers": "Figurinhas",
    "profile": "Fotos de perfil",
    "other": "Outras mídias",
}

ACTION_LABELS = {
    "keep": "Manter",
    "trash": "Mover para lixeira",
    "delete": "Apagar definitivamente",
}

GLOBAL_MEDIA_EXTS = set().union(*EXTENSION_MAP.values())
EXCLUDE_NAMES = {".nomedia", "desktop.ini", "thumbs.db"}


@dataclass
class FileRecord:
    src: str
    rel_path: str
    size: int
    mtime: float
    age_days: int
    action: str
    media_type: str


def ensure_dirs() -> None:
    Path(CONFIG_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)


def load_config() -> Dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        cfg = {}
    except json.JSONDecodeError:
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
    input("\nPressione Enter para continuar...")


def prompt_yes_no(msg: str, default_yes: bool = True) -> bool:
    suffix = "S/n" if default_yes else "s/N"
    while True:
        ans = input(f"{msg} [{suffix}]: ").strip().lower()
        if ans == "":
            return default_yes
        if ans in ("s", "sim", "y", "yes"):
            return True
        if ans in ("n", "nao", "não", "no"):
            return False
        print("Responda com S para sim ou N para não.")


def prompt_choice(msg: str, choices: Iterable[str], default: str) -> str:
    valid = set(choices)
    while True:
        ans = input(f"{msg} [{default}]: ").strip() or default
        if ans in valid:
            return ans
        print("Opção inválida. Escolha uma das opções mostradas.")


def prompt_int(msg: str, default: int, min_value: int = 0) -> int:
    while True:
        raw = input(f"{msg} [{default}]: ").strip()
        if raw == "":
            return default
        try:
            value = int(raw)
        except ValueError:
            print("Digite um número inteiro.")
            continue
        if value < min_value:
            print(f"Digite um número maior ou igual a {min_value}.")
            continue
        return value


def strong_confirm(msg: str, word: str = "APAGAR") -> bool:
    print("\n" + msg)
    print(f"Para confirmar, digite exatamente: {word}")
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


def detect_media_base(current: str | None = None) -> str:
    if current and os.path.exists(current):
        return current
    for path in KNOWN_MEDIA_BASES:
        if os.path.exists(path):
            return path
    return current or KNOWN_MEDIA_BASES[0]


def check_storage_access(media_base: str) -> Tuple[bool, str]:
    if not os.path.exists(media_base):
        return False, f"Pasta não encontrada: {media_base}"
    try:
        os.listdir(media_base)
    except PermissionError:
        return False, "Permissão negada ao acessar a pasta."
    except Exception as exc:
        return False, f"Erro ao acessar a pasta: {exc}"
    return True, "OK"


def explain_storage_fix(media_base: str, reason: str) -> None:
    header("Permissão ou pasta não encontrada")
    print(reason)
    print("\nNo Termux, normalmente você precisa rodar este comando uma vez:")
    print("  termux-setup-storage")
    print("\nDepois feche e abra o Termux novamente, se necessário.")
    print("\nPasta configurada:")
    print(f"  {media_base}")
    print("\nSe o seu WhatsApp usa outra pasta, altere em Configurações > Caminho da pasta.")


def configure_media_path(cfg: Dict) -> None:
    header("Caminho da pasta de mídia")
    detected = detect_media_base(cfg.get("media_base"))
    default_choice = "1"
    if detected in KNOWN_MEDIA_BASES:
        default_choice = str(KNOWN_MEDIA_BASES.index(detected) + 1)
    print("O app vai procurar mídias dentro desta pasta:")
    print(f"  {detected}")
    print("\nPastas comuns detectadas:")
    for idx, path in enumerate(KNOWN_MEDIA_BASES, start=1):
        marker = "existe" if os.path.exists(path) else "não encontrada"
        print(f"{idx}) {path} ({marker})")
    print("4) Digitar outro caminho")

    choice = prompt_choice("Escolha a pasta", {"1", "2", "3", "4"}, default_choice)
    if choice in {"1", "2", "3"}:
        cfg["media_base"] = KNOWN_MEDIA_BASES[int(choice) - 1]
    else:
        custom = input("Cole o caminho completo da pasta de mídia do WhatsApp: ").strip()
        if custom:
            cfg["media_base"] = custom
    save_config(cfg)


def apply_preset(cfg: Dict, key: str) -> None:
    preset = PRESETS[key]
    cfg["age_keep_days"] = preset["age_keep_days"]
    cfg["age_trash_min"] = preset["age_trash_min"]
    cfg["age_trash_max"] = preset["age_trash_max"]


def configure_custom_ages(cfg: Dict) -> None:
    header("Idades personalizadas")
    print("Use números em dias. Exemplo: manter até 30 dias, mover de 31 a 90 dias para a lixeira e apagar acima de 90 dias.")
    while True:
        keep = prompt_int("Manter arquivos com até quantos dias", int(cfg["age_keep_days"]), 0)
        trash_min = prompt_int("Mover para lixeira a partir de quantos dias", int(cfg["age_trash_min"]), keep + 1)
        trash_max = prompt_int("Mover para lixeira até quantos dias", int(cfg["age_trash_max"]), trash_min)
        if keep < trash_min <= trash_max:
            cfg["age_keep_days"] = keep
            cfg["age_trash_min"] = trash_min
            cfg["age_trash_max"] = trash_max
            save_config(cfg)
            return
        print("A ordem precisa ser: manter primeiro, depois mover para a lixeira, depois apagar definitivamente.")


def configure_preset_or_custom(cfg: Dict) -> None:
    header("Regras de limpeza")
    print("Escolha um perfil de limpeza. Você sempre verá uma prévia antes de qualquer alteração.\n")
    for key, preset in PRESETS.items():
        extra = " (recomendado)" if key == "1" else ""
        print(f"{key}) {preset['name']}{extra}: {preset['description']}")
    print("4) Personalizado")

    choice = prompt_choice("Escolha", {"1", "2", "3", "4"}, "1")
    if choice == "4":
        configure_custom_ages(cfg)
    else:
        apply_preset(cfg, choice)
        save_config(cfg)


def configure_included_folders(cfg: Dict) -> None:
    header("Pastas incluídas")
    print("A pasta 'Sent' guarda mídias que você enviou para outras pessoas.")
    cfg["include_sent"] = prompt_yes_no("Incluir mídias enviadas", bool(cfg["include_sent"]))
    print("\nA pasta 'Private' costuma guardar mídias ocultas da galeria. Por segurança, o padrão é não incluir.")
    cfg["include_private"] = prompt_yes_no("Incluir mídias ocultas", bool(cfg["include_private"]))
    cfg["show_top_files"] = prompt_int("Quantos arquivos grandes mostrar na prévia", int(cfg["show_top_files"]), 1)
    save_config(cfg)


def setup_wizard(cfg: Dict) -> None:
    header("Primeira configuração")
    print("Este app ajuda a liberar espaço apagando ou movendo mídias antigas do WhatsApp.")
    print("Nada será alterado sem uma prévia e uma confirmação sua.")

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
        "by_action": {key: {"count": 0, "size": 0} for key in ACTION_LABELS},
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
    print("Configuração atual:")
    print(f"  Pasta: {cfg['media_base']}")
    print(f"  Manter: até {cfg['age_keep_days']} dias")
    print(f"  Mover para lixeira: {cfg['age_trash_min']} a {cfg['age_trash_max']} dias")
    print(f"  Sugerir apagar: acima de {cfg['age_trash_max']} dias")
    print(f"  Incluir mídias enviadas: {'sim' if cfg.get('include_sent') else 'não'}")
    print(f"  Incluir mídias ocultas: {'sim' if cfg.get('include_private') else 'não'}")


def print_report(records: List[FileRecord], summary: Dict, cfg: Dict) -> None:
    header("Prévia da limpeza")
    print_config_summary(cfg)
    print("\nResumo:")
    print(f"  Mídias analisadas: {summary['total_files']} ({human_size(summary['total_size'])})")
    print(f"  Não incluídas por segurança ou configuração: {summary['ignored_files']}")
    if summary["permission_errors"]:
        print(f"  Arquivos sem permissão de leitura: {summary['permission_errors']}")

    print("\nO que será feito:")
    for action, label in ACTION_LABELS.items():
        bucket = summary["by_action"][action]
        print(f"  {label}: {bucket['count']} arquivos ({human_size(bucket['size'])})")

    if summary["by_media"]:
        print("\nPor tipo de mídia:")
        for media_type, bucket in sorted(summary["by_media"].items(), key=lambda item: item[1]["size"], reverse=True):
            label = MEDIA_LABELS.get(media_type, media_type)
            print(f"  {label}: {bucket['count']} arquivos ({human_size(bucket['size'])})")

    candidates = [r for r in records if r.action in {"trash", "delete"}]
    if candidates:
        print(f"\nArquivos maiores que podem ser limpos (mostrando {cfg['show_top_files']}):")
        for idx, rec in enumerate(sorted(candidates, key=lambda r: r.size, reverse=True)[: int(cfg["show_top_files"])], start=1):
            action = ACTION_LABELS[rec.action]
            print(f"  {idx}) {human_size(rec.size)} | {rec.age_days} dias | {action} | {rec.rel_path}")


def make_trash_dir(media_base: str) -> str:
    base_parent = os.path.dirname(media_base)
    timestamp = datetime.now().strftime("whatsapp_clean_trash_%Y%m%d_%H%M%S")
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
        print("\nNenhuma alteração foi aplicada.")
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
                log_entries.append(
                    {
                        "src": rec.src,
                        "dst": dst,
                        "planned_dst": dst,
                        "action": "move",
                        "size": rec.size,
                        "mtime": rec.mtime,
                        "error": None,
                    }
                )
            except Exception as exc:
                print(f"Falha ao mover: {rec.rel_path} -> {exc}")
                log_entries.append(
                    {
                        "src": rec.src,
                        "dst": None,
                        "planned_dst": dst,
                        "action": "move",
                        "size": rec.size,
                        "mtime": rec.mtime,
                        "error": str(exc),
                    }
                )

        elif rec.action == "delete":
            try:
                os.remove(rec.src)
                deleted_count += 1
                total_bytes += rec.size
                log_entries.append(
                    {
                        "src": rec.src,
                        "dst": None,
                        "planned_dst": None,
                        "action": "delete",
                        "size": rec.size,
                        "mtime": rec.mtime,
                        "error": None,
                    }
                )
            except Exception as exc:
                print(f"Falha ao apagar: {rec.rel_path} -> {exc}")
                log_entries.append(
                    {
                        "src": rec.src,
                        "dst": None,
                        "planned_dst": None,
                        "action": "delete",
                        "size": rec.size,
                        "mtime": rec.mtime,
                        "error": str(exc),
                    }
                )

    log_path = write_log(log_entries, cfg, moved_count, deleted_count, total_bytes)
    print("\nLimpeza concluída.")
    print(f"  Movidos para lixeira: {moved_count}")
    print(f"  Apagados definitivamente: {deleted_count}")
    print(f"  Espaço processado: {human_size(total_bytes)}")
    print(f"  Registro da operação: {log_path}")
    return log_path


def run_cleanup_flow(cfg: Dict) -> None:
    header("Analisar e limpar")
    ok, reason = check_storage_access(cfg["media_base"])
    if not ok:
        explain_storage_fix(cfg["media_base"], reason)
        pause()
        return

    print("Analisando arquivos. Em celulares com muita mídia, isso pode levar alguns minutos...")
    records, summary = scan_files(cfg["media_base"], cfg)
    print_report(records, summary, cfg)

    trash_bucket = summary["by_action"]["trash"]
    delete_bucket = summary["by_action"]["delete"]
    if trash_bucket["count"] == 0 and delete_bucket["count"] == 0:
        print("\nNada antigo o suficiente para limpar com as regras atuais.")
        pause()
        return

    print("\nEsta foi apenas a prévia. Nenhum arquivo foi alterado ainda.")
    if not prompt_yes_no("Deseja aplicar alguma limpeza agora", default_yes=False):
        return

    apply_moves = False
    apply_deletes = False
    if trash_bucket["count"]:
        apply_moves = prompt_yes_no(
            f"Mover {trash_bucket['count']} arquivos ({human_size(trash_bucket['size'])}) para a lixeira",
            default_yes=True,
        )
    if delete_bucket["count"]:
        wants_delete = prompt_yes_no(
            f"Também apagar definitivamente {delete_bucket['count']} arquivos ({human_size(delete_bucket['size'])})",
            default_yes=False,
        )
        if wants_delete:
            apply_deletes = strong_confirm(
                "Apagar definitivamente não pode ser desfeito por este app. "
                "Arquivos movidos para a lixeira podem ser restaurados; arquivos apagados não.",
                word="APAGAR",
            )

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
            reason = "erro registrado na operação"
        if entry.get("action") != "move":
            reason = reason or "arquivo apagado definitivamente"

        actual_src = entry.get("dst") or entry.get("planned_dst")
        restore_to = entry.get("src")
        if not actual_src or not restore_to:
            reason = reason or "entrada incompleta"
        elif not os.path.exists(actual_src):
            reason = reason or "arquivo não encontrado na lixeira"

        if reason:
            skipped.append({"entry": entry, "reason": reason})
        else:
            restorable.append({"entry": entry, "current_location": actual_src, "restore_to": restore_to})
    return restorable, skipped


def restore_from_log(log_path: str) -> None:
    restorable, skipped = preview_restore_from_log(log_path)
    header("Prévia de restauração")
    print(f"Podem ser restaurados: {len(restorable)}")
    print(f"Não podem ser restaurados: {len(skipped)}")

    for idx, item in enumerate(restorable[:20], start=1):
        entry = item["entry"]
        print(f"  {idx}) {human_size(entry.get('size', 0))} | {item['restore_to']}")
    if len(restorable) > 20:
        print(f"  ... e mais {len(restorable) - 20} arquivos")

    if skipped:
        print("\nItens que não serão restaurados:")
        for item in skipped[:10]:
            print(f"  - {item['entry'].get('src')} ({item['reason']})")

    if not restorable:
        pause()
        return
    if not prompt_yes_no("Restaurar estes arquivos agora", default_yes=False):
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
            print(f"Falha ao restaurar {dst}: {exc}")
    print(f"\nArquivos restaurados: {restored}")
    pause()


def run_restore_flow() -> None:
    header("Restaurar arquivos")
    logs = list_available_logs()
    if not logs:
        print("Nenhum registro de limpeza encontrado.")
        pause()
        return

    for idx, path in enumerate(logs[:20], start=1):
        print(f"{idx}) {os.path.basename(path)}")
    print("0) Voltar")

    choice = prompt_int("Escolha um registro", 1, 0)
    if choice == 0:
        return
    if choice < 1 or choice > min(len(logs), 20):
        print("Opção inválida.")
        pause()
        return
    restore_from_log(logs[choice - 1])


def run_settings_flow(cfg: Dict) -> None:
    while True:
        header("Configurações")
        print_config_summary(cfg)
        print("\n1) Usar perfil de limpeza")
        print("2) Editar idades manualmente")
        print("3) Escolher pastas incluídas")
        print("4) Alterar caminho do WhatsApp")
        print("5) Refazer assistente inicial")
        print("0) Voltar")

        choice = prompt_choice("Escolha", {"0", "1", "2", "3", "4", "5"}, "0")
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
            setup_wizard(cfg)


def show_help() -> None:
    header("Ajuda rápida")
    print("1. Primeiro use 'Analisar e limpar' para ver a prévia.")
    print("2. Arquivos em 'Mover para lixeira' saem da pasta do WhatsApp, mas podem ser restaurados pelo menu.")
    print("3. Arquivos em 'Apagar definitivamente' só são removidos se você digitar APAGAR.")
    print("4. Para ser mais conservador, escolha o perfil Seguro em Configurações.")
    print("5. Se aparecer permissão negada, rode no Termux: termux-setup-storage")
    pause()


def main_menu() -> None:
    cfg = load_config()
    ensure_dirs()
    if not cfg.get("setup_complete"):
        setup_wizard(cfg)

    while True:
        header("Limpador de mídia do WhatsApp")
        print_config_summary(cfg)
        print("\n1) Analisar e limpar")
        print("2) Configurações")
        print("3) Restaurar arquivos da lixeira")
        print("4) Ajuda")
        print("0) Sair")

        choice = prompt_choice("Escolha", {"0", "1", "2", "3", "4"}, "1")
        if choice == "1":
            run_cleanup_flow(cfg)
        elif choice == "2":
            run_settings_flow(cfg)
        elif choice == "3":
            run_restore_flow()
        elif choice == "4":
            show_help()
        elif choice == "0":
            print("Saindo.")
            return


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nInterrompido.")
