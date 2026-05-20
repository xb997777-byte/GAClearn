<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import PageSection from '../components/PageSection.vue';
import { playAudioUrl, speakText } from '../lib/speech';
import { addFavorite, getLearnWordDetail, removeFavorite } from '../services/learn';

const route = useRoute();
const word = ref(null);

const favoriteText = computed(() => (word.value?.progress?.is_favorite ? '已收藏' : '未收藏'));

async function loadWord() {
  const wordId = Number(route.params.id || 0);
  if (!wordId) {
    return;
  }
  word.value = await getLearnWordDetail(wordId);
}

async function handleFavoriteToggle() {
  if (!word.value) {
    return;
  }
  if (word.value.progress?.is_favorite) {
    await removeFavorite(word.value.id);
    word.value.progress.is_favorite = false;
    return;
  }
  await addFavorite({ word_id: word.value.id });
  if (!word.value.progress) {
    word.value.progress = {};
  }
  word.value.progress.is_favorite = true;
}

async function handlePlayWord() {
  const pronunciation = (word.value && word.value.pronunciation) || {};
  if (pronunciation.audio_url) {
    await playAudioUrl(pronunciation.audio_url);
    return;
  }
  await speakText(pronunciation.tts_text || word.value.word, { lang: 'en-US' });
}

async function handlePlayExample() {
  if (!word.value) {
    return;
  }
  await speakText(
    word.value.pronunciation?.example_tts_text ||
      word.value.example_sentence ||
      word.value.word,
    { lang: 'en-US' },
  );
}

onMounted(loadWord);
</script>

<template>
  <div class="page-stack">
    <PageSection v-if="word" :title="word.word" :subtitle="word.phonetic || word.pronunciation?.phonetic || ''">
      <div class="word-focus-panel">
        <div class="word-cn">{{ word.meaning_cn || word.meaning }}</div>
        <div class="word-detail-copy">{{ word.meaning_en || word.part_of_speech || '当前词条暂无补充英文说明。' }}</div>
        <div v-if="word.example_sentence" class="example-card">
          <div class="example-en">{{ word.example_sentence }}</div>
          <div class="example-cn">{{ word.example_translation || word.translation || '' }}</div>
        </div>
      </div>

      <div class="button-row">
        <button class="primary-button" type="button" @click="handlePlayWord">播放单词</button>
        <button class="ghost-button" type="button" @click="handlePlayExample">播放例句</button>
        <button class="ghost-button" type="button" @click="handleFavoriteToggle">{{ favoriteText }}</button>
      </div>
    </PageSection>
  </div>
</template>
