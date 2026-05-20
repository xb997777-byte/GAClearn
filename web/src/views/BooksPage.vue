<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import PageSection from '../components/PageSection.vue';
import { listBooks } from '../services/books';

const router = useRouter();

const books = ref([]);
const loading = ref(false);
const searchKeyword = ref('');
const selectedCategory = ref('');
const selectedLevel = ref('');

const categoryOptions = computed(() => {
  const values = [];
  books.value.forEach((book) => {
    if (book.category && !values.includes(book.category)) {
      values.push(book.category);
    }
  });
  return values;
});

const levelOptions = computed(() => {
  const values = [];
  books.value.forEach((book) => {
    if (book.level && !values.includes(book.level)) {
      values.push(book.level);
    }
  });
  return values;
});

const filteredBooks = computed(() => books.value.filter((book) => {
  const keyword = searchKeyword.value.trim().toLowerCase();
  if (selectedCategory.value && book.category !== selectedCategory.value) {
    return false;
  }
  if (selectedLevel.value && book.level !== selectedLevel.value) {
    return false;
  }
  if (keyword && !`${book.name} ${book.description || ''}`.toLowerCase().includes(keyword)) {
    return false;
  }
  return true;
}));

async function loadBooksData() {
  loading.value = true;
  try {
    const data = await listBooks({ page: 1, page_size: 100 });
    books.value = data.list || [];
  } finally {
    loading.value = false;
  }
}

function handleChoose(bookId) {
  router.push(`/web/plan?bookId=${bookId}`);
}

onMounted(loadBooksData);
</script>

<template>
  <div class="page-stack">
    <PageSection tone="hero">
      <div class="hero-wrap compact">
        <div>
          <div class="hero-kicker">词书选择</div>
          <div class="hero-title">先选对主词书，后面的计划、学习和 AI 才会真正顺手。</div>
          <div class="hero-copy">词书一旦切换，今天的学习节奏也会一起重算，所以这里建议你把主线素材先定下来。</div>
        </div>
      </div>
    </PageSection>

    <PageSection title="选择适合你的词书" subtitle="按照当前目标和考试阶段选择主词书，后续可以随时切换。">
      <div class="toolbar-grid">
        <input v-model="searchKeyword" class="text-input" placeholder="搜索词书，例如 四级、雅思、高中" />
        <select v-model="selectedCategory" class="select-input">
          <option value="">全部考试/阶段</option>
          <option v-for="item in categoryOptions" :key="item" :value="item">{{ item }}</option>
        </select>
        <select v-model="selectedLevel" class="select-input">
          <option value="">全部难度层级</option>
          <option v-for="item in levelOptions" :key="item" :value="item">{{ item }}</option>
        </select>
      </div>
      <div class="soft-caption">{{ loading ? '正在加载词书...' : `共找到 ${filteredBooks.length} 本词书` }}</div>
    </PageSection>

    <PageSection tone="soft">
      <div v-if="filteredBooks.length" class="action-card-list">
        <article v-for="book in filteredBooks" :key="book.id" class="action-card">
          <div class="action-card-title">{{ book.name }}</div>
          <div class="action-card-description">{{ book.description }}</div>
          <div class="chip-row">
            <span class="chip-light">{{ book.category }}</span>
            <span class="chip-light">{{ book.level }}</span>
            <span class="chip-light">{{ book.word_count }} 词</span>
          </div>
          <div class="button-row">
            <button class="primary-button" type="button" @click="handleChoose(book.id)">使用这本词书</button>
          </div>
        </article>
      </div>
      <div v-else class="empty-state">暂无符合当前筛选条件的词书。</div>
    </PageSection>
  </div>
</template>
