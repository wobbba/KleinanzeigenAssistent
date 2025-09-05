from pathlib import Path
import shutil
import cv2
import ffmpeg
import numpy as np
from PIL import Image


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for p in path.rglob("*"):
            try:
                if p.is_file():
                    total += p.stat().st_size
            except Exception:
                pass
    except Exception:
        pass
    return total


def _format_bytes(n: int) -> str:
    units = ["B","KB","MB","GB","TB","PB"]
    f = float(n)
    i = 0
    while f >= 1024.0 and i < len(units)-1:
        f /= 1024.0
        i += 1
    return f"{f:.1f} {units[i]}"


def _clear_dir_contents(path: Path):
    if not path.exists():
        return
    for child in path.iterdir():
        try:
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
        except Exception:
            pass
        

def safe_int(v, default=None):
    try:
        return int(str(v).strip())
    except Exception:
        return default
    

def is_black_separator(path,
                       resize_to=256,
                       p95_max=20,          # brightness cap
                       std_max=8,           # flatness cap
                       entropy_max=1.5,     # bits
                       edge_ratio_max=0.001 # edges cap
                      ):
    # 1) load -> grayscale -> small for speed/noise smoothing
    im = Image.open(path).convert("L").resize((resize_to, resize_to))
    arr = np.asarray(im, dtype=np.uint8)

    # 2) darkness + flatness
    p95 = np.percentile(arr, 95)
    std = arr.std()

    # 3) entropy (penalize structure/texture)
    # histogram on 256 bins
    hist = np.bincount(arr.flatten(), minlength=256).astype(np.float64)
    p = hist / hist.sum()
    p = p[p > 0]
    entropy = -(p * np.log2(p)).sum()

    # 4) edge density (real scenes have edges even if dark)
    # gentle blur to suppress sensor noise before Canny
    arr_blur = cv2.GaussianBlur(arr, (5,5), 0)
    edges = cv2.Canny(arr_blur, 20, 60, L2gradient=True)
    edge_ratio = (edges > 0).mean()

    return (p95 <= p95_max) and (std <= std_max) and (entropy <= entropy_max) and (edge_ratio <= edge_ratio_max)


def strip_silence_ffmpegpy(src: str, dst: str):
    (
        ffmpeg
        .input(src)
        .output(
            dst,
            af="silenceremove=stop_periods=-1:stop_duration=0.5:stop_threshold=-50dB",
            acodec="libopus", audio_bitrate="64k", ar="48000"
        )
        .overwrite_output()
        .run(quiet=True)   # quiet=True to suppress logs
    )