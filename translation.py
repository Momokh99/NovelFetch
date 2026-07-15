from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor


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
                    chunks.append(cur)
                    cur = s + "."
                else:
                    cur = (cur + " " + s + ".") if cur else (s + ".")
            continue
        if len(cur) + len(p) + 2 > maxlen:
            chunks.append(cur)
            cur = p
        else:
            cur = (cur + "\n\n" + p) if cur else p
    if cur:
        chunks.append(cur)
    return chunks


def _translate_text(text, target):
    try:
        translator = GoogleTranslator(source="auto", target=target)
        chunks = _chunk_text(text)
        if len(chunks) == 1:
            return translator.translate(text)
        translated = list(_translate_pool.map(translator.translate, chunks))
        return "\n\n".join(translated)
    except Exception:
        return None






