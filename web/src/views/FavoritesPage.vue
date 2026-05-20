<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import InfoGrid from '../components/InfoGrid.vue';
import PageSection from '../components/PageSection.vue';
import { listFavorites, removeFavorite } from '../services/learn';

const router = useRouter();
const list = ref([]);

const summaryItems = computed(() => {
  const books = new Set(list.value.map((item) => item.word?.book?.name).filter(Boolean));
  const withExample = list.value.filter((item) => item.word?.example_sentence).length;
  return [
    { label: '收藏总数', value: list.value.length, description: '你主动标记下来的重点词。' },
    { label: '覆盖词书', value: books.size, description: '当前收藏分布到多少本词书。' },
    { label: '带例句词', value: withExample, description: '复习时更容易连同语境一起回忆。' },
    { label: '可回看词', value: list.value.length, description: '随时可回到单词详情继续学习。' },
  ];
});

async function loadPage() {
  const data = await listFavorites();
  list.value = data.list || [];
}

async function handleDelete(wordId) {
  await removeFavorite(wordId);
  await loadPage();
}

onMounted(loadPage);
</script>

<template>
  <div class="page-stack">
    <PageSection title="收藏夹" subtitle="把你主动留下的高价值单词整理在一起，网页端也能继续回看。">
      <InfoGrid :items="summaryItems" />
    </PageSection>

    <PageSection v-if="list.length" title="收藏单词" subtitle="适合集中看常考词、常忘词和你想反复记住的词。">
      <div class="list-stack">
        <div v-for="item in list" :key="item.id" class="list-line interactive">
          <div @click="router.push(`/web/word/${item.word?.id}`)">
            <strong>{{ item.word?.word || '未命名单词' }}</strong>
            <span class="line-meta">{{ item.word?.meaning_cn || item.word?.meaning || '' }}</span>
            <span class="soft-caption">{{ item.word?.part_of_speech || '' }}{{ item.word?.book?.name ? ` · ${item.word.book.name}` : '' }}</span>
          </div>
          <button class="ghost-button small" type="button" @click="handleDelete(item.word?.id)">取消收藏</button>
        </div>
      </div>
    </PageSection>

    <PageSection v-else title="收藏单词" subtitle="当前还没有收藏内容。">
      <div class="empty-state">当你在学习页或单词详情里收藏单词后，这里会自动同步显示，方便你跨端继续回看。</div>
    </PageSection>
  </div>
</template>
