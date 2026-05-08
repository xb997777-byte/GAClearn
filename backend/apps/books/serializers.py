from rest_framework import serializers

from .models import Book, Word, WordExample


class WordExampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = WordExample
        fields = ("id", "example_sentence", "example_translation", "sort_order")


class WordSerializer(serializers.ModelSerializer):
    examples = WordExampleSerializer(many=True, read_only=True)

    class Meta:
        model = Word
        fields = (
            "id",
            "book",
            "word",
            "phonetic",
            "part_of_speech",
            "meaning_cn",
            "example_sentence",
            "example_translation",
            "audio_url",
            "difficulty",
            "synonyms",
            "order_in_book",
            "examples",
        )


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ("id", "name", "category", "level", "description", "word_count", "status", "cover_color")

