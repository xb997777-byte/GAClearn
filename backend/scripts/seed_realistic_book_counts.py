import os
import sys
from pathlib import Path

import django

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from django.db import transaction  # noqa: E402

from apps.books.models import Book, Word, WordExample  # noqa: E402


RESOURCE_FILE = BASE_DIR / "scripts" / "resources" / "google_20k.txt"

BOOK_TARGETS = [
    {
        "name": "四级高频词汇",
        "legacy_names": ["四级高频词汇测试集"],
        "category": "CET-4",
        "level": "基础",
        "description": "适合大学英语四级备考的高频词汇。",
        "cover_color": "#4F7CFF",
        "target_count": 4500,
        "offset": 0,
    },
    {
        "name": "考研核心词汇",
        "legacy_names": ["考研核心词汇测试集"],
        "category": "考研",
        "level": "进阶",
        "description": "适合考研英语阅读、写作和长难句突破。",
        "cover_color": "#17C7A3",
        "target_count": 5500,
        "offset": 2500,
    },
    {
        "name": "雅思场景词汇",
        "legacy_names": ["雅思场景词汇测试集"],
        "category": "IELTS",
        "level": "强化",
        "description": "适合雅思阅读和写作场景的词汇训练。",
        "cover_color": "#FF7A59",
        "target_count": 3500,
        "offset": 5000,
    },
]

STOP_WORDS = {
    "the", "of", "and", "to", "a", "in", "for", "is", "on", "that", "by", "this", "with",
    "i", "you", "it", "not", "or", "be", "are", "from", "at", "as", "your", "all", "have",
    "new", "more", "an", "was", "we", "will", "home", "can", "us", "about", "if", "my", "has",
    "but", "our", "one", "other", "do", "no", "information", "time", "they", "site", "he",
    "up", "may", "what", "which", "their", "news", "out", "use", "any", "there", "see", "only",
    "so", "his", "when", "contact", "here", "business", "who", "web", "also", "now", "help",
    "get", "pm", "view", "online", "first", "am", "been", "would", "how", "were", "me", "services",
    "some", "these", "click", "its", "like", "service", "than", "find", "price", "date", "back",
}


def load_word_pool():
    if not RESOURCE_FILE.exists():
        raise FileNotFoundError(f"resource file not found: {RESOURCE_FILE}")

    words = []
    with RESOURCE_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            word = line.strip().lower()
            if not word or word in STOP_WORDS:
                continue
            if not word.isalpha():
                continue
            if len(word) < 4 or len(word) > 12:
                continue
            words.append(word)
    return words


def detect_part_of_speech(word):
    if word.endswith(("tion", "sion", "ment", "ness", "ity", "ship")):
        return "n."
    if word.endswith(("able", "ible", "ous", "ive", "al", "ful", "less", "ic", "ary")):
        return "adj."
    if word.endswith(("ize", "ise", "ify", "ate", "en")):
        return "v."
    if word.endswith("ly"):
        return "adv."
    return "n."


def build_meaning(word, part_of_speech):
    if part_of_speech == "adj.":
        return f"与 {word} 相关的性质或状态（示例释义）"
    if part_of_speech == "v.":
        return f"表示与 {word} 相关的动作或行为（示例释义）"
    if part_of_speech == "adv.":
        return f"表示与 {word} 相关的方式或程度（示例释义）"
    return f"与 {word} 相关的事物或概念（示例释义）"


def build_example(word):
    sentence = f"The word {word} appears in this vocabulary book."
    translation = f"单词 {word} 已加入当前词书，供学习和测试使用。"
    return sentence, translation


def get_or_upgrade_book(config):
    candidates = [config["name"]] + config["legacy_names"]
    book = Book.objects.filter(name__in=candidates).order_by("id").first()
    if not book:
        book = Book.objects.create(
            name=config["name"],
            category=config["category"],
            level=config["level"],
            description=config["description"],
            status="active",
            cover_color=config["cover_color"],
        )
        return book

    updated = False
    for field, value in (
        ("name", config["name"]),
        ("category", config["category"]),
        ("level", config["level"]),
        ("description", config["description"]),
        ("status", "active"),
        ("cover_color", config["cover_color"]),
    ):
        if getattr(book, field) != value:
            setattr(book, field, value)
            updated = True
    if updated:
        book.save()
    return book


def chunk_list(items, size):
    for index in range(0, len(items), size):
        yield items[index:index + size]


def expand_book_words(book, config, word_pool):
    existing_words = list(book.words.values_list("word", flat=True))
    existing_set = set(existing_words)
    target_count = config["target_count"]
    current_count = len(existing_words)
    if current_count >= target_count:
        book.word_count = current_count
        book.save(update_fields=["word_count", "updated_at"])
        return 0

    need_count = target_count - current_count
    next_order = (book.words.order_by("-order_in_book").values_list("order_in_book", flat=True).first() or 0) + 1
    start_offset = config["offset"]

    selected_words = []
    for word in word_pool[start_offset:]:
        if word in existing_set:
            continue
        selected_words.append(word)
        existing_set.add(word)
        if len(selected_words) >= need_count:
            break

    if len(selected_words) < need_count:
        for word in word_pool:
            if word in existing_set:
                continue
            selected_words.append(word)
            existing_set.add(word)
            if len(selected_words) >= need_count:
                break

    created_total = 0
    for batch in chunk_list(selected_words, 500):
        word_objects = []
        for word_text in batch:
            pos = detect_part_of_speech(word_text)
            sentence, translation = build_example(word_text)
            word_objects.append(
                Word(
                    book=book,
                    word=word_text,
                    phonetic="",
                    part_of_speech=pos,
                    meaning_cn=build_meaning(word_text, pos),
                    example_sentence=sentence,
                    example_translation=translation,
                    audio_url="",
                    difficulty=2,
                    synonyms="",
                    order_in_book=next_order,
                )
            )
            next_order += 1

        Word.objects.bulk_create(word_objects, batch_size=500)
        created_words = list(Word.objects.filter(book=book, word__in=batch).only("id", "word", "example_sentence", "example_translation"))
        example_objects = [
            WordExample(
                word=item,
                example_sentence=item.example_sentence,
                example_translation=item.example_translation,
                sort_order=1,
            )
            for item in created_words
        ]
        WordExample.objects.bulk_create(example_objects, batch_size=500)
        created_total += len(created_words)

    book.word_count = book.words.count()
    book.save(update_fields=["word_count", "updated_at"])
    return created_total


@transaction.atomic
def main():
    word_pool = load_word_pool()
    summary = []
    for config in BOOK_TARGETS:
        book = get_or_upgrade_book(config)
        before_count = book.words.count()
        created_count = expand_book_words(book, config, word_pool)
        summary.append(
            {
                "name": book.name,
                "before_count": before_count,
                "created_count": created_count,
                "final_count": book.word_count,
            }
        )

    print({"books": summary})


if __name__ == "__main__":
    main()
