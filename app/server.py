from typing import List

import os
import time

from pathlib import Path
from PIL import Image, ImageOps

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.common import ADS_ARCHIVE_DIR, ADS_DIR, INPUT_ARCHIVE_DIR, INPUT_DIR, AUDIO_DIR, KLEIN_LOG_PATH, KLEIN_LOG_PATH, ROOT_DIR, get_cfg
from app.datamodel import SubmitPayload, UndoPayload
from app.helpers import _clear_dir_contents, _dir_size, _format_bytes, strip_silence_ffmpegpy
from app.input import archive_input_folder, restore_input_for_rel
from app.items import ITEMS, item_by_id, list_images, list_items
from app.kleinanzeigen import archive_published_ads, list_pending_ads, remove_pending_ad_dir, run_bulk_publish, write_ad_yaml
from app.design_listing import design_listing


# Initialize FastAPI server and mount static files for media
server = FastAPI(title="Kleinanzeigen Assistent")
server.mount("/media", StaticFiles(directory=str(INPUT_DIR)), name="media")


# Serve the main HTML page
@server.get("/", response_class=HTMLResponse)
def index():
    index_path = (ROOT_DIR / "app/index.html").resolve()
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


# Return a list of items with their image counts
@server.get("/api/items")
def api_items():
    global ITEMS
    ITEMS = list_items()
    data = []
    for it in ITEMS:
        imgs = list_images(it)
        data.append({"id": it.id, "name": it.name, "imageCount": len(imgs)})
    return {"items": data}


# Return image URLs for a specific item
@server.get("/api/items/{item_id}/images")
def api_item_images(item_id: int):
    it = item_by_id(item_id)
    imgs = list_images(it)
    return {"item": {"id": it.id, "name": it.name}, "images": [f"/media/{p}" for p in imgs]}

# Return image URLs for a specific item
@server.get("/api/config/accessibility")
def api_config_accessibility():
    return {
        "accessibility": get_cfg("accessibility_mode")
    }


# Upload an audio file for an item, remove silences, and generate a draft
@server.post("/api/audio/{item_id}")
async def api_audio_upload(item_id: int, file: UploadFile = File(...)):
    it = item_by_id(item_id)
    ts = int(time.time() * 1000)
    ext = Path(file.filename or "note.webm").suffix.lower() or ".webm"
    audio_id = f"{it.id}-{ts}{ext}"
    dest = AUDIO_DIR / audio_id
    content = await file.read()
    dest.write_bytes(content)

    # Remove silences from the uploaded audio using ffmpeg
    tmp = dest.with_suffix(dest.suffix + ".tmp.webm")
    strip_silence_ffmpegpy(str(dest), str(tmp))
    # Replace original file with processed file
    os.replace(tmp, dest)

    # Generate a draft listing using the audio
    draft = await design_listing(str(dest)) 

    # delete audio file
    dest.unlink(missing_ok=True)

    return {"ok": True, "audioId": audio_id, "draft": draft}


# Submit an item: process image crops, save metadata, and archive input
@server.post("/api/items/{item_id}/submit")
def api_submit(item_id: int, payload: SubmitPayload):
    it = item_by_id(item_id)

    # Prepare ad directory for this item
    ad_dir = (ADS_DIR / it.rel_path)
    ad_dir.mkdir(parents=True, exist_ok=True)

    # Respect client-provided image order if present
    ordered_selections = payload.selections
    if payload.image_order:
        by_url = {s.url: s for s in payload.selections}
        ordered_selections = [by_url[u] for u in payload.image_order if u in by_url]

    # Save cropped images
    cropped_paths: List[Path] = []
    for idx, sel in enumerate(ordered_selections):
        if not sel.url.startswith("/media/"):
            raise HTTPException(status_code=400, detail=f"Invalid media URL: {sel.url}")
        rel = sel.url[len("/media/") :]
        src_path = INPUT_DIR / rel
        if not src_path.exists():
            raise HTTPException(status_code=404, detail=f"Source image not found: {rel}")

        # Open and crop the image according to selection
        with Image.open(src_path) as im:
            im = ImageOps.exif_transpose(im)
            im = im.convert("RGB")
            W, H = im.size
            x = min(max(sel.crop.x, 0.0), 1.0)
            y = min(max(sel.crop.y, 0.0), 1.0)
            w = min(max(sel.crop.w, 0.0), 1.0)
            h = min(max(sel.crop.h, 0.0), 1.0)
            left = int(round(x * W)); top = int(round(y * H))
            right = int(round((x + w) * W)); bottom = int(round((y + h) * H))
            left, top = max(0, left), max(0, top)
            right, bottom = min(W, right), min(H, bottom)
            if right <= left or bottom <= top:
                continue
            cropped = im.crop((left, top, right, bottom))
            out_name = f"cropped_{idx+1:02d}.jpg"
            out_path = ad_dir / out_name
            cropped.save(out_path, format="JPEG", quality=92, optimize=True)
            cropped_paths.append(out_path)

    # Write ad metadata to YAML file
    ad_file = write_ad_yaml(it, dict(payload.metadata or {}), ad_dir)

    # Archive the input folder now
    archive_input_folder(it)


    # Compute next item id if available
    next_id = it.id + 1 if it.id + 1 < len(ITEMS) else None
    return {
        "ok": True,
        "ad_file": str(ad_file),
        "cropped": [str(p) for p in cropped_paths],
        "nextItemId": next_id,
    }


# List all pending ads
@server.get("/api/pending")
def api_pending():
    return {"pending": list_pending_ads()}


# Publish all pending ads and archive them if successful
@server.post("/api/publish_all")
def api_publish_all():
    pending = list_pending_ads()
    if not pending:
        return {"ok": True, "published": False, "message": "No pending ads."}
    res = run_bulk_publish()
    pub_ok = (res.returncode == 0)
    if pub_ok:
        archive_published_ads()
    return {
        "ok": pub_ok,
        "returncode": res.returncode,
        "stdout": res.stdout[-6000:],
        "stderr": res.stderr[-6000:],
        "published": pub_ok,
    }


# Get archive size and log info
@server.get("/api/archive/info")
def api_archive_info():
    log_size = KLEIN_LOG_PATH.stat().st_size if KLEIN_LOG_PATH.exists() else 0
    total = _dir_size(ADS_ARCHIVE_DIR) + _dir_size(INPUT_ARCHIVE_DIR) + log_size
    return {"bytes": total, "human": _format_bytes(total)}


# Clear all archives and logs
@server.post("/api/archive/clear")
def api_archive_clear():
    _clear_dir_contents(ADS_ARCHIVE_DIR)
    _clear_dir_contents(INPUT_ARCHIVE_DIR)
    if KLEIN_LOG_PATH.exists():
        try:
            KLEIN_LOG_PATH.unlink()
        except Exception:
            pass
    return {"ok": True}


# Archive and delete input for a specific item
@server.post("/api/items/{item_id}/delete_input")
def api_delete_input(item_id: int):
    it = item_by_id(item_id)
    archive_input_folder(it)
    return {"ok": True}


# Undo a pending ad and restore its input
@server.post("/api/pending/undo")
def api_pending_undo(payload: UndoPayload):
    rel = payload.dir.strip().strip("/")
    remove_pending_ad_dir(rel)
    restored = restore_input_for_rel(rel)
    return {"ok": True, "restored": restored}


# Undo all pending ads and restore their inputs
@server.post("/api/pending/undo_all")
def api_pending_undo_all():
    entries = list_pending_ads()
    restored = 0
    for x in entries:
        rel = x.get("dir","").strip().strip("/")
        if not rel:
            continue
        remove_pending_ad_dir(rel)
        if restore_input_for_rel(rel):
            restored += 1
    return {"ok": True, "count": len(entries), "restored": restored}
