<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import InfoGrid from '../components/InfoGrid.vue';
import PageSection from '../components/PageSection.vue';
import { getWrongWordsReview } from '../services/ai';
import { deleteWrongWord, listWrongWords } from '../services/review';

const router = useRouter();
const list = ref([]);
const review = ref(null);
const loading = ref(false);

const summaryItems = computed(() => [
  { label: '当前错词', value: list.value.length, description: '还在回收队列里的薄弱词。' },
  { label: '优先回收', value: review.value?.priority_words?.length || 0, description: 'AI 认为最值得先处理的一批词。' },
  { label: '错误模式', value: review.value?.mistake_patterns?.length || 0, description: 'AI 总结出的重复性问题。' },
  { label: '行动步骤', value: review.value?.action_plan?.length || 0, description: '建议你按顺序执行的恢复动作。' },
]);

async function loadPage() {
  loading.value = true;
  try {
    const data = await listWrongWords();
    list.value = data.list || [];
    const coach = await getWrongWordsReview({ limit: 12 }).catch(() => null);
    review.value = coach?.review || null;
  } finally {
    loading.value = false;
  }
}

async function handleDelete(wordId) {
  await deleteWrongWord(wordId);
  await loadPage();
}

onMounted(loadPage);
</script>

<template>
  <div class="page-stack">
    <PageSection title="错词本" subtitle="网页端和小程序端共用同一份错词本，适合集中回收薄弱点。">
      <InfoGrid :items="summaryItems" />
    </PageSection>

    <PageSection v-if="list.length" title="错词列表" subtitle="先把词认清，再决定是回到学习页还是直接复习。">
      <div class="list-stack">
        <div v-for="item in list" :key="item.word_id || item.id" class="list-line interactive">
          <div @click="router.push(`/web/word/${item.word_id || item.id}`)">
            <strong>{{ item.word || item.word_text }}</strong>
            <span class="line-meta">{{ item.meaning_cn || item.meaning || '' }}</span>
            <span class="soft-caption">错误次数 {{ item.wrong_count || 0 }}</span>
          </div>
          <button class="ghost-button small" type="button" @click="handleDelete(item.word_id || item.id)">移除</button>
        </div>
      </div>
    </PageSection>
    <PageSection v-else-if="!loading" title="错词列表" subtitle="当前这份错词本是空的。">
      <div class="empty-state">目前没有活跃错词，这通常说明你最近的学习节奏比较稳，可以继续推进新词或开始小测。</div>
    </PageSection>

    <PageSection v-if="review" title="AI 错词复盘" subtitle="把错词薄弱点总结成人能直接执行的建议。">
      <div class="coach-panel">
        <div class="coach-headline">{{ review.headline }}</div>
        <div class="coach-copy">{{ review.summary }}</div>
        <div v-if="review.coach_line" class="coach-motivation">{{ review.coach_line }}</div>
      </div>

      <div v-if="review.mistake_patterns?.length" class="list-stack">
        <div v-for="item in review.mistake_patterns" :key="item.title || item.pattern || item" class="list-line">
          <strong>{{ item.title || item.pattern || '错误模式' }}</strong>
          <span class="line-meta">{{ item.summary || item.detail || item }}</span>
        </div>
      </div>

      <div v-if="review.priority_words?.length" class="chip-row">
        <span v-for="item in review.priority_words" :key="item.word || item" class="chip-light">{{ item.word || item }}</span>
      </div>

      <div v-if="review.action_plan?.length" class="list-stack">
        <div v-for="(item, index) in review.action_plan" :key="item" class="list-line">
          <strong>步骤 {{ index + 1 }}</strong>
          <span class="line-meta">{{ item }}</span>
        </div>
      </div>
    </PageSection>
  </div>
</template>
