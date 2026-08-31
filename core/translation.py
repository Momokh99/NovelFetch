import re
import time
from concurrent.futures import ThreadPoolExecutor
from this import d

from deep_translator import GoogleTranslator

_translate_pool = ThreadPoolExecutor(max_workers=5)


def _chunk_text(text, maxlen=4800):
    paragraphs = text.split("\n\n")
    chunks, cur = [], ""
    for p in paragraphs:
        if len(p) > maxlen:
            sentences = p.replace("\n", " ").split(". ")
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                if len(cur) + len(s) + 2 > maxlen:
                    if cur:
                        chunks.append(cur)
                    cur = s + "."
                else:
                    cur = (cur + " " + s + ".") if cur else (s + ".")
            continue
        if len(cur) + len(p) + 2 > maxlen:
            if cur:
                chunks.append(cur)
            cur = p
        else:
            cur = (cur + "\n\n" + p) if cur else p
    if cur:
        chunks.append(cur)
    return chunks


# deep_translator's GoogleTranslator hits translate.google.com/m, which is
# throttled/flaky: it intermittently returns an HTTP 500 page, and when that
# happens deep_translator "succeeds" with the error page text as the result.
# Treat both signals as transient failures and retry with a short backoff.
_ERROR_PAGE_RE = re.compile(r"^Error \d+", re.I)
_RETRIES = 3


def _safe_translate(translator, chunk, retries=_RETRIES):
    last = None
    for attempt in range(retries):
        try:
            out = translator.translate(chunk)
            if (out and not _ERROR_PAGE_RE.match(str(out))):
                return out
            last = out  # e.g. 'Error 500 (Server Error)!!1...' — retry
        except Exception as exc:  # noqa: BLE001 — provider errors are expected
            last = exc
        if attempt < retries - 1:
            time.sleep(0.8 * (attempt + 1))
    return None


def _translate_text(text, target):
    try:
        translator = GoogleTranslator(source="auto", target=target)
    except Exception:
        return None
    chunks = _chunk_text(text)
    if len(chunks) == 1:
        return _safe_translate(translator, text)
    translated = list(_translate_pool.map(
        lambda c: _safe_translate(translator, c), chunks))
    if any(t is None for t in translated):
        return None
    return "\n\n".join([t for t in translated if t is not None])
