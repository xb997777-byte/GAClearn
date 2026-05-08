from .models import Book, Word


def list_books(category=None, keyword=None, level=None):
    queryset = Book.objects.filter(status="active").exclude(category__iexact="demo").order_by("id")
    if category:
        queryset = queryset.filter(category__icontains=category)
    if keyword:
        queryset = queryset.filter(name__icontains=keyword)
    if level:
        queryset = queryset.filter(level__icontains=level)
    return queryset


def paginate_queryset(queryset, page=1, page_size=20):
    page = max(int(page), 1)
    page_size = min(max(int(page_size), 1), 500)
    start = (page - 1) * page_size
    end = start + page_size
    return queryset[start:end], queryset.count(), page, page_size


def get_book_detail(book_id):
    return Book.objects.prefetch_related("words").filter(id=book_id).first()


def list_book_words(book, page=1, page_size=20, keyword=None):
    queryset = book.words.all().order_by("order_in_book", "id")
    if keyword:
        queryset = queryset.filter(word__icontains=keyword)
    return paginate_queryset(queryset, page, page_size)


def get_word(word_id):
    return Word.objects.select_related("book").prefetch_related("examples").filter(id=word_id).first()
