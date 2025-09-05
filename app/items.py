from typing import List

import re
from fastapi import HTTPException

from app.datamodel import Item
from app.common import INPUT_DIR, IMAGE_EXTS


_slug_rx = re.compile(r"[^a-z0-9]+")
def slugify(s: str) -> str:
    s = s.strip().lower()
    s = _slug_rx.sub("-", s).strip("-")
    return s or "item"

def list_items() -> List[Item]:
    if not INPUT_DIR.exists() or not INPUT_DIR.is_dir():
        INPUT_DIR.mkdir(parents=True, exist_ok=True)
    subdirs = [p for p in INPUT_DIR.iterdir() if p.is_dir()]
    subdirs.sort(key=lambda p: p.name.lower())
    items: List[Item] = []
    for idx, p in enumerate(subdirs):
        rel = str(p.relative_to(INPUT_DIR)).replace("\\", "/")
        items.append(Item(id=idx, name=p.name, rel_path=rel, abs_path=p))
    return items

def list_images(item: Item) -> List[str]:
    files = []
    for child in item.abs_path.iterdir():
        if child.is_file() and child.suffix.lower() in IMAGE_EXTS:
            rel_from_root = str(child.relative_to(INPUT_DIR)).replace("\\", "/")
            files.append(rel_from_root)
    files.sort()
    return files


ITEMS: List[Item] = list_items()


def item_by_id(item_id: int) -> Item:
    if 0 <= item_id < len(ITEMS):
        return ITEMS[item_id]
    raise HTTPException(status_code=404, detail="Item not found")