const booksApi = require('../../services/modules/books');
const router = require('../../utils/router');
const { withThemePage } = require('../../utils/theme-manager');

function buildUniqueOptions(list, field) {
  const values = [];
  (list || []).forEach((item) => {
    const value = String(item[field] || '').trim();
    if (value && values.indexOf(value) === -1) {
      values.push(value);
    }
  });
  return values;
}

function decorateOptions(values, activeValue) {
  return [{ label: '全部', value: '' }]
    .concat(values.map((value) => ({ label: value, value })))
    .map((item) => ({
      ...item,
      className: item.value === activeValue ? 'filter-chip active' : 'filter-chip'
    }));
}

Page(withThemePage({
  data: {
    books: [],
    categoryOptions: [],
    levelOptions: [],
    selectedCategory: '',
    selectedLevel: '',
    searchKeyword: '',
    activeKeyword: '',
    resultSummaryText: '正在加载词书',
    loading: false
  },

  onShow() {
    getApp().setTabBarSelected(1);
    this.initializePage();
  },

  async initializePage() {
    await Promise.all([
      this.loadFilterOptions(),
      this.loadBooks()
    ]);
  },

  async loadFilterOptions() {
    try {
      const data = await booksApi.listBooks({ page: 1, page_size: 100 });
      const list = data.list || [];
      this.setData({
        categoryOptions: decorateOptions(buildUniqueOptions(list, 'category'), this.data.selectedCategory),
        levelOptions: decorateOptions(buildUniqueOptions(list, 'level'), this.data.selectedLevel)
      });
    } catch (error) {
      this.setData({
        categoryOptions: decorateOptions([], this.data.selectedCategory),
        levelOptions: decorateOptions([], this.data.selectedLevel)
      });
    }
  },

  buildBookQuery() {
    const params = {
      page: 1,
      page_size: 50
    };
    if (this.data.selectedCategory) {
      params.category = this.data.selectedCategory;
    }
    if (this.data.selectedLevel) {
      params.level = this.data.selectedLevel;
    }
    if (this.data.activeKeyword) {
      params.keyword = this.data.activeKeyword;
    }
    return params;
  },

  refreshOptionState() {
    this.setData({
      categoryOptions: decorateOptions(
        this.data.categoryOptions.filter((item) => item.value).map((item) => item.value),
        this.data.selectedCategory
      ),
      levelOptions: decorateOptions(
        this.data.levelOptions.filter((item) => item.value).map((item) => item.value),
        this.data.selectedLevel
      )
    });
  },

  async loadBooks() {
    this.setData({ loading: true });
    try {
      const data = await booksApi.listBooks(this.buildBookQuery());
      const books = data.list || [];
      const total = data.pagination ? data.pagination.total : books.length;
      const hasFilter = !!(this.data.selectedCategory || this.data.selectedLevel || this.data.activeKeyword);
      this.setData({
        books,
        resultSummaryText: hasFilter ? `筛选到 ${total} 本词书` : `共 ${total} 本可用词书`,
        loading: false
      });
    } catch (error) {
      this.setData({ loading: false });
      wx.showToast({ title: '加载词书失败', icon: 'none' });
    }
  },

  handleKeywordInput(event) {
    this.setData({
      searchKeyword: event.detail.value || ''
    });
  },

  handleSearchConfirm() {
    this.setData({
      activeKeyword: this.data.searchKeyword.trim()
    });
    this.loadBooks();
  },

  handleCategoryTap(event) {
    const value = event.currentTarget.dataset.value || '';
    this.setData({ selectedCategory: value });
    this.refreshOptionState();
    this.loadBooks();
  },

  handleLevelTap(event) {
    const value = event.currentTarget.dataset.value || '';
    this.setData({ selectedLevel: value });
    this.refreshOptionState();
    this.loadBooks();
  },

  handleClearFilters() {
    this.setData({
      selectedCategory: '',
      selectedLevel: '',
      searchKeyword: '',
      activeKeyword: ''
    });
    this.refreshOptionState();
    this.loadBooks();
  },

  handleChoose(event) {
    const { bookId } = event.currentTarget.dataset;
    router.go(`/pages/plan/index?bookId=${bookId}`);
  }
}));
