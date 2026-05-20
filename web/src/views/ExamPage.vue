<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import PageSection from '../components/PageSection.vue';
import { generatePlacementTest, generateTest, submitPlacementTest, submitTest } from '../services/exams';

const route = useRoute();

const mode = computed(() => (route.query.mode === 'placement' ? 'placement' : 'practice'));
const loading = ref(true);
const testMeta = ref(null);
const questions = ref([]);
const currentIndex = ref(0);
const selectedValue = ref('');
const answersMap = ref({});
const result = ref(null);
const pageError = ref('');

const currentQuestion = computed(() => questions.value[currentIndex.value] || null);
const progressPercent = computed(() => {
  if (!questions.value.length) {
    return 0;
  }
  return Math.round(((currentIndex.value + 1) / questions.value.length) * 100);
});

const resultSummary = computed(() => {
  if (!result.value) {
    return null;
  }
  const score = Number(result.value.score || 0);
  const tone = score >= 85 ? '表现很稳' : score >= 60 ? '基础不错' : '还可以继续补强';
  return {
    tone,
    accuracy: result.value.question_count
      ? `${result.value.correct_count}/${result.value.question_count}`
      : '0/0',
  };
});

async function loadTest() {
  loading.value = true;
  pageError.value = '';
  const data = mode.value === 'placement'
    ? await generatePlacementTest({ question_count: 18 })
    : await generateTest({ question_count: 12 });

  testMeta.value = {
    testId: data.test_id,
    sessionType: data.session_type,
    bookName: data.book?.name || '',
  };
  questions.value = data.questions || [];
  currentIndex.value = 0;
  selectedValue.value = '';
  answersMap.value = {};
  result.value = null;
  loading.value = false;
}

function restoreSavedAnswer() {
  if (!currentQuestion.value) {
    selectedValue.value = '';
    return;
  }
  const saved = answersMap.value[currentQuestion.value.question_id];
  if (!saved) {
    selectedValue.value = '';
    return;
  }
  if (currentQuestion.value.answer_mode === 'input') {
    selectedValue.value = saved.submitted_text || '';
    return;
  }
  const optionKey = saved.selected_option;
  selectedValue.value = currentQuestion.value.options?.[optionKey] || '';
}

function saveCurrentAnswer() {
  if (!currentQuestion.value) {
    return false;
  }
  const answerValue = String(selectedValue.value || '').trim();
  if (!answerValue) {
    pageError.value = currentQuestion.value.answer_mode === 'input' ? '请先输入答案。' : '请先选择一个选项。';
    return false;
  }

  pageError.value = '';
  answersMap.value[currentQuestion.value.question_id] = {
    question_id: currentQuestion.value.question_id,
    selected_option: currentQuestion.value.answer_mode === 'choice'
      ? Object.keys(currentQuestion.value.options || {}).find((key) => currentQuestion.value.options[key] === selectedValue.value) || ''
      : '',
    submitted_text: currentQuestion.value.answer_mode === 'input' ? answerValue : '',
  };
  return true;
}

async function submitCurrentTest() {
  const answers = Object.values(answersMap.value);
  result.value = mode.value === 'placement'
    ? await submitPlacementTest({ test_id: testMeta.value.testId, answers })
    : await submitTest({ test_id: testMeta.value.testId, answers });
}

async function handleNext() {
  if (!saveCurrentAnswer()) {
    return;
  }
  if (currentIndex.value + 1 >= questions.value.length) {
    await submitCurrentTest();
    return;
  }
  currentIndex.value += 1;
  restoreSavedAnswer();
}

function handlePrevious() {
  if (currentIndex.value === 0) {
    return;
  }
  saveCurrentAnswer();
  currentIndex.value -= 1;
  restoreSavedAnswer();
}

onMounted(loadTest);
</script>

<template>
  <div class="page-stack">
    <PageSection v-if="loading" :title="mode === 'placement' ? '分级测试' : '词汇测试'" subtitle="正在为网页端加载测试题目..." />

    <template v-else-if="result">
      <PageSection :title="mode === 'placement' ? '分级测试结果' : '测试结果'" subtitle="测试结果已经写回同一份后端学习数据。">
        <div class="result-card">
          <div class="action-card-title">{{ resultSummary?.tone || '测试完成' }}</div>
          <div class="action-card-description">
            正确率 {{ resultSummary?.accuracy }} · 得分 {{ result.score }} 分
          </div>
          <div class="info-grid compact-grid">
            <article class="info-card">
              <div class="info-label">正确题数</div>
              <div class="info-value">{{ result.correct_count }}</div>
            </article>
            <article class="info-card">
              <div class="info-label">总题数</div>
              <div class="info-value">{{ result.question_count }}</div>
            </article>
            <article class="info-card">
              <div class="info-label">测试类型</div>
              <div class="info-value">{{ result.session_type === 'placement' ? '分级测试' : '词汇测试' }}</div>
            </article>
            <article v-if="result.cefr_level" class="info-card">
              <div class="info-label">建议等级</div>
              <div class="info-value">{{ result.cefr_level }}</div>
            </article>
          </div>

          <div v-if="result.recommendation" class="list-stack">
            <div v-if="result.recommendation.focus" class="list-line">
              <strong>下一步重点</strong>
              <span class="line-meta">{{ result.recommendation.focus }}</span>
            </div>
            <div v-if="result.recommendation.daily_target" class="list-line">
              <strong>建议每日目标</strong>
              <span class="line-meta">{{ result.recommendation.daily_target }} 个新词</span>
            </div>
            <div v-if="result.recommendation.book?.name" class="list-line">
              <strong>建议词书</strong>
              <span class="line-meta">{{ result.recommendation.book.name }}</span>
            </div>
          </div>

          <div class="button-row">
            <button class="primary-button" type="button" @click="loadTest">再来一轮</button>
          </div>
        </div>
      </PageSection>
    </template>

    <template v-else-if="currentQuestion">
      <PageSection
        :title="mode === 'placement' ? '分级测试' : '词汇测试'"
        :subtitle="`${testMeta?.bookName || '智能组卷'} · 第 ${currentIndex + 1} / ${questions.length} 题`"
      >
        <div class="progress-strip">
          <div class="progress-strip-bar" :style="{ width: `${progressPercent}%` }"></div>
        </div>

        <div class="question-panel">
          <div class="chip-row compact">
            <span class="chip-light">{{ currentQuestion.question_type }}</span>
            <span class="chip-light">{{ currentQuestion.cefr_tag }}</span>
            <span class="chip-light">{{ currentQuestion.answer_mode === 'input' ? '输入题' : '选择题' }}</span>
          </div>
          <div class="question-stem">{{ currentQuestion.stem }}</div>

          <div v-if="currentQuestion.answer_mode === 'input'">
            <input v-model="selectedValue" class="text-input" placeholder="输入你的答案" />
          </div>

          <div v-else class="option-grid">
            <button
              v-for="(value, key) in currentQuestion.options"
              :key="key"
              class="option-card"
              :class="{ active: selectedValue === value }"
              type="button"
              @click="selectedValue = value"
            >
              <strong>{{ key }}</strong>
              <span>{{ value }}</span>
            </button>
          </div>
        </div>

        <div class="button-row">
          <button class="ghost-button" type="button" :disabled="currentIndex === 0" @click="handlePrevious">上一题</button>
          <button class="primary-button" type="button" @click="handleNext">
            {{ currentIndex + 1 >= questions.length ? '提交测试' : '下一题' }}
          </button>
        </div>

        <div v-if="pageError" class="notice error">{{ pageError }}</div>
      </PageSection>
    </template>
  </div>
</template>
