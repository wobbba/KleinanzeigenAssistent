from pathlib import Path
import yaml


ROOT_DIR = Path(__file__).parent.parent

CONFIG_FILE = ROOT_DIR / "config.yaml"

# ----------------------------
# Config file loading
# ----------------------------
USER_CFG_PATH = CONFIG_FILE.resolve()

with open(USER_CFG_PATH, "r", encoding="utf-8") as f:
    user_cfg = yaml.safe_load(f)
def get_cfg(key, default=None):
    return user_cfg.get(key, default)

KLEIN_CONFIG_PATH = (ROOT_DIR / get_cfg("klein_cfg")).resolve()

with open(KLEIN_CONFIG_PATH, "r", encoding="utf-8") as f:
    klein_cfg = yaml.safe_load(f)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif"}

# ----------------------------
# Constants definition
# ----------------------------
HOST = get_cfg("host")
PORT = int(get_cfg("port"))

KLEIN_BIN = Path(get_cfg("klein_bin")).expanduser().resolve()

WORK_DIR = Path("./.work").resolve()
INBOX_DIR = Path("./inbox").resolve()

INPUT_DIR = WORK_DIR / "input"
ADS_DIR = WORK_DIR / "ads"
ADS_ARCHIVE_DIR = WORK_DIR / "ads_archive"
INPUT_ARCHIVE_DIR = WORK_DIR / "input_archive"
AUDIO_DIR = WORK_DIR / "audio"
KLEIN_LOG_PATH = WORK_DIR / "kleinanzeigen_bot.log"

for p in (WORK_DIR, ADS_DIR, ADS_ARCHIVE_DIR, AUDIO_DIR, INPUT_ARCHIVE_DIR):
    p.mkdir(parents=True, exist_ok=True)

BROWSER_CMD = [get_cfg("chromium_path"),] + klein_cfg["browser"]["arguments"]
