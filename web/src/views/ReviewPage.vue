<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import PageSection from '../components/PageSection.vue';
import { speakText } from '../lib/speech';
import { getReviewTasks, submitReview } from '../services/review';
import { useSessionStore } from '../stores/session';

const router = useRouter();
const sessionStore = useSessionStore();

const loading = ref(true);
const sessionId = ref(null);
const list = ref([]);
const currentIndex = ref(0);
const selectedValue = ref('');
const answerFeedback = ref(null);
const submitting = ref(false);
const pageError = ref('');

const currentQuestion = computed(() => list.value[currentIndex.value] || null);
const currentOptions = computed(() => (currentQuestion.value && currentQuestion.value.options) || []);
const promptLabel = computed(() => {
  const type = currentQuestion.value?.question_type || '';
  if (type === 'word_to_meaning') return '看单词，选正确释义';
  if (type === 'meaning_to_word') return '看中文，选正确单词';
  if (type === 'example_to_word') return '结合例句，选缺失单词';
  if (type === 'spelling') return '根据中文，拼出完整单词';
  if (type === 'listening_to_word') return '听发音，选正确单词';
  return '完成这道复习题';
});

async function loadTasks() {
  loading.value = true;
  try {
    const data = await getReviewTasks({
      limit: Number(sessionStore.settings.review_batch_size || 8),
    });
    sessionId.value = data.session_id;
    list.value = data.list || [];
    currentIndex.value = 0;
    selectedValue.value = '';
    answerFeedback.value = null;
    pageError.value = '';
  } finally {
    loading.value = false;
  }
}

async function playPrompt() {
  if (!currentQuestion.value || !currentQuestion.value.speech_text) {
    return;
  }
  await speakText(currentQuestion.value.speech_text, {
    lang: currentQuestion.value.speech_lang || 'en-US',
  });
}

async function playFeedbackExample() {
  if (!answerFeedback.value?.example_sentence) {
    return;
  }
  await speakText(answerFeedback.value.example_sentence, {
    lang: answerFeedback.value.speech_lang || 'en-US',
  });
}

async function submitCurrent() {
  if (!currentQuestion.value) {
    return;
  }
  if (submitting.value || answerFeedback.value) {
    return;
  }
  pageError.value = '';
  const answerValue = String(selectedValue.value || '').trim();
  if (!answerValue) {
    pageError.value = currentQuestion.value.answer_mode === 'input' ? '请先输入答案。' : '请先选择一个答案。';
    return;
  }

  submitting.value = true;
  const payload = {
    session_id: sessionId.value,
    answers: [
      {
        word_id: currentQuestion.value.word_id,
        user_answer: answerValue,
        question_type: currentQuestion.value.question_type,
      },
    ],
  };
  try {
    const result = await submitReview(payload);
    const answerItem = result?.answers?.[0] || null;
    answerFeedback.value = answerItem
      ? {
          ...(answerItem.answer_feedback || {}),
          is_correct: !!answerItem.is_correct,
          correct_answer: answerItem.correct_answer,
          user_answer: answerItem.user_answer,
          word: answerItem.word,
        }
      : null;
    if (answerFeedback.value?.example_sentence) {
      playFeedbackExample().catch(() => {
        // ignore audio failure
      });
    }
  } finally {
    submitting.value = false;
  }
}

async function nextQuestion() {
  if (currentIndex.value + 1 >= list.value.length) {
    router.push('/web/home');
    return;
  }
  currentIndex.value += 1;
  selectedValue.value = '';
  answerFeedback.value = null;
  pageError.value = '';
}

onMounted(loadTasks);
</script>

<template>
  <div class="page-stack">
    <PageSection v-if="loading" title="复习" subtitle="正在加载复习任务..." />

    <template v-else-if="currentQuestion">
      <PageSection tone="hero">
        <div class="hero-wrap compact">
          <div>
            <div class="hero-kicker">复习进度</div>
            <div class="hero-title">{{ currentIndex + 1 }} / {{ list.length }}</div>
            <div class="hero-copy">{{ promptLabel }}</div>
          </div>
          <div class="button-row">
            <button class="ghost-button light" type="button" @click="playPrompt">播放题目</button>
          </div>
        </div>
      </PageSection>

      <PageSection :title="currentQuestion.stem || '当前题目'" :subtitle="currentQuestion.helper_text || ''">
        <div class="question-panel">
          <div class="progress-strip">
            <div class="progress-strip-bar" :style="{ width: `${((currentIndex + 1) / Math.max(list.length, 1)) * 100}%` }"></div>
          </div>
          <div class="chip-row compact">
            <span class="chip-light">{{ currentQuestion.question_type || '复习题' }}</span>
            <span class="chip-light">{{ currentQuestion.answer_mode === 'input' ? '输入作答' : '选择作答' }}</span>
          </div>
        </div>

        <div v-if="currentQuestion.answer_mode === 'input'">
          <input v-model="selectedValue" class="text-input" placeholder="输入你的答案" />
        </div>
        <div v-else class="option-grid">
          <button
            v-for="item in currentOptions"
            :key="item.key"
            class="option-card"
            :class="{ active: selectedValue === item.value }"
            type="button"
            @click="selectedValue = item.value"
          >
            {{ item.value }}
          </button>
        </div>

        <div class="button-row">
          <button class="primary-button" type="button" :disabled="submitting || !!answerFeedback" @click="submitCurrent">
            {{ submitting ? '提交中...' : '提交答案' }}
          </button>
          <button class="ghost-button" type="button" @click="nextQuestion">下一题</button>
        </div>
        <div v-if="pageError" class="notice error">{{ pageError }}</div>

        <div v-if="answerFeedback" class="feedback-panel">
          <div class="feedback-title">{{ answerFeedback.is_correct ? '回答正确' : '回答有误' }}</div>
          <div class="feedback-copy">{{ answerFeedback.title || answerFeedback.explanation || '已记录本题结果。' }}</div>
          <div class="chip-row compact">
            <span class="chip-light">{{ answerFeedback.is_correct ? '这题已稳住' : '这题进入回收池' }}</span>
          </div>
          <div class="list-stack">
            <div class="list-line">
              <strong>正确答案</strong>
              <span class="line-meta">{{ answerFeedback.correct_answer || answerFeedback.word || '--' }}</span>
            </div>
            <div class="list-line">
              <strong>核心释义</strong>
              <span class="line-meta">{{ answerFeedback.meaning_cn || '--' }}</span>
            </div>
          </div>
          <div v-if="answerFeedback.example_sentence" class="example-card">
            <div class="example-en">{{ answerFeedback.example_sentence }}</div>
            <div class="example-cn">{{ answerFeedback.example_translation || '' }}</div>
          </div>
          <div v-if="answerFeedback.recovery_tip" class="notice">{{ answerFeedback.recovery_tip }}</div>
          <div v-if="answerFeedback.usage_tip" class="soft-caption">{{ answerFeedback.usage_tip }}</div>
        </div>
      </PageSection>
    </template>

    <PageSection v-else title="复习" subtitle="当前没有待复习任务。">
      <div class="empty-state">今天的复习已经清空了，可以回首页继续学习新词或进入 AI 中心。</div>
    </PageSection>
  </div>
</template>
