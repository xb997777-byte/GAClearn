from django.contrib import admin

from .models import Book, Word, WordExample

admin.site.register(Book)
admin.site.register(Word)
admin.site.register(WordExample)

# Register your models here.
