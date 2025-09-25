#!/usr/bin/env python3
"""
Interactive Termux-friendly WhatsApp media cleaner skeleton.

Features implemented here (skeleton):
- First-run storage permission check + persist to config
- Scan WhatsApp Media folder and classify files by age (days)
- Report counts and sizes per action (keep/move/delete)
- Dry-run default; apply changes only after confirmation
- Move files to a timestamped trash folder when moving
- Write a JSON log for moved/deleted files to allow restore
- Restore stub that can move files back using a log

This is a conservative skeleton focused on clarity and safety.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple


# Enforce minimum Python version used by this script
if sys.version_info < (3, 10):
    sys.stderr.write(
        "This script requires Python 3.10 or newer.\nPlease install a newer Python or run the script in Termux with Python 3.10+.\n"
    )
    sys.exit(1)


MEDIA_BASE = '/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media'
CONFIG_PATH = os.path.expanduser('~/.config/whatsapp_clean/config.json')
LOGS_DIR = os.path.expanduser('~/.local/share/whatsapp_clean/logs')

# Defaults; can be overridden in config.json
DEFAULTS = {
    'age_keep_days': 30,
    'age_trash_min': 31,
    'age_trash_max': 60,
    'auto_prune': False,
    'include_private': False,
    'include_sent': True,
}

# Files and extensions policy
# Map folder keywords to allowed extensions (lowercase, without dot)
EXTENSION_MAP = {
    'images': {'jpg', 'jpeg', 'png', 'webp', 'heic'},
    'animated_gifs': {'gif'},
    'video': {'mp4', 'mkv', 'mov', '3gp', 'avi'},
    'audio': {'mp3', 'm4a', 'opus', 'ogg', 'amr'},
    'voice': {'opus', 'm4a', 'amr'},
    'stickers': {'webp'},
    'profile': {'jpg', 'jpeg', 'png', 'webp'},
}

# Global accepted media extensions if folder is unrecognized
GLOBAL_MEDIA_EXTS = set().union(*EXTENSION_MAP.values())

# Names to never touch
EXCLUDE_NAMES = {'.nomedia', 'desktop.ini', 'thumbs.db'}


@dataclass
class FileRecord:
    src: str
    dst: str | None
    size: int
    mtime: float


def ensure_dirs():
    Path(CONFIG_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)


def load_config() -> Dict:
    cfg = {}
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    except FileNotFoundError:
        cfg = {}
    # Ensure defaults are present
    for k, v in DEFAULTS.items():
        if k not in cfg:
            cfg[k] = v
    if 'has_storage_permission' not in cfg:
        cfg['has_storage_permission'] = None
    return cfg


def save_config(cfg: Dict):
    ensure_dirs()
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)


def check_storage_access() -> Tuple[bool, str]:
    """Return (accessible, message)."""
    if not os.path.exists(MEDIA_BASE):
        return False, f"Path does not exist: {MEDIA_BASE}"
    try:
        # quick read access test
        _ = os.listdir(MEDIA_BASE)
        return True, "OK"
    except PermissionError:
        return False, "Permission denied when accessing storage."
    except Exception as e:
        return False, f"Error accessing storage: {e}"


def prompt_yes_no(msg: str, default_yes: bool = True) -> bool:
    yes = 'S' if default_yes else 's'
    no = 'N' if default_yes else 'n'
    prompt = f"{msg} [{yes}/{no}]: "
    while True:
        ans = input(prompt).strip()
        if ans == '' and default_yes:
            return True
        if ans == '' and not default_yes:
            return False
        if ans.lower() in ('s', 'sim'):
            return True
        if ans.lower() in ('n', 'no', 'nao', 'não'):
            return False


def strong_confirm(msg: str) -> bool:
    print(msg)
    print("Type YES to confirm:")
    ans = input('> ').strip()
    return ans == 'YES'


def first_run_permission_check(cfg: Dict) -> Dict:
    # Only skip check if we previously recorded True.
    if cfg.get('has_storage_permission') is True:
        return cfg

    print('Esta ferramenta precisa de acesso à pasta de mídia do WhatsApp dentro do Termux.')
    ok, reason = check_storage_access()
    if ok:
        print('Acesso ao armazenamento disponível.')
        cfg['has_storage_permission'] = True
        save_config(cfg)
        return cfg

    print('Falha ao acessar o armazenamento:', reason)
    print('Se estiver usando Termux, conceda acesso executando:')
    print('  termux-setup-storage')
    print('Em seguida, execute este script novamente.')
    # perguntar se o usuário já concedeu permissão e deseja continuar
    got_perm = prompt_yes_no('Você já concedeu permissão de armazenamento?', default_yes=False)
    if got_perm:
        ok2, reason2 = check_storage_access()
        if ok2:
            cfg['has_storage_permission'] = True
            save_config(cfg)
            return cfg
        else:
            print('Ainda não é possível acessar o armazenamento:', reason2)
    print('Encerrando até que a permissão de armazenamento esteja disponível.')
    sys.exit(1)


def scan_files(base: str, include_private: bool = False, include_sent: bool = True, cfg: Dict | None = None) -> Tuple[List[FileRecord], Dict[str, int]]:
    now = time.time()
    keep: List[FileRecord] = []
    trash_candidates: List[FileRecord] = []
    delete_candidates: List[FileRecord] = []
    summary = {'total_files': 0, 'total_size': 0, 'ignored_files': 0}

    # Load limits from config or defaults
    if cfg is None:
        cfg = load_config()
    keep_d = cfg.get('age_keep_days', DEFAULTS['age_keep_days'])
    trash_min = cfg.get('age_trash_min', DEFAULTS['age_trash_min'])
    trash_max = cfg.get('age_trash_max', DEFAULTS['age_trash_max'])

    base_path = Path(base)
    for root, dirs, files in os.walk(base):
        for fn in files:
            path = os.path.join(root, fn)
            try:
                st = os.stat(path)
            except FileNotFoundError:
                continue
            except PermissionError:
                # skip files we can't access
                continue

            age_days = int((now - st.st_mtime) / 86400)
            rec = FileRecord(src=path, dst=None, size=st.st_size, mtime=st.st_mtime)
            summary['total_files'] += 1
            summary['total_size'] += st.st_size

            # normalize path parts for folder-based filters
            rel = Path(path).relative_to(base_path) if base_path in Path(path).parents or Path(path) == base_path else Path(path)
            parts = [p.lower() for p in rel.parts]
            # Exclude certain filenames explicitly
            name = Path(path).name.lower()
            if name in EXCLUDE_NAMES or name.startswith('.'):
                summary['ignored_files'] += 1
                continue

            # Extension whitelist: only consider known media extensions
            ext = Path(path).suffix.lower().lstrip('.')
            if ext == '':
                summary['ignored_files'] += 1
                continue

            # Determine folder-based extension policy if possible
            # Find a matching folder key from path parts (use EXTENSION_MAP keys)
            # Melhor: detectar por substring em cada parte (ex.: "WhatsApp Images" contém "images")
            folder_key = None
            for k in EXTENSION_MAP.keys():
                found = False
                for p in parts:
                    # normalize and check if the folder key appears as a whole or as substring
                    if k == p or k in p:
                        found = True
                        break
                if found:
                    folder_key = k
                    break

            allowed_exts = None
            if folder_key:
                allowed_exts = EXTENSION_MAP.get(folder_key, set())
            else:
                # No recognized folder key; fall back to global media extensions
                allowed_exts = GLOBAL_MEDIA_EXTS

            if ext not in allowed_exts:
                # extension not allowed for this folder (or not globally recognized)
                summary['ignored_files'] += 1
                continue

            if not include_private and 'private' in parts:
                # treat as keep (skip processing)
                keep.append(rec)
                continue
            if not include_sent and 'sent' in parts:
                keep.append(rec)
                continue

            if age_days <= keep_d:
                keep.append(rec)
            elif trash_min <= age_days <= trash_max:
                trash_candidates.append(rec)
            else:
                delete_candidates.append(rec)

    return keep + trash_candidates + delete_candidates, {'keep': len(keep), 'trash': len(trash_candidates), 'delete': len(delete_candidates), **summary}


def human_size(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}TB"


def make_trash_dir(base_parent: str) -> str:
    ts = datetime.now().strftime('whatsapp_clean_trash_%Y%m%d_%H%M%S')
    dst = os.path.join(base_parent, ts)
    os.makedirs(dst, exist_ok=True)
    return dst


def perform_actions(records: List[FileRecord], dry_run: bool, apply_moves: bool, apply_deletes: bool, cfg: Dict | None = None) -> str:
    """Perform moves/deletes. Returns path to log file."""
    if not records:
        print('No files to act on.')
        return ''

    base_parent = os.path.dirname(MEDIA_BASE)
    trash_dir = make_trash_dir(base_parent)
    log_entries = []

    if cfg is None:
        cfg = load_config()

    keep_d = cfg.get('age_keep_days', DEFAULTS['age_keep_days'])
    trash_min = cfg.get('age_trash_min', DEFAULTS['age_trash_min'])
    trash_max = cfg.get('age_trash_max', DEFAULTS['age_trash_max'])

    moved_count = 0
    deleted_count = 0
    total_bytes = 0

    for rec in records:
        # recompute age to decide action
        age_days = int((time.time() - rec.mtime) / 86400)
        if age_days <= keep_d:
            continue

        rel = os.path.relpath(rec.src, MEDIA_BASE)
        dst = os.path.join(trash_dir, rel)
        dst_dir = os.path.dirname(dst)

        if trash_min <= age_days <= trash_max:
            # move to trash
            if dry_run:
                print(f"DRY MOVE: {rec.src} -> {dst} ({human_size(rec.size)})")
                log_entries.append({'src': rec.src, 'dst': None, 'planned_dst': dst, 'action': 'move', 'size': rec.size, 'mtime': rec.mtime, 'error': None})
                continue
            if apply_moves:
                os.makedirs(dst_dir, exist_ok=True)
                try:
                    shutil.move(rec.src, dst)
                    log_entries.append({'src': rec.src, 'dst': dst, 'planned_dst': dst, 'action': 'move', 'size': rec.size, 'mtime': rec.mtime, 'error': None})
                    moved_count += 1
                    total_bytes += rec.size
                except Exception as e:
                    print('Failed to move', rec.src, '->', e)
                    log_entries.append({'src': rec.src, 'dst': None, 'planned_dst': dst, 'action': 'move', 'size': rec.size, 'mtime': rec.mtime, 'error': str(e)})

        elif age_days > trash_max:
            # candidate for delete (> trash_max)
            if dry_run:
                print(f"DRY DELETE: {rec.src} ({human_size(rec.size)})")
                log_entries.append({'src': rec.src, 'dst': None, 'planned_dst': None, 'action': 'delete', 'size': rec.size, 'mtime': rec.mtime, 'error': None})
                continue
            if apply_deletes:
                try:
                    os.remove(rec.src)
                    log_entries.append({'src': rec.src, 'dst': None, 'planned_dst': None, 'action': 'delete', 'size': rec.size, 'mtime': rec.mtime, 'error': None})
                    deleted_count += 1
                    total_bytes += rec.size
                except Exception as e:
                    print('Failed to delete', rec.src, '->', e)
                    log_entries.append({'src': rec.src, 'dst': None, 'planned_dst': None, 'action': 'delete', 'size': rec.size, 'mtime': rec.mtime, 'error': str(e)})

    # write log
    if log_entries:
        ensure_dirs()
        meta = {
            'timestamp': datetime.now().isoformat(),
            'cfg': cfg,
            'summary': {'moved_count': moved_count, 'deleted_count': deleted_count, 'bytes_processed': total_bytes},
        }
        log_path = os.path.join(LOGS_DIR, datetime.now().strftime('log_%Y%m%d_%H%M%S.json'))
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump({'meta': meta, 'entries': log_entries}, f, indent=2)
        print('Operation log written to', log_path)
        return log_path
    return ''


def restore_from_log(log_path: str):
    print('Restore from log is a best-effort operation.')
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print('Failed to read log:', e)
        return

    entries = data.get('entries', [])
    for entry in entries:
        if entry.get('error'):
            print('Skipping entry with error recorded:', entry.get('src'))
            continue

        # Determine actual source: prefer recorded dst (where file was moved), else planned_dst
        actual_src = entry.get('dst') or entry.get('planned_dst')
        dst = entry.get('src')
        if not actual_src or not dst:
            print('Skipping malformed log entry:', entry)
            continue
        if not os.path.exists(actual_src):
            print('Cannot restore, source missing:', actual_src)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.move(actual_src, dst)
            print('Restored', dst)
        except Exception as e:
            print('Failed restore', actual_src, '->', e)


def list_available_logs() -> List[str]:
    """Return a sorted list of log file paths in LOGS_DIR (most recent first)."""
    try:
        files = [os.path.join(LOGS_DIR, p) for p in os.listdir(LOGS_DIR) if p.endswith('.json')]
    except FileNotFoundError:
        return []
    files.sort(reverse=True)
    return files


def preview_restore_from_log(log_path: str) -> Tuple[List[Dict], List[Dict]]:
    """Return two lists: (restorable_entries, skipped_entries).

    restorable_entries: entries that appear to be recoverable (dst/planned_dst exists and no error)
    skipped_entries: entries that cannot be restored with reasons (missing fields, missing files, error recorded)
    """
    restorable = []
    skipped = []
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        raise

    entries = data.get('entries', [])
    for entry in entries:
        reason = None
        if entry.get('error'):
            reason = 'error_recorded'
        actual_src = entry.get('dst') or entry.get('planned_dst')
        dst = entry.get('src')
        if not actual_src or not dst:
            reason = reason or 'malformed_entry'
        elif not os.path.exists(actual_src):
            reason = reason or 'source_missing'

        if reason:
            skipped.append({'entry': entry, 'reason': reason})
        else:
            restorable.append({'entry': entry, 'current_location': actual_src, 'restore_to': dst})

    return restorable, skipped


def main_menu():
    cfg = load_config()
    ensure_dirs()
    first_run_permission_check(cfg)

    while True:
        print('\nLimpador de Mídia do WhatsApp - Menu')
        print('1) Análise e limpeza (scan → report → aplicar) [recomendada]')
        print('2) Restaurar arquivos a partir de um log')
        print('3) Configurações')
        print('4) Sair')
        choice = input('Escolha uma opção [1]: ').strip() or '1'
        if choice == '1':
            print('Analisando... (pode levar alguns minutos)')
            # Use config defaults as the initial choice
            default_private = bool(cfg.get('include_private', DEFAULTS['include_private']))
            default_sent = bool(cfg.get('include_sent', DEFAULTS['include_sent']))
            include_private = prompt_yes_no('Incluir pastas Private?', default_yes=default_private)
            include_sent = prompt_yes_no('Incluir pastas Sent?', default_yes=default_sent)
            if prompt_yes_no('Salvar estas escolhas como padrão no config?', default_yes=False):
                cfg['include_private'] = include_private
                cfg['include_sent'] = include_sent
                save_config(cfg)
            records, counts = scan_files(MEDIA_BASE, include_private=include_private, include_sent=include_sent, cfg=cfg)
            print('Resumo:', counts)
            total_size = sum(r.size for r in records)
            print(f'Total de arquivos analisados: {len(records)}, tamanho total ~ {human_size(total_size)}')

            dry = prompt_yes_no('Executar em modo simulação (dry-run)? (nenhuma alteração será feita)', default_yes=True)

            apply_moves = False
            apply_deletes = False
            if not dry:
                # load current limits from cfg so prompts reflect actual values
                current_keep = cfg.get('age_keep_days', DEFAULTS['age_keep_days'])
                current_trash_min = cfg.get('age_trash_min', DEFAULTS['age_trash_min'])
                current_trash_max = cfg.get('age_trash_max', DEFAULTS['age_trash_max'])

                apply_moves = prompt_yes_no(f'Aplicar movimentações ({current_trash_min}–{current_trash_max} dias) para a lixeira?', default_yes=True)
                if apply_moves:
                    print('Arquivos em /Private/ exigirão confirmação adicional antes de mover.')
                # deletion requires strong confirmation
                want_delete = prompt_yes_no(f'Também excluir arquivos com mais de {current_trash_max} dias?', default_yes=False)
                if want_delete:
                    ok = strong_confirm(f'Você está prestes a EXCLUIR PERMANENTEMENTE arquivos com mais de {current_trash_max} dias. Isso é irreversível.')
                    apply_deletes = ok

            log = perform_actions(records, dry_run=dry, apply_moves=apply_moves, apply_deletes=apply_deletes, cfg=cfg)
            if log:
                print('Veja o log para detalhes e possíveis instruções de restauração.')

        elif choice == '2':
            print('Logs disponíveis:')
            logs = list_available_logs()
            if not logs:
                print('Nenhum log encontrado em', LOGS_DIR)
                continue
            for i, p in enumerate(logs, start=1):
                print(f"{i}) {os.path.basename(p)}  ({p})")
            sel = input('Escolha um log para pré-visualizar (número) ou caminho completo: ').strip()
            chosen = None
            if sel.isdigit():
                idx = int(sel) - 1
                if 0 <= idx < len(logs):
                    chosen = logs[idx]
            else:
                # accept direct path
                if sel:
                    chosen = sel

            if not chosen:
                print('Seleção inválida; retornando ao menu.')
                continue

            try:
                restorable, skipped = preview_restore_from_log(chosen)
            except Exception as e:
                print('Falha ao ler/prever log:', e)
                continue

            print('\nEntradas restauráveis:')
            for i, it in enumerate(restorable, start=1):
                e = it['entry']
                print(f"{i}) {e.get('src')}  <- {it['current_location']}")
            print(f"Total restauráveis: {len(restorable)}")

            if skipped:
                print('\nEntradas puladas (não restauráveis):')
                for s in skipped:
                    e = s['entry']
                    print(f"- {e.get('src')}  reason={s['reason']}")

            if not restorable:
                print('Nada a restaurar neste log.')
                continue

            if prompt_yes_no('Deseja restaurar as entradas listadas agora?', default_yes=False):
                restore_from_log(chosen)

        elif choice == '3':
            print('Configurações:')
            print(json.dumps(cfg, indent=2))
            if prompt_yes_no('Editar limites de idade? (padrão 30/31-60/60+)', default_yes=False):
                try:
                    new_keep = int(input(f"Manter arquivos até (dias) [{cfg.get('age_keep_days')}]: ").strip() or cfg.get('age_keep_days'))
                    new_trash_min = int(input(f"Mover para Trash entre (dias) [{cfg.get('age_trash_min')}]: ").strip() or cfg.get('age_trash_min'))
                    new_trash_max = int(input(f"Excluir acima de (dias) [{cfg.get('age_trash_max')}]: ").strip() or cfg.get('age_trash_max'))
                    cfg['age_keep_days'] = new_keep
                    cfg['age_trash_min'] = new_trash_min
                    cfg['age_trash_max'] = new_trash_max
                    save_config(cfg)
                    print('Limites atualizados.')
                except ValueError:
                    print('Valores inválidos; mantendo as configurações anteriores.')

            if prompt_yes_no('Alternar auto_prune (mover+deletar sem confirmação)?', default_yes=False):
                if not cfg.get('auto_prune'):
                    print('auto_prune exige confirmação forte. Você confirma que deseja ativar auto_prune?')
                    if strong_confirm('Digite YES para ativar auto_prune (exclusões automáticas acima do limite):'):
                        cfg['auto_prune'] = True
                        save_config(cfg)
                        print('auto_prune ativado')
                else:
                    cfg['auto_prune'] = False
                    save_config(cfg)
                    print('auto_prune desativado')

        elif choice == '4':
            print('Saindo')
            return
        else:
            print('Opção inválida')


if __name__ == '__main__':
    try:
        main_menu()
    except KeyboardInterrupt:
        print('\nInterrupted')