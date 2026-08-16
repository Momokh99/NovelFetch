import json
import os
import threading


PROGRESS_FILE = "novels/progress.json"

class ProgressTracker:
    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        self._data: dict = {}
        self._dirty = False
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

    def mark_seen(self, slug, idx):
        with self._lock:
            entry = self._data.get(slug, {"last": idx, "seen": []})
            entry["last"] = idx
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

    def remove(self, slug):
        """Forget a novel entirely (e.g. when its folder is deleted)."""
        with self._lock:
            if slug in self._data:
                del self._data[slug]
                self._dirty = True

    def flush(self):
        with self._lock:
            if not self._dirty:
                return
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp, self.path)
            self._dirty = False

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
