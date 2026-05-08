import argparse
import csv
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import django
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from apps.books.models import Book, Word, WordExample  # noqa: E402


sys.stdout.reconfigure(encoding="utf-8")

ECDICT_PATH = BASE_DIR / "scripts" / "resources" / "ecdict.csv"
PLACEHOLDER_EXAMPLE_MARKER = "appears in this vocabulary book"
PLACEHOLDER_TRANSLATION_MARKER = "已加入当前词书"
BLOCKLIST_WORDS = {
    "fuck",
    "fucking",
    "shit",
    "bitch",
    "slut",
    "dick",
    "asshole",
    "whore",
    "damn",
    "piss",
    "bastard",
}
POS_ALIAS = {
    "adjective": "adj.",
    "adj": "adj.",
    "a": "adj.",
    "adverb": "adv.",
    "adv": "adv.",
    "ad": "adv.",
    "noun": "n.",
    "n": "n.",
    "verb": "v.",
    "v": "v.",
    "vt": "v.",
    "vi": "v.",
    "pronoun": "pron.",
    "pron": "pron.",
    "preposition": "prep.",
    "prep": "prep.",
    "conjunction": "conj.",
    "conj": "conj.",
    "interjection": "interj.",
    "interj": "interj.",
    "int": "interj.",
    "determiner": "det.",
    "article": "art.",
    "numeral": "num.",
}
THREAD_LOCAL = threading.local()


def get_session():
    if not hasattr(THREAD_LOCAL, "session"):
        session = requests.Session()
        session.headers.update({"User-Agent": "wxapp-dict-enricher/1.0"})
        THREAD_LOCAL.session = session
    return THREAD_LOCAL.session


def normalize_text(value):
    value = (value or "").replace("\r", " ").replace("\n", " ").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def normalize_pos(value):
    raw = normalize_text(value).lower().rstrip(".")
    return POS_ALIAS.get(raw, value if value else "")


def pos_matches(pos_hint, line_prefix):
    hint = normalize_pos(pos_hint)
    prefix = normalize_pos(line_prefix)
    if not hint or not prefix:
        return False
    if hint == prefix:
        return True
    if hint == "v." and prefix == "v.":
        return True
    return False


def is_placeholder_word(word):
    sentence = normalize_text(word.example_sentence).lower()
    translation = normalize_text(word.example_translation)
    return PLACEHOLDER_EXAMPLE_MARKER in sentence or PLACEHOLDER_TRANSLATION_MARKER in translation


def should_enrich_word(word):
    return (
        is_placeholder_word(word)
        or not normalize_text(word.meaning_cn)
        or not normalize_text(word.example_sentence)
    )


def load_ecdict_subset(target_words):
    if not ECDICT_PATH.exists():
        raise FileNotFoundError(f"ecdict file not found: {ECDICT_PATH}")

    target_words = {item.lower() for item in target_words}
    result = {}
    with ECDICT_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            word = row["word"].strip().lower()
            if word not in target_words or word in result:
                continue
            result[word] = {
                "phonetic": normalize_text(row.get("phonetic", "")),
                "translation": row.get("translation", "").replace("\\n", "\n"),
                "definition": normalize_text(row.get("definition", "")),
                "pos": normalize_text(row.get("pos", "")),
            }
            if len(result) >= len(target_words):
                break
    return result


def split_translation_lines(raw_translation):
    lines = []
    for raw_line in raw_translation.splitlines():
        line = normalize_text(raw_line)
        if not line:
            continue
        line = re.sub(r"^\[[^\]]+\]\s*", "", line)
        match = re.match(r"^(adj\.|adv\.|ad\.|a\.|n\.|v\.|vt\.|vi\.|prep\.|pron\.|conj\.|interj\.|int\.|det\.|art\.|num\.)\s*(.+)$", line, re.I)
        if match:
            prefix = normalize_pos(match.group(1))
            body = match.group(2)
        else:
            prefix = ""
            body = line
        body = body.replace(",", "；").replace(";", "；")
        body = re.sub(r"；+", "；", body).strip("； ")
        if body:
            lines.append({"pos": prefix, "text": body})
    return lines


def choose_translation(ecdict_entry, pos_hint):
    if not ecdict_entry:
        return ""
    lines = split_translation_lines(ecdict_entry.get("translation", ""))
    if not lines:
        return ""

    for line in lines:
        if pos_matches(pos_hint, line["pos"]):
            return line["text"]

    return lines[0]["text"]


def infer_pos_from_ecdict(ecdict_entry, current_pos):
    if not ecdict_entry:
        return normalize_pos(current_pos)
    lines = split_translation_lines(ecdict_entry.get("translation", ""))
    if not lines:
        return normalize_pos(current_pos)
    for line in lines:
        if line["pos"]:
            return normalize_pos(line["pos"])
    return normalize_pos(current_pos)


def score_example(sentence, word):
    if not sentence:
        return -999
    sentence = normalize_text(sentence)
    lower_sentence = sentence.lower()
    lower_word = word.lower()
    word_count = len(sentence.split())

    score = 0
    if re.search(rf"\b{re.escape(lower_word)}\b", lower_sentence):
        score += 30
    if 4 <= word_count <= 16:
        score += 20
    elif word_count <= 3:
        score -= 25
    elif word_count > 24:
        score -= 10
    if sentence[:1].isupper():
        score += 5
    if sentence.endswith((".", "!", "?")):
        score += 5
    if any(bad in lower_sentence for bad in BLOCKLIST_WORDS if bad != lower_word):
        score -= 30
    if any(name in sentence for name in ("Tom", "Mary", "Sami", "Mennad", "Layla", "Corona")):
        score -= 6
    return score


def translate_text(text):
    text = normalize_text(text)
    if not text:
        return ""
    session = get_session()
    response = session.get(
        "https://translate.googleapis.com/translate_a/single",
        params={
            "client": "gtx",
            "sl": "en",
            "tl": "zh-CN",
            "dt": "t",
            "q": text,
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    return normalize_text("".join(item[0] for item in data[0] if item and item[0]))


def fetch_dictionary_data(word):
    session = get_session()
    try:
        response = session.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=20)
    except requests.RequestException:
        return {}
    if response.status_code != 200:
        return {}

    try:
        payload = response.json()
    except ValueError:
        return {}

    phonetic = ""
    candidates = []
    for entry in payload:
        if not phonetic:
            phonetic = normalize_text(entry.get("phonetic", ""))
        for phonetic_item in entry.get("phonetics", []):
            phonetic_text = normalize_text(phonetic_item.get("text", ""))
            if phonetic_text:
                phonetic = phonetic or phonetic_text
                break

        for meaning in entry.get("meanings", []):
            pos = normalize_pos(meaning.get("partOfSpeech", ""))
            for definition in meaning.get("definitions", []):
                candidates.append(
                    {
                        "pos": pos,
                        "definition": normalize_text(definition.get("definition", "")),
                        "example": normalize_text(definition.get("example", "")),
                    }
                )

    best_definition = ""
    best_pos = ""
    for candidate in candidates:
        if candidate["definition"]:
            best_definition = candidate["definition"]
            best_pos = candidate["pos"]
            break

    best_example = ""
    best_score = -999
    for candidate in candidates:
        score = score_example(candidate["example"], word)
        if score > best_score:
            best_score = score
            best_example = candidate["example"]

    return {
        "phonetic": phonetic,
        "pos": best_pos,
        "definition": best_definition,
        "example": best_example,
    }


def extract_chinese_translation(item):
    for group in item.get("translations", []):
        for translation in group:
            if str(translation.get("lang", "")).lower() in {"cmn", "zh", "zho"}:
                return normalize_text(translation.get("text", ""))
    return ""


def fetch_tatoeba_example(word):
    session = get_session()
    try:
        response = session.get(
            "https://tatoeba.org/en/api_v0/search",
            params={"from": "eng", "query": word, "orphans": "no", "sort": "relevance"},
            timeout=20,
        )
    except requests.RequestException:
        return {}
    if response.status_code != 200:
        return {}

    try:
        payload = response.json()
    except ValueError:
        return {}

    best = {}
    best_score = -999
    for item in payload.get("results", []):
        sentence = normalize_text(item.get("text", ""))
        if not re.search(rf"\b{re.escape(word)}\b", sentence, re.I):
            continue
        score = score_example(sentence, word)
        chinese = extract_chinese_translation(item)
        if chinese:
            score += 10
        if score > best_score:
            best_score = score
            best = {"example": sentence, "translation": chinese}
    return best


def enrich_single_word(word_text, current_pos, ecdict_entry):
    word_text = word_text.lower()
    dictionary_data = fetch_dictionary_data(word_text)

    target_pos = (
        normalize_pos(dictionary_data.get("pos", ""))
        or infer_pos_from_ecdict(ecdict_entry, current_pos)
        or normalize_pos(ecdict_entry.get("pos", "") if ecdict_entry else "")
        or normalize_pos(current_pos)
    )
    target_meaning = choose_translation(ecdict_entry, target_pos)
    if not target_meaning and dictionary_data.get("definition"):
        try:
            target_meaning = translate_text(dictionary_data["definition"])
        except requests.RequestException:
            target_meaning = ""

    example_sentence = dictionary_data.get("example", "")
    example_translation = ""

    if example_sentence:
        try:
            example_translation = translate_text(example_sentence)
        except requests.RequestException:
            example_translation = ""
    else:
        tatoeba_data = fetch_tatoeba_example(word_text)
        example_sentence = tatoeba_data.get("example", "")
        example_translation = tatoeba_data.get("translation", "")
        if example_sentence and not example_translation:
            try:
                example_translation = translate_text(example_sentence)
            except requests.RequestException:
                example_translation = ""

    return {
        "word": word_text,
        "part_of_speech": target_pos or current_pos,
        "phonetic": dictionary_data.get("phonetic", "") or (ecdict_entry.get("phonetic", "") if ecdict_entry else ""),
        "meaning_cn": target_meaning,
        "example_sentence": example_sentence,
        "example_translation": example_translation,
    }


def delete_blocklist_words():
    removed = []
    words = list(Word.objects.filter(word__in=BLOCKLIST_WORDS).select_related("book"))
    for word in words:
        removed.append((word.book.name, word.word))
        word.delete()

    if removed:
        for book in Book.objects.all():
            new_count = book.words.count()
            if book.word_count != new_count:
                book.word_count = new_count
                book.save(update_fields=["word_count", "updated_at"])
    return removed


def update_word_record(word_obj, enriched):
    changed = False

    for field in ("part_of_speech", "phonetic", "meaning_cn", "example_sentence", "example_translation"):
        if field in {"example_sentence", "example_translation"} and enriched.get(field) is None:
            continue
        new_value = normalize_text(enriched.get(field, ""))
        if getattr(word_obj, field) != new_value:
            setattr(word_obj, field, new_value)
            changed = True

    if changed:
        word_obj.save(update_fields=["part_of_speech", "phonetic", "meaning_cn", "example_sentence", "example_translation", "updated_at"])

    placeholder_examples = word_obj.examples.filter(example_sentence__icontains=PLACEHOLDER_EXAMPLE_MARKER)
    if word_obj.example_sentence:
        example_obj = word_obj.examples.order_by("sort_order", "id").first()
        if example_obj is None:
            WordExample.objects.create(
                word=word_obj,
                example_sentence=word_obj.example_sentence,
                example_translation=word_obj.example_translation,
                sort_order=1,
            )
        else:
            if (
                example_obj.example_sentence != word_obj.example_sentence
                or example_obj.example_translation != word_obj.example_translation
                or example_obj.sort_order != 1
            ):
                example_obj.example_sentence = word_obj.example_sentence
                example_obj.example_translation = word_obj.example_translation
                example_obj.sort_order = 1
                example_obj.save(update_fields=["example_sentence", "example_translation", "sort_order", "updated_at"])
        placeholder_examples.exclude(sort_order=1).delete()
    else:
        placeholder_examples.delete()

    return changed


def build_target_queryset(book_id=None, limit=None):
    queryset = Word.objects.select_related("book").prefetch_related("examples").order_by("id")
    if book_id:
        queryset = queryset.filter(book_id=book_id)
    queryset = [word for word in queryset if should_enrich_word(word)]
    if limit:
        queryset = queryset[:limit]
    return queryset


def build_repair_queryset(book_id=None, limit=None):
    queryset = Word.objects.select_related("book").prefetch_related("examples").order_by("id")
    if book_id:
        queryset = queryset.filter(book_id=book_id)
    queryset = list(queryset)
    if limit:
        queryset = queryset[:limit]
    return queryset


def parse_args():
    parser = argparse.ArgumentParser(description="Enrich placeholder word data with real dictionary meanings and examples")
    parser.add_argument("--book-id", type=int, default=0, help="Only process a single book id")
    parser.add_argument("--limit", type=int, default=0, help="Only process the first N placeholder words")
    parser.add_argument("--workers", type=int, default=8, help="Network worker count")
    parser.add_argument("--batch-size", type=int, default=250, help="Unique word batch size for incremental saves")
    parser.add_argument("--repair-pos", action="store_true", help="Repair all words from ECDICT without fetching examples")
    parser.add_argument("--remove-blocked", action="store_true", help="Delete obviously inappropriate words before enriching")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.remove_blocked:
        removed = delete_blocklist_words()
        print(f"removed blocked words: {len(removed)}")
        for book_name, word_text in removed[:20]:
            print(f"  - {book_name}: {word_text}")

    if args.repair_pos:
        words = build_repair_queryset(book_id=args.book_id or None, limit=args.limit or None)
    else:
        words = build_target_queryset(book_id=args.book_id or None, limit=args.limit or None)
    if not words:
        print("no placeholder words found")
        return

    unique_words = sorted({word.word.lower(): word.part_of_speech for word in words}.items())
    ecdict_map = load_ecdict_subset(word for word, _ in unique_words)
    print(f"placeholder rows: {len(words)}")
    print(f"unique words to enrich: {len(unique_words)}")

    words_by_text = {}
    for word_obj in words:
        words_by_text.setdefault(word_obj.word.lower(), []).append(word_obj)

    completed = 0
    changed_count = 0
    blank_example_count = 0
    failed = 0
    batch_size = max(args.batch_size, 1)

    for start in range(0, len(unique_words), batch_size):
        chunk = unique_words[start:start + batch_size]
        enriched_by_word = {}

        if args.repair_pos:
            for word_text, part_of_speech in chunk:
                ecdict_entry = ecdict_map.get(word_text, {})
                enriched_by_word[word_text] = {
                    "word": word_text,
                    "part_of_speech": infer_pos_from_ecdict(ecdict_entry, part_of_speech) or normalize_pos(part_of_speech),
                    "phonetic": normalize_text(ecdict_entry.get("phonetic", "")),
                    "meaning_cn": choose_translation(ecdict_entry, part_of_speech),
                    "example_sentence": None,
                    "example_translation": None,
                }
        else:
            with ThreadPoolExecutor(max_workers=max(args.workers, 1)) as executor:
                future_map = {
                    executor.submit(enrich_single_word, word_text, part_of_speech, ecdict_map.get(word_text, {})): word_text
                    for word_text, part_of_speech in chunk
                }
                for future in as_completed(future_map):
                    word_text = future_map[future]
                    try:
                        enriched_by_word[word_text] = future.result()
                    except Exception as exc:  # noqa: BLE001
                        failed += 1
                        enriched_by_word[word_text] = {
                            "word": word_text,
                            "part_of_speech": "",
                            "phonetic": "",
                            "meaning_cn": choose_translation(ecdict_map.get(word_text, {}), ""),
                            "example_sentence": "",
                            "example_translation": "",
                        }
                        print(f"[warn] failed to enrich {word_text}: {exc}")

        chunk_blank_count = 0
        chunk_changed_count = 0
        for word_text, _ in chunk:
            enriched = enriched_by_word.get(word_text, {})
            if not normalize_text(enriched.get("example_sentence", "")):
                chunk_blank_count += len(words_by_text.get(word_text, []))
            for word_obj in words_by_text.get(word_text, []):
                if update_word_record(word_obj, enriched):
                    chunk_changed_count += 1

        completed += len(chunk)
        changed_count += chunk_changed_count
        blank_example_count += chunk_blank_count
        print(
            f"saved batch {start // batch_size + 1}: "
            f"{completed}/{len(unique_words)} unique words, "
            f"updated rows +{chunk_changed_count}, "
            f"rows without real examples in batch {chunk_blank_count}"
        )

    print(f"updated rows: {changed_count}")
    print(f"rows still without real examples: {blank_example_count}")
    print(f"failed lookups: {failed}")


if __name__ == "__main__":
    main()
