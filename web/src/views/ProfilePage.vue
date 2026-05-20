<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import InfoGrid from '../components/InfoGrid.vue';
import PageSection from '../components/PageSection.vue';
import { getMe } from '../services/auth';
import { getOverview } from '../services/stats';
import { useSessionStore } from '../stores/session';

const router = useRouter();
const sessionStore = useSessionStore();
const user = ref(null);
const overview = ref(null);

const summaryItems = computed(() => [
  { label: '昵称', value: user.value?.nickname || '学习者', description: '当前网页端直接复用后端里的用户资料。' },
  { label: '每日目标', value: `${user.value?.settings?.daily_target || 0} 个`, description: '网页和小程序共用同一份学习节奏设置。' },
  { label: 'CEFR', value: user.value?.settings?.cefr_level || '--', description: user.value?.settings?.placement_completed_at ? '来自分级测试结果。' : '完成分级测试后会自动更新。' },
  { label: '个性化 RAG', value: user.value?.settings?.personalized_rag_status || 'idle', description: user.value?.settings?.personalized_rag_enabled ? '个人知识库已开启。' : '当前仍使用公共知识库优先回答。' },
  { label: '提醒订阅', value: user.value?.settings?.reminder_subscription_status || 'unknown', description: '网页端只展示状态，开启动作仍需在小程序内完成。' },
  { label: '上次登录', value: user.value?.last_login_at ? user.value.last_login_at.slice(0, 10) : '--', description: '帮助你确认最近一次学习触达。' },
]);

const assetItems = computed(() => [
  { label: '收藏单词', value: overview.value?.favorite_count ?? 0, description: '你主动保留下来的重点词。' },
  { label: '错词数量', value: overview.value?.wrong_word_count ?? 0, description: '当前仍在回收队列里的薄弱词。' },
  { label: '连续打卡', value: overview.value?.streak_days ?? 0, description: '持续性是多端学习最值钱的资产。' },
  { label: '语法进度', value: `${overview.value?.grammar_learning_percent ?? 0}%`, description: `已覆盖 ${overview.value?.grammar_studied_count ?? 0}/${overview.value?.grammar_sentence_count ?? 0} 条句子。` },
]);

const quickActions = computed(() => [
  {
    title: '学习设置',
    subtitle: '调整每日目标、音频、提醒和复习习惯',
    description: '这些设置会直接影响网页和小程序两端的学习体验。',
    badge: '同步',
    tags: ['节奏', '发音', '提醒'],
    actions: [{ label: '进入设置', primary: true, onClick: () => router.push('/web/settings') }],
  },
  {
    title: '收藏夹',
    subtitle: '回看你主动留下的高价值单词',
    description: '适合整理“常考 / 常忘 / 想重点记”的词汇。',
    badge: '沉淀',
    tags: ['重点词', '主动保留'],
    actions: [{ label: '打开收藏夹', primary: true, onClick: () => router.push('/web/favorites') }],
  },
  {
    title: '错词本',
    subtitle: '集中处理还没真正掌握的薄弱点',
    description: 'AI 会基于错词本给你恢复建议和优先顺序。',
    badge: '回收',
    tags: ['薄弱点', 'AI 建议'],
    actions: [{ label: '去错词本', primary: true, onClick: () => router.push('/web/wrong-words') }],
  },
]);

async function loadProfile() {
  const [userData, overviewData] = await Promise.all([
    getMe(),
    getOverview().catch(() => null),
  ]);
  user.value = userData;
  overview.value = overviewData;
  sessionStore.setUserInfo(userData);
  if (userData?.settings) {
    sessionStore.setSettings(userData.settings);
  }
}

onMounted(loadProfile);
</script>

<template>
  <div class="page-stack">
    <PageSection tone="hero">
      <div class="hero-wrap compact">
        <div>
          <div class="hero-kicker">个人学习空间</div>
          <div class="hero-title">{{ user?.nickname || '学习者' }}</div>
          <div class="hero-copy">这里把你的设置、学习资产和长期进度汇总成一个网页端学习档案。</div>
          <div class="chip-row">
            <span class="chip-light dark">{{ user?.settings?.cefr_level || '待分级' }}</span>
            <span class="chip-light dark">多端连续学习</span>
          </div>
        </div>
      </div>
    </PageSection>

    <PageSection title="学习档案" subtitle="资料展示直接复用后端当前用户档案。">
      <InfoGrid :items="summaryItems" />
    </PageSection>

    <PageSection v-if="overview" title="学习资产" subtitle="把这段时间积累下来的内容集中看清。">
      <InfoGrid :items="assetItems" />
    </PageSection>

    <PageSection title="快捷入口" subtitle="把个人常用工具集中到这里。">
      <div class="action-card-list">
        <article v-for="item in quickActions" :key="item.title" class="action-card">
          <div class="action-card-head">
            <div>
              <div class="action-card-title">{{ item.title }}</div>
              <div class="action-card-subtitle">{{ item.subtitle }}</div>
            </div>
            <div v-if="item.badge" class="soft-pill">{{ item.badge }}</div>
          </div>
          <div class="action-card-description">{{ item.description }}</div>
          <div v-if="item.tags?.length" class="chip-row">
            <span v-for="tag in item.tags" :key="tag" class="chip-light">{{ tag }}</span>
          </div>
          <div class="button-row">
            <button
              v-for="action in item.actions"
              :key="action.label"
              class="ghost-button"
              :class="{ primary: action.primary }"
              type="button"
              @click="action.onClick"
            >
              {{ action.label }}
            </button>
          </div>
        </article>
      </div>
    </PageSection>
  </div>
</template>
