<script setup>
import { computed, ref } from 'vue';
import PageSection from '../components/PageSection.vue';
import { analyzeSentence } from '../services/grammar';

const sentence = ref('');
const result = ref(null);
const loading = ref(false);
const errorText = ref('');

const groupedAnnotations = computed(() => {
  const annotations = result.value?.annotations || [];
  return annotations.map((item) => ({
    title: item.text_span,
    subtitle: item.explanation || '',
    meta: [item.role_label, item.grammar_label].filter(Boolean).join(' · '),
    background: item.background || '',
    color: item.color || '',
  }));
});

async function handleAnalyze() {
  if (!String(sentence.value || '').trim()) {
    errorText.value = '请先输入一句英文，再开始拆句。';
    return;
  }
  loading.value = true;
  errorText.value = '';
  try {
    result.value = await analyzeSentence(sentence.value);
  } catch (error) {
    errorText.value = error.message || '拆句失败，请稍后重试。';
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="page-stack">
    <PageSection title="自动拆句" subtitle="输入一句英文，网页端会把主干、从句、修饰层和中文解释清楚拆开。">
      <textarea v-model="sentence" class="text-area" rows="6" placeholder="输入你想分析的英文句子"></textarea>
      <div class="button-row">
        <button class="primary-button" type="button" :disabled="loading" @click="handleAnalyze">
          {{ loading ? '分析中...' : '开始拆句' }}
        </button>
      </div>
      <div v-if="errorText" class="notice error">{{ errorText }}</div>
    </PageSection>

    <PageSection v-if="result" :title="result.sentence" :subtitle="result.translation_cn || '已完成句子拆解'">
      <div class="result-card">
        <div class="action-card-title">一句话先看懂</div>
        <div class="action-card-description">{{ result.summary || result.analysis }}</div>
        <div class="info-grid compact-grid">
          <article class="info-card">
            <div class="info-label">主干</div>
            <div class="info-value">{{ result.main_structure || '--' }}</div>
          </article>
          <article class="info-card">
            <div class="info-label">难度</div>
            <div class="info-value">{{ result.difficulty_label || result.difficulty || '--' }}</div>
          </article>
          <article class="info-card">
            <div class="info-label">场景</div>
            <div class="info-value">{{ result.scene_tag || '自由输入' }}</div>
          </article>
          <article class="info-card">
            <div class="info-label">长难句</div>
            <div class="info-value">{{ result.is_long_sentence ? '是' : '否' }}</div>
          </article>
        </div>
      </div>

      <div v-if="result.complete_segments?.length" class="result-card">
        <div class="action-card-title">结构高亮</div>
        <div class="segment-flow">
          <span
            v-for="(segment, index) in result.complete_segments"
            :key="`${index}-${segment.text}`"
            class="segment-chip"
            :style="{ background: segment.background || '#ffffff', color: segment.color || '#344054' }"
          >
            {{ segment.text }}
          </span>
        </div>
      </div>

      <div v-if="groupedAnnotations.length" class="result-card">
        <div class="action-card-title">逐段解释</div>
        <div class="list-stack">
          <div v-for="item in groupedAnnotations" :key="item.title + item.meta" class="list-line">
            <strong :style="{ color: item.color || 'inherit' }">{{ item.title }}</strong>
            <span class="line-meta">{{ item.subtitle }}</span>
            <span v-if="item.meta" class="soft-caption">{{ item.meta }}</span>
          </div>
        </div>
      </div>

      <div v-if="result.grammar_tags?.length" class="chip-row">
        <span v-for="tag in result.grammar_tags" :key="tag" class="chip-light">{{ tag }}</span>
      </div>
    </PageSection>
  </div>
</template>
