<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import PageSection from '../components/PageSection.vue';
import { getGrammarGuide } from '../services/ai';

const route = useRoute();
const router = useRouter();
const guide = ref(null);

const pointId = computed(() => String(route.params.volumeId || ''));
const point = computed(() => {
  const items = guide.value?.recommended_points || [];
  return items.find((item) => String(item.point_id || item.sentence_id || item.id) === pointId.value) || null;
});

async function loadGuide() {
  guide.value = await getGrammarGuide().catch(() => null);
}

onMounted(loadGuide);
</script>

<template>
  <div class="page-stack">
    <PageSection
      :title="point?.title || '语法分册'"
      :subtitle="point?.reason || point?.learning_tip || '继续查看这一条语法建议的学习重点。'"
    >
      <div v-if="point" class="page-stack">
        <div class="result-card">
          <div class="action-card-title">{{ point.title }}</div>
          <div class="action-card-description">{{ point.reason || point.learning_tip || '这条建议已经纳入当前语法路线。' }}</div>
          <div class="chip-row">
            <span class="chip-light">{{ point.category || '语法点' }}</span>
            <span class="chip-light">{{ point.difficulty_label || '当前阶段推荐' }}</span>
          </div>
        </div>

        <div v-if="point.sample_sentence" class="result-card">
          <div class="action-card-title">示例句</div>
          <div class="example-en">{{ point.sample_sentence }}</div>
        </div>

        <div class="button-row">
          <button class="primary-button" type="button" @click="router.push('/web/grammar/examples')">去句库继续练</button>
          <button class="ghost-button" type="button" @click="router.push('/web/grammar/guide')">返回总览</button>
        </div>
      </div>

      <div v-else class="empty-state">
        当前还没有匹配到这条语法建议，可以先回到总览重新选择。
      </div>
    </PageSection>
  </div>
</template>
