from django.db import models

from common.core.models import TimeStampedModel


class Book(TimeStampedModel):
    name = models.CharField(max_length=128, verbose_name="词书名称")
    category = models.CharField(max_length=64, verbose_name="分类")
    level = models.CharField(max_length=64, blank=True, default="", verbose_name="难度层级")
    description = models.TextField(blank=True, default="", verbose_name="简介")
    word_count = models.PositiveIntegerField(default=0, verbose_name="单词量")
    status = models.CharField(max_length=16, default="active", verbose_name="状态")
    cover_color = models.CharField(max_length=32, blank=True, default="", verbose_name="封面颜色")

    class Meta:
        db_table = "books"
        ordering = ["id"]
        verbose_name = "词书"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Word(TimeStampedModel):
    book = models.ForeignKey("books.Book", on_delete=models.CASCADE, related_name="words")
    word = models.CharField(max_length=128, verbose_name="单词")
    phonetic = models.CharField(max_length=128, blank=True, default="", verbose_name="音标")
    part_of_speech = models.CharField(max_length=64, blank=True, default="", verbose_name="词性")
    meaning_cn = models.CharField(max_length=255, verbose_name="中文释义")
    example_sentence = models.TextField(blank=True, default="", verbose_name="例句")
    example_translation = models.TextField(blank=True, default="", verbose_name="例句翻译")
    audio_url = models.URLField(blank=True, default="", verbose_name="音频地址")
    difficulty = models.PositiveSmallIntegerField(default=1, verbose_name="难度")
    synonyms = models.CharField(max_length=255, blank=True, default="", verbose_name="近义词")
    order_in_book = models.PositiveIntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "words"
        ordering = ["book_id", "order_in_book", "id"]
        verbose_name = "单词"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.word


class WordExample(TimeStampedModel):
    word = models.ForeignKey("books.Word", on_delete=models.CASCADE, related_name="examples")
    example_sentence = models.TextField(verbose_name="例句")
    example_translation = models.TextField(blank=True, default="", verbose_name="例句翻译")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "word_examples"
        ordering = ["sort_order", "id"]
        verbose_name = "单词例句"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.word.word} 示例"

# Create your models here.
