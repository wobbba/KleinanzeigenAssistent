import json
from pathlib import Path
import shutil
from typing import Dict, List, Optional

import subprocess
import sys
import time

import yaml

from app.common import ADS_ARCHIVE_DIR, ADS_DIR, BROWSER_CMD, INPUT_ARCHIVE_DIR, KLEIN_BIN, KLEIN_CONFIG_PATH, KLEIN_LOG_PATH
from app.datamodel import Item
from app.helpers import safe_int
from app.items import slugify

_browser_proc: Optional[subprocess.Popen] = None

def start_debug_browser_once():
    global _browser_proc
    if _browser_proc and _browser_proc.poll() is None:
        return
    try:
        _browser_proc = subprocess.Popen(BROWSER_CMD, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # give it a moment to bind the port
        time.sleep(1.5)
    except Exception as e:
        print(f"[warn] Could not start debug browser: {e}", file=sys.stderr)


def run_bulk_publish() -> subprocess.CompletedProcess:
    start_debug_browser_once()
    cmd = [str(KLEIN_BIN), "publish", "--ads=new", f"--config={str(KLEIN_CONFIG_PATH)}", f"--logfile={str(KLEIN_LOG_PATH)}"]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def find_ad_files(root: Path) -> List[Path]:
    return list(root.rglob("ad_*.y*ml"))  # yaml/yml


def write_ad_yaml(item: Item, md: Dict, ad_dir: Path) -> Path:
    ad_dir.mkdir(parents=True, exist_ok=True)

    ad = {}
    ad["active"] = True
    ad["type"] = (md.get("type") or "OFFER").strip().upper()
    ad["title"] = (md.get("title") or "").strip()
    ad["description"] = (md.get("description") or "").strip()
    ad["category"] = (md.get("category") or "").strip()

    price = safe_int(md.get("price"), None)
    if price is not None:
        ad["price"] = price
    ad["price_type"] = (md.get("price_type") or "NEGOTIABLE").strip().upper()

    ship_type = (md.get("shipping_type") or "SHIPPING").strip().upper()
    ad["shipping_type"] = ship_type
    if md.get("shipping_costs") not in (None, ""):
        ad["shipping_costs"] = float(md["shipping_costs"])
    shipping_options = md.get("shipping_options") or []
    if isinstance(shipping_options, str):
        shipping_options = [s.strip() for s in shipping_options.split(",") if s.strip()]
    ad["shipping_options"] = shipping_options
    sd = md.get("sell_directly")
    if sd is not None:
        ad["sell_directly"] = bool(sd)

    contact = md.get("contact") or {}
    ad["contact"] = {
        "name": contact.get("name", ""),
        "street": contact.get("street", ""),
        "zipcode": str(contact.get("zipcode", "")) if contact.get("zipcode") is not None else "",
        "phone": str(contact.get("phone", "")) if contact.get("phone") is not None else "",
    }

    sa = md.get("special_attributes")
    if isinstance(sa, dict):
        ad["special_attributes"] = sa
    else:
        # try to parse JSON string
        if isinstance(sa, str) and sa.strip():
            try:
                obj = json.loads(sa)
                if isinstance(obj, dict):
                    ad["special_attributes"] = obj
            except Exception:
                pass

    rep = md.get("republication_interval")
    if rep not in (None, ""):
        ri = safe_int(rep, None)
        if ri is not None:
            ad["republication_interval"] = ri

    ad["images"] = ["cropped_*.jpg"]

    fname = f"ad_{slugify(item.name)}.yaml"
    ad_file = ad_dir / fname
    with open(ad_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(ad, f, sort_keys=False, allow_unicode=True)
    return ad_file


def list_pending_ads() -> List[Dict]:
    ads = []
    for ad in find_ad_files(ADS_DIR):
        try:
            data = yaml.safe_load(ad.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
        rel_dir = ad.parent.relative_to(ADS_DIR).as_posix()
        ads.append({
            "dir": rel_dir,
            "file": ad.name,
            "title": data.get("title", ""),
            "category": data.get("category", ""),
            "price": data.get("price", None),
        })
    ads.sort(key=lambda x: x["dir"])
    return ads


def remove_pending_ad_dir(rel_dir: str):
    d = ADS_DIR / rel_dir
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


def archive_published_ads():
    # Move all remaining ad dirs from PUB_ADS_DIR to PUB_ARCHIVE_DIR
    # We move *directories* that contain ad_*.yml files.
    for ad in find_ad_files(ADS_DIR):
        d = ad.parent
        rel = d.relative_to(ADS_DIR)
        dst = ADS_ARCHIVE_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            # merge move: move files individually
            for p in d.iterdir():
                target = dst / p.name
                if target.exists():
                    target = dst / f"{p.stem}__{int(time.time())}{p.suffix}"
                shutil.move(str(p), str(target))
            # cleanup dir
            try:
                d.rmdir()
            except Exception:
                pass
        else:
            shutil.move(str(d), str(dst))


