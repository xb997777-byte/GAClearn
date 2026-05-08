import argparse
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

from apps.grammar.data_builder import build_grammar_seed_data  # noqa: E402
from apps.grammar.models import GrammarAnnotation, GrammarLearningRecord, GrammarPoint, GrammarSentence  # noqa: E402


def seed(reset=True):
    payloads = build_grammar_seed_data()

    with transaction.atomic():
        if reset:
            GrammarLearningRecord.objects.all().delete()
            GrammarAnnotation.objects.all().delete()
            GrammarSentence.objects.all().delete()
            GrammarPoint.objects.all().delete()

        sentence_count = 0
        annotation_count = 0

        for point_payload in payloads:
            sentences = point_payload.pop("sentences")
            point = GrammarPoint.objects.create(**point_payload)

            for sentence_payload in sentences:
                annotations = sentence_payload.pop("annotations")
                sentence = GrammarSentence.objects.create(point=point, **sentence_payload)
                GrammarAnnotation.objects.bulk_create(
                    [
                        GrammarAnnotation(sentence=sentence, **annotation_payload)
                        for annotation_payload in annotations
                    ]
                )
                sentence_count += 1
                annotation_count += len(annotations)

    print(
        f"grammar seed complete: points={GrammarPoint.objects.count()}, "
        f"sentences={sentence_count}, annotations={annotation_count}"
    )


def main():
    parser = argparse.ArgumentParser(description="Seed grammar learning data")
    parser.add_argument("--no-reset", action="store_true", help="Do not clear existing grammar data before seeding")
    args = parser.parse_args()
    seed(reset=not args.no_reset)


if __name__ == "__main__":
    main()

