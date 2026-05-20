<script setup>
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import PageSection from '../components/PageSection.vue';
import ActionCardList from '../components/ActionCardList.vue';
import { getProgress, listTopics } from '../services/grammar';

const router = useRouter();
const progress = ref(null);
const topicCount = ref(0);
const sentenceCount = ref(0);

const modules = [
  {
    title: '语法总览',
    subtitle: '像一本语法书一样，从简单到困难，按顺序带你把语法体系学完整。',
    description: '适合先打基础、按阶段系统推进的人。',
    tags: ['循序渐进', '分册学习', '基础到提高'],
    actions: [{ label: '查看总览', primary: true, onClick: () => router.push('/web/grammar/guide') }],
  },
  {
    title: '自动拆句',
    subtitle: '输入任意英文句子，立刻拆出主干、修饰层和中文解释。',
    description: '适合想查当前一句话到底怎么读的人。',
    tags: ['自由输入', '即时分析', '颜色标注'],
    actions: [{ label: '开始拆句', primary: true, onClick: () => router.push('/web/grammar/analyze') }],
  },
  {
    title: '例句学语法',
    subtitle: '按专题、难度和句库例句来学，把语法规则放进真实句子里。',
    description: '适合系统刷句子、按专题持续学习的人。',
    tags: ['句库学习', '主干视图', '专项练习'],
    actions: [{ label: '进入句库', primary: true, onClick: () => router.push('/web/grammar/examples') }],
  },
];

async function loadSummary() {
  const [progressData, topicsData] = await Promise.all([
    getProgress().catch(() => null),
    listTopics().catch(() => ({ list: [] })),
  ]);
  progress.value = progressData;
  const topics = (topicsData && topicsData.list) || [];
  topicCount.value = topics.length;
  sentenceCount.value = topics.reduce((sum, item) => sum + Number(item.sentence_count || 0), 0);
}

onMounted(loadSummary);
</script>

<template>
  <div class="page-stack">
    <PageSection title="语法中心" subtitle="把总览、拆句和句库学习放在一个网页工作台里。">
      <div class="info-grid">
        <article class="info-card">
          <div class="info-label">专题数量</div>
          <div class="info-value">{{ topicCount }}</div>
          <div class="info-description">当前语法专题总数</div>
        </article>
        <article class="info-card">
          <div class="info-label">句子数量</div>
          <div class="info-value">{{ sentenceCount }}</div>
          <div class="info-description">当前已入库的语法句子</div>
        </article>
        <article class="info-card">
          <div class="info-label">累计练习</div>
          <div class="info-value">{{ progress?.total_practice_count || 0 }}</div>
          <div class="info-description">你已经做过的语法练习次数</div>
        </article>
        <article class="info-card">
          <div class="info-label">学习进度</div>
          <div class="info-value">{{ progress?.learning_percent || 0 }}%</div>
          <div class="info-description">当前语法句库覆盖进度</div>
        </article>
      </div>
    </PageSection>

    <PageSection title="三条语法主路径" subtitle="保留和小程序一致的信息架构，只是改成更适合网页的大屏表达。">
      <ActionCardList :items="modules" />
    </PageSection>
  </div>
</template>
