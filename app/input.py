import os
from pathlib import Path
import shutil

from app.common import IMAGE_EXTS, INBOX_DIR, INPUT_ARCHIVE_DIR, INPUT_DIR
from app.datamodel import Item
from app.helpers import is_black_separator


def process_inbox(inbox_path=INBOX_DIR):

    print("Processing inbox...")
    
    new_item = True
    target_dir = None

    for filename in sorted(os.listdir(inbox_path)):
        if "." + filename.lower().split(".")[-1] in IMAGE_EXTS:
            
            if new_item:
                target_dir = os.path.join(INPUT_DIR, filename.split(".")[0])
                os.mkdir(target_dir)
                new_item = False

            file_path = os.path.join(inbox_path, filename)
            if is_black_separator(file_path):
                os.remove(file_path)
                new_item = True
            else:
                shutil.move(file_path, target_dir)


def archive_input_folder(item: Item):
    src = item.abs_path
    if not src.exists():
        return
    dest = INPUT_ARCHIVE_DIR / item.rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Move; if exists, add suffix
    final = dest
    n = 1
    while final.exists():
        final = dest.parent / f"{dest.name}__{n}"
        n += 1
    shutil.move(str(src), str(final))


def restore_input_for_rel(rel_dir: str) -> bool:
    # Try exact match, then suffixed variants like name__N
    rel = Path(rel_dir)
    exact = INPUT_ARCHIVE_DIR / rel
    candidates = []
    if exact.exists():
        candidates.append(exact)
    parent = (INPUT_ARCHIVE_DIR / rel.parent)
    base = rel.name
    if parent.exists():
        for p in parent.glob(base + "__*"):
            if p.is_dir():
                candidates.append(p)
    if not candidates:
        return False
    # pick most recent
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    src = candidates[0]
    dst = INPUT_DIR / rel
    final = dst
    n = 1
    while final.exists():
        final = dst.parent / f"{dst.name}__undo{n}"
        n += 1
    final.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(src), str(final))
        return True
    except Exception:
        return False
