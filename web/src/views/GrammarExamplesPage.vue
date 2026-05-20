<script setup>
import { computed, onMounted, ref } from 'vue';
import PageSection from '../components/PageSection.vue';
import { createRecord, listSentences, listTopics } from '../services/grammar';

const topics = ref([]);
const sentences = ref([]);
const selectedTopic = ref('');
const selectedSentence = ref(null);

const filteredSentences = computed(() => {
  if (!selectedTopic.value) {
    return sentences.value;
  }
  return sentences.value.filter((item) => String(item.topic_id || item.grammar_point_id || '') === String(selectedTopic.value));
});

async function loadPage() {
  const [topicsData, sentencesData] = await Promise.all([
    listTopics().catch(() => ({ list: [] })),
    listSentences({ page: 1, page_size: 50 }).catch(() => ({ list: [] })),
  ]);
  topics.value = topicsData.list || [];
  sentences.value = sentencesData.list || [];
}

async function handleMarkLearned(sentenceId) {
  await createRecord({
    sentence_id: sentenceId,
    action_type: 'understood',
  }).catch(() => null);
}

onMounted(loadPage);
</script>

<template>
  <div class="page-stack">
    <PageSection title="例句学语法" subtitle="把语法规则放进真实句子里，适合系统刷句子。">
      <div class="toolbar-grid">
        <select v-model="selectedTopic" class="select-input">
          <option value="">全部专题</option>
          <option v-for="item in topics" :key="item.id" :value="item.id">{{ item.title || item.name }}</option>
        </select>
      </div>

      <div v-if="filteredSentences.length" class="list-stack">
        <div
          v-for="item in filteredSentences"
          :key="item.id"
          class="list-line interactive column"
          @click="selectedSentence = item"
        >
          <strong>{{ item.sentence || item.text }}</strong>
          <span class="line-meta">{{ item.translation_cn || item.translation || item.explanation || '' }}</span>
          <span class="soft-caption">{{ item.point_title || item.grammar_point_title || item.category || '语法句子' }}</span>
          <button class="ghost-button small" type="button" @click.stop="handleMarkLearned(item.id)">标记已学</button>
        </div>
      </div>
      <div v-else class="empty-state">当前筛选条件下还没有句子，可以换一个语法专题继续看。</div>
    </PageSection>

    <PageSection v-if="selectedSentence" title="当前句子详情" subtitle="在网页端保留和小程序一致的句子学习流。">
      <div class="result-card">
        <div class="action-card-title">{{ selectedSentence.sentence || selectedSentence.text }}</div>
        <div class="action-card-description">{{ selectedSentence.translation_cn || selectedSentence.translation || '当前没有中文翻译。' }}</div>
        <div class="chip-row">
          <span class="chip-light">{{ selectedSentence.point_title || selectedSentence.grammar_point_title || '语法点' }}</span>
          <span v-if="selectedSentence.difficulty_label" class="chip-light">{{ selectedSentence.difficulty_label }}</span>
          <span v-if="selectedSentence.scene_tag" class="chip-light">{{ selectedSentence.scene_tag }}</span>
        </div>
      </div>

      <div v-if="selectedSentence.summary || selectedSentence.explanation || selectedSentence.analysis" class="result-card">
        <div class="action-card-title">学习提示</div>
        <div class="action-card-description">{{ selectedSentence.summary || selectedSentence.explanation || selectedSentence.analysis }}</div>
      </div>
    </PageSection>
  </div>
</template>
