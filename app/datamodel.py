from typing import Dict, List, Optional

from dataclasses import dataclass
from pathlib import Path
from pydantic import BaseModel


@dataclass
class Item:
    id: int
    name: str
    rel_path: str  # relative to INPUT_DIR
    abs_path: Path


class UndoPayload(BaseModel):
    dir: str


class SelectionCrop(BaseModel):
    x: float; y: float; w: float; h: float  # normalized [0,1]


class ImageSelection(BaseModel):
    url: str
    crop: SelectionCrop


class SubmitPayload(BaseModel):
    metadata: Dict
    selections: List[ImageSelection]
    audio_id: Optional[str] = None
    # Full image URL order as seen in the UI (e.g. ["/media/.../a.jpg", ...])
    image_order: Optional[List[str]] = None