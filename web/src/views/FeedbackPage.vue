<script setup>
import { reactive } from 'vue';
import PageSection from '../components/PageSection.vue';
import { submitFeedback } from '../services/auth';

const noticeText = reactive({
  success: '',
  error: '',
});

const form = reactive({
  category: 'experience',
  content: '',
  contact: '',
  page: 'web',
});

async function handleSubmit() {
  noticeText.success = '';
  noticeText.error = '';
  if (!String(form.content || '').trim()) {
    noticeText.error = '请先填写反馈内容。';
    return;
  }
  await submitFeedback(form);
  form.content = '';
  form.contact = '';
  noticeText.success = '反馈已提交，后端已经收到这条网页端意见。';
}
</script>

<template>
  <div class="page-stack">
    <PageSection title="意见反馈" subtitle="网页端的问题和体验建议也会写回同一套后端反馈表。">
      <div class="field-grid">
        <label class="field-stack">
          <span class="field-label">反馈类型</span>
          <select v-model="form.category" class="select-input">
            <option value="experience">使用体验</option>
            <option value="bug">问题反馈</option>
            <option value="content">内容纠错</option>
            <option value="ai">AI 功能</option>
            <option value="other">其他</option>
          </select>
        </label>
        <label class="field-stack span-2">
          <span class="field-label">联系方式</span>
          <input v-model="form.contact" class="text-input" placeholder="可选，方便后续联系" />
        </label>
      </div>
      <label class="field-stack">
        <span class="field-label">反馈内容</span>
        <textarea v-model="form.content" class="text-area" rows="8" placeholder="详细描述你遇到的问题或建议"></textarea>
      </label>
      <div class="button-row">
        <button class="primary-button" type="button" @click="handleSubmit">提交反馈</button>
      </div>
      <div v-if="noticeText.success" class="notice">{{ noticeText.success }}</div>
      <div v-if="noticeText.error" class="notice error">{{ noticeText.error }}</div>
    </PageSection>
  </div>
</template>
