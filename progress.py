import json
import os
import threading
import time


PROGRESS_FILE = "novels/progress.json"
TRACKING_FILE = "novels/tracking.json"

class ProgressTracker:
    def __init__(self, path):
        self.path = path
        self.tracking_path = TRACKING_FILE
        self._lock = threading.Lock()
        self._data: dict = {}
        self._tracked: dict = {}
        self._dirty = False
        self._tracked_dirty = False
        self._load()

    def _load(self):
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        for slug, val in list(data.items()):
            if isinstance(val, int):
                data[slug] = {"last": val, "seen": [val]}
        self._data = data
        try:
            with open(self.tracking_path) as f:
                self._tracked = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._tracked = {}
        self._backfill_tracked()

    def _backfill_tracked(self):
        """Migrate legacy tracked flags (meta.json with "tracked": true) into
        the tracking registry so deleting a folder no longer drops tracking."""
        novels_dir = os.path.dirname(self.path)
        if not os.path.isdir(novels_dir):
            return
        for root, dirs, files in os.walk(novels_dir):
            if "meta.json" not in files:
                continue
            rel = os.path.relpath(root, novels_dir).replace(os.sep, "/")
            if rel in self._tracked:
                continue
            try:
                with open(os.path.join(root, "meta.json")) as f:
                    meta = json.load(f)
            except (OSError, ValueError):
                continue
            if meta.get("tracked"):
                self._tracked[rel] = {"title": meta.get("title") or rel}
                self._tracked_dirty = True

    def mark_seen(self, slug, idx):
        with self._lock:
            entry = self._data.get(slug, {"last": idx, "seen": []})
            entry["last"] = idx
            entry["last_time"] = int(time.time())
            if idx not in entry["seen"]:
                entry["seen"].append(idx)
            self._data[slug] = entry
            self._dirty = True

    def get_last(self, slug):
        with self._lock:
            entry = self._data.get(slug)
            return entry["last"] if entry else None

    def get_seen(self, slug):
        with self._lock:
            entry = self._data.get(slug)
            return set(entry["seen"]) if entry else set()

    def get_history(self):
        """Reading history, newest-read first: [{slug, last, last_time}, ...]."""
        with self._lock:
            rows = [
                {"slug": slug, "last": v["last"], "last_time": v.get("last_time")}
                for slug, v in self._data.items()
                if isinstance(v, dict) and v.get("last_time")
            ]
        rows.sort(key=lambda r: int(r["last_time"]), reverse=True)
        return rows

    def remove(self, slug):
        """Forget a novel entirely (e.g. when its folder is deleted)."""
        with self._lock:
            if slug in self._data:
                del self._data[slug]
                self._dirty = True

    def track(self, slug, title):
        """Register a slug as tracked. Persists even if the novels/{slug}
        folder is removed, so tracking survives deleting the files."""
        with self._lock:
            prev = self._tracked.get(slug, {})
            if prev.get("title") != title:
                self._tracked[slug] = {"title": title}
                self._tracked_dirty = True

    def untrack(self, slug):
        """Stop tracking a novel (keeps any reading progress)."""
        with self._lock:
            if slug in self._tracked:
                del self._tracked[slug]
                self._tracked_dirty = True

    def is_tracked(self, slug):
        with self._lock:
            return slug in self._tracked

    def tracked_novels(self):
        """Every tracked slug regardless of whether files still exist:
        [{slug, title}, ...] sorted by title."""
        with self._lock:
            rows = [
                {"slug": slug, "title": v.get("title") or slug}
                for slug, v in self._tracked.items()
            ]
        rows.sort(key=lambda n: n["slug"])
        return rows

    def flush(self):
        with self._lock:
            if self._dirty:
                os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
                tmp = self.path + ".tmp"
                with open(tmp, "w") as f:
                    json.dump(self._data, f, indent=2)
                os.replace(tmp, self.path)
                self._dirty = False
            if self._tracked_dirty:
                os.makedirs(os.path.dirname(self.tracking_path) or ".", exist_ok=True)
                tmp = self.tracking_path + ".tmp"
                with open(tmp, "w") as f:
                    json.dump(self._tracked, f, indent=2)
                os.replace(tmp, self.tracking_path)
                self._tracked_dirty = False

progress = ProgressTracker(PROGRESS_FILE)

def _scan_library():
    novels_dir = "novels"
    if not os.path.isdir(novels_dir):
        return []
    result = []
    for root, dirs, files in os.walk(novels_dir):
        if "meta.json" not in files:
            continue
        rel = os.path.relpath(root, novels_dir).replace(os.sep, "/")
        result.append({"slug": rel, "title": _slug_to_title(rel), "count": len(files)})
    result.sort(key=lambda n: n["slug"])
    return result

LANGUAGES = {
    "Arabic": "ar", "Chinese": "zh-cn", "French": "fr", "German": "de",
    "Hindi": "hi", "Italian": "it", "Japanese": "ja", "Korean": "ko",
    "Portuguese": "pt", "Russian": "ru", "Spanish": "es", "Turkish": "tr",
}


def _slug_to_title(slug):
    raw = slug.split(":", 1)[-1] if ":" in slug else slug
    return raw.replace("-", " ").title()
