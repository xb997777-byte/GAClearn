<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import PageSection from '../components/PageSection.vue';
import { getGrammarGuide } from '../services/ai';

const router = useRouter();
const guide = ref(null);

const recommendedPoints = computed(() => guide.value?.recommended_points || []);

async function loadGuide() {
  guide.value = await getGrammarGuide().catch(() => null);
}

function handleOpenPoint(point) {
  router.push(`/web/grammar/guide/${point.point_id || point.sentence_id || point.id}`);
}

onMounted(loadGuide);
</script>

<template>
  <div class="page-stack">
    <PageSection title="语法总览" subtitle="按照你当前阶段，把本周最值得补的语法点先排出来。">
      <div v-if="guide" class="result-card">
        <div class="action-card-title">{{ guide.headline || 'AI 语法总览' }}</div>
        <div class="action-card-description">{{ guide.summary || '已根据当前学习状态整理语法路线。' }}</div>
      </div>

      <div v-if="recommendedPoints.length" class="list-stack">
        <div
          v-for="item in recommendedPoints"
          :key="item.point_id || item.title"
          class="list-line interactive"
          @click="handleOpenPoint(item)"
        >
          <div>
            <strong>{{ item.title }}</strong>
            <span class="line-meta">{{ item.reason || item.learning_tip || '点击进入这一册继续查看。' }}</span>
          </div>
          <span class="soft-pill">{{ item.difficulty_label || item.category || '语法点' }}</span>
        </div>
      </div>

      <div v-else-if="guide" class="empty-state">当前还没有更多分册化建议，稍后可以重新生成。</div>
      <div v-else class="empty-state">当前还没有可展示的语法总览，可以稍后再试。</div>
    </PageSection>

    <PageSection v-if="guide?.evidence?.retrieval_hits?.length" title="推荐依据" subtitle="默认只保留简洁说明，更详细的技术信息仍收纳在高级区。">
      <div class="list-stack">
        <div v-for="item in guide.evidence.retrieval_hits" :key="item.title" class="list-line">
          <strong>{{ item.title }}</strong>
          <span class="line-meta">{{ item.reason }}</span>
          <span v-if="item.preview" class="soft-caption">{{ item.preview }}</span>
        </div>
      </div>

      <details class="details-box">
        <summary>查看详细分析</summary>
        <pre class="pre-block">{{ JSON.stringify(guide.evidence || guide, null, 2) }}</pre>
      </details>
    </PageSection>
  </div>
</template>
