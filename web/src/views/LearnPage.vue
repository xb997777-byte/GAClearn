<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import PageSection from '../components/PageSection.vue';
import { addFavorite, createLearningRecord, getLearnWords } from '../services/learn';
import { playAudioUrl, speakText } from '../lib/speech';
import { useSessionStore } from '../stores/session';

const router = useRouter();
const sessionStore = useSessionStore();

const loading = ref(true);
const submitting = ref(false);
const words = ref([]);
const currentIndex = ref(0);
const targetCount = ref(0);
const meaningVisible = ref(false);
const decisionStage = ref('initial');
const messageText = ref('');

const currentWord = computed(() => words.value[currentIndex.value] || null);
const progressText = computed(() => `${Math.min(currentIndex.value + 1, targetCount.value || 0)} / ${targetCount.value || words.value.length || 0}`);
const primaryActionText = computed(() => (decisionStage.value === 'initial' ? '认识' : '确认认识并进入下一个'));
const secondaryActionText = computed(() => (decisionStage.value === 'initial' ? '不认识' : '确认不认识并进入下一个'));

async function loadWords() {
  loading.value = true;
  try {
    const data = await getLearnWords();
    words.value = data.list || [];
    targetCount.value = Number(data.target_count || words.value.length || 0);
    currentIndex.value = 0;
    meaningVisible.value = false;
    decisionStage.value = 'initial';
    messageText.value = '';
    await autoPlayWord();
  } finally {
    loading.value = false;
  }
}

async function autoPlayWord() {
  if (!currentWord.value || !sessionStore.settings.auto_play_audio) {
    return;
  }
  const pronunciation = currentWord.value.pronunciation || {};
  try {
    if (pronunciation.audio_url) {
      await playAudioUrl(pronunciation.audio_url);
      return;
    }
    await speakText(pronunciation.tts_text || currentWord.value.word, { lang: 'en-US' });
  } catch (error) {
    // ignore autoplay block
  }
}

async function playWord() {
  if (!currentWord.value) {
    return;
  }
  const pronunciation = currentWord.value.pronunciation || {};
  if (pronunciation.audio_url) {
    await playAudioUrl(pronunciation.audio_url);
    return;
  }
  await speakText(pronunciation.tts_text || currentWord.value.word, { lang: 'en-US' });
}

async function playExample() {
  if (!currentWord.value) {
    return;
  }
  const sentence =
    currentWord.value.pronunciation?.example_tts_text ||
    currentWord.value.example_sentence ||
    currentWord.value.word;
  await speakText(sentence, { lang: 'en-US' });
}

function revealMeaning() {
  meaningVisible.value = true;
  decisionStage.value = 'reviewing';
  messageText.value = '先看释义、英文说明和例句，再确认你是否真的记住了。';
  playExample().catch(() => {
    // ignore audio failure
  });
}

async function moveNext() {
  if (currentIndex.value + 1 >= words.value.length) {
    router.push('/web/home');
    return;
  }
  currentIndex.value += 1;
  meaningVisible.value = false;
  decisionStage.value = 'initial';
  messageText.value = '';
  await autoPlayWord();
}

async function submitLearning(actionType, result) {
  if (!currentWord.value) {
    return;
  }
  if (decisionStage.value === 'initial') {
    revealMeaning();
    return;
  }
  if (submitting.value) {
    return;
  }
  submitting.value = true;
  await createLearningRecord({
    word_id: currentWord.value.id,
    source: 'learn',
    action_type: actionType,
    result,
    duration: 8,
  });
  submitting.value = false;
  await moveNext();
}

async function handleFavorite() {
  if (!currentWord.value) {
    return;
  }
  await addFavorite({
    word_id: currentWord.value.id,
    note: '网页端学习时收藏',
  });
  messageText.value = '当前单词已加入收藏夹。';
}

function handleBackToDecision() {
  decisionStage.value = 'initial';
  meaningVisible.value = false;
  messageText.value = '';
}

function openDetail() {
  if (!currentWord.value) {
    return;
  }
  router.push(`/web/word/${currentWord.value.id}`);
}

onMounted(loadWords);
</script>

<template>
  <div class="page-stack">
    <PageSection v-if="loading" title="学习单词" subtitle="正在加载今天要学的新词..." />

    <template v-else-if="currentWord">
      <PageSection tone="hero">
        <div class="hero-wrap compact">
          <div>
            <div class="hero-kicker">今日学习进度</div>
            <div class="hero-title">{{ progressText }}</div>
            <div class="hero-copy">网页端沿用和小程序相同的学习记录写回逻辑。</div>
            <div class="chip-row">
              <span class="chip-light dark">{{ currentWord.part_of_speech || '词汇学习' }}</span>
              <span class="chip-light dark">{{ sessionStore.settings.auto_play_audio ? '自动发音已开' : '自动发音已关' }}</span>
            </div>
          </div>
          <div class="button-row">
            <button class="ghost-button light" type="button" @click="playWord">播放单词</button>
            <button class="ghost-button light" type="button" @click="playExample">播放例句</button>
          </div>
        </div>
      </PageSection>

      <PageSection :title="currentWord.word" :subtitle="currentWord.phonetic || currentWord.pronunciation?.phonetic || ''">
        <div class="word-focus-panel">
          <div class="chip-row compact">
            <span class="chip-light">{{ meaningVisible ? '已展开释义' : '先自己判断，再看讲解' }}</span>
          </div>
          <div class="word-cn">{{ currentWord.meaning_cn || currentWord.meaning || '暂未提供中文释义' }}</div>
          <div v-if="meaningVisible" class="word-detail-block">
            <div class="word-detail-title">英文释义与用法</div>
            <div class="word-detail-copy">{{ currentWord.meaning_en || currentWord.part_of_speech || '当前词条暂无补充说明。' }}</div>
            <div v-if="currentWord.example_sentence" class="example-card">
              <div class="example-en">{{ currentWord.example_sentence }}</div>
              <div class="example-cn">{{ currentWord.example_translation || currentWord.translation || '' }}</div>
            </div>
          </div>
        </div>

        <div v-if="messageText" class="notice">{{ messageText }}</div>

        <div class="button-row">
          <button class="primary-button" type="button" :disabled="submitting" @click="submitLearning('known', 'correct')">
            {{ primaryActionText }}
          </button>
          <button class="ghost-button" type="button" :disabled="submitting" @click="submitLearning('unknown', 'wrong')">
            {{ secondaryActionText }}
          </button>
          <button v-if="decisionStage === 'reviewing'" class="ghost-button" type="button" :disabled="submitting" @click="handleBackToDecision">
            返回重新判断
          </button>
          <button class="ghost-button" type="button" @click="handleFavorite">收藏</button>
          <button class="ghost-button" type="button" @click="openDetail">查看详情</button>
        </div>
      </PageSection>
    </template>

    <PageSection v-else title="学习单词" subtitle="今天的新词已经学完了。">
      <div class="empty-state">当前没有可学习的新词，可以返回首页或去复习页继续学习。</div>
    </PageSection>
  </div>
</template>
