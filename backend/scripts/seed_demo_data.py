import os
import sys
from pathlib import Path

import django

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from apps.books.models import Book, Word, WordExample  # noqa: E402


BOOK_NAME = "Demo Exam Vocabulary"

WORDS = [
    {
        "word": "resilient",
        "phonetic": "/rɪˈzɪliənt/",
        "part_of_speech": "adj.",
        "meaning_cn": "able to recover quickly; adaptable",
        "example_sentence": "A resilient student can recover after setbacks.",
        "example_translation": "有韧性的学生能在受挫后快速恢复。",
    },
    {
        "word": "concise",
        "phonetic": "/kənˈsaɪs/",
        "part_of_speech": "adj.",
        "meaning_cn": "brief but clear",
        "example_sentence": "Please write a concise summary.",
        "example_translation": "请写一段简洁的总结。",
    },
    {
        "word": "infer",
        "phonetic": "/ɪnˈfɜːr/",
        "part_of_speech": "v.",
        "meaning_cn": "to reach a conclusion from evidence",
        "example_sentence": "We can infer the answer from the context.",
        "example_translation": "我们可以从上下文推断答案。",
    },
    {
        "word": "coherent",
        "phonetic": "/koʊˈhɪrənt/",
        "part_of_speech": "adj.",
        "meaning_cn": "logical and well organized",
        "example_sentence": "Her speech was clear and coherent.",
        "example_translation": "她的演讲清晰而连贯。",
    },
    {
        "word": "cultivate",
        "phonetic": "/ˈkʌltɪveɪt/",
        "part_of_speech": "v.",
        "meaning_cn": "to develop or improve over time",
        "example_sentence": "Reading helps cultivate good habits.",
        "example_translation": "阅读有助于培养良好习惯。",
    },
]


def main():
    book, _ = Book.objects.get_or_create(
        name=BOOK_NAME,
        defaults={
            "category": "demo",
            "level": "starter",
            "description": "seed data for local api testing",
            "status": "active",
            "cover_color": "#4F7CFF",
        },
    )

    for index, payload in enumerate(WORDS, start=1):
        word, _ = Word.objects.get_or_create(
            book=book,
            word=payload["word"],
            defaults={
                "phonetic": payload["phonetic"],
                "part_of_speech": payload["part_of_speech"],
                "meaning_cn": payload["meaning_cn"],
                "example_sentence": payload["example_sentence"],
                "example_translation": payload["example_translation"],
                "difficulty": 1,
                "order_in_book": index,
            },
        )
        WordExample.objects.get_or_create(
            word=word,
            example_sentence=payload["example_sentence"],
            defaults={
                "example_translation": payload["example_translation"],
                "sort_order": 1,
            },
        )

    book.word_count = book.words.count()
    book.save(update_fields=["word_count", "updated_at"])
    print(f"seed complete: book_id={book.id}, word_count={book.word_count}")


if __name__ == "__main__":
    main()
