import { createRouter, createWebHistory } from 'vue-router';
import { useSessionStore } from '../stores/session';
import LoginPage from '../views/LoginPage.vue';
import DashboardPage from '../views/DashboardPage.vue';
import BooksPage from '../views/BooksPage.vue';
import PlanPage from '../views/PlanPage.vue';
import LearnPage from '../views/LearnPage.vue';
import ReviewPage from '../views/ReviewPage.vue';
import GrammarHubPage from '../views/GrammarHubPage.vue';
import AiCenterPage from '../views/AiCenterPage.vue';
import ProfilePage from '../views/ProfilePage.vue';
import SettingsPage from '../views/SettingsPage.vue';
import StatsPage from '../views/StatsPage.vue';
import ExamPage from '../views/ExamPage.vue';
import WordDetailPage from '../views/WordDetailPage.vue';
import WrongWordsPage from '../views/WrongWordsPage.vue';
import FavoritesPage from '../views/FavoritesPage.vue';
import FeedbackPage from '../views/FeedbackPage.vue';
import GrammarAnalyzePage from '../views/GrammarAnalyzePage.vue';
import GrammarExamplesPage from '../views/GrammarExamplesPage.vue';
import GrammarGuidePage from '../views/GrammarGuidePage.vue';
import GrammarGuideVolumePage from '../views/GrammarGuideVolumePage.vue';

const routes = [
  {
    path: '/web/login',
    name: 'login',
    component: LoginPage,
    meta: {
      requiresAuth: false,
      hideChrome: true,
      title: '登录',
    },
  },
  {
    path: '/web',
    redirect: '/web/home',
  },
  {
    path: '/web/home',
    name: 'home',
    component: DashboardPage,
    meta: { requiresAuth: true, title: '首页', navGroup: 'main' },
  },
  {
    path: '/web/books',
    name: 'books',
    component: BooksPage,
    meta: { requiresAuth: true, title: '词书', navGroup: 'main' },
  },
  {
    path: '/web/plan',
    name: 'plan',
    component: PlanPage,
    meta: { requiresAuth: true, title: '学习计划', navGroup: 'study' },
  },
  {
    path: '/web/learn',
    name: 'learn',
    component: LearnPage,
    meta: { requiresAuth: true, title: '学习单词', navGroup: 'study' },
  },
  {
    path: '/web/review',
    name: 'review',
    component: ReviewPage,
    meta: { requiresAuth: true, title: '复习', navGroup: 'study' },
  },
  {
    path: '/web/grammar',
    name: 'grammar',
    component: GrammarHubPage,
    meta: { requiresAuth: true, title: '语法', navGroup: 'main' },
  },
  {
    path: '/web/grammar/examples',
    name: 'grammar-examples',
    component: GrammarExamplesPage,
    meta: { requiresAuth: true, title: '例句学语法', navGroup: 'grammar' },
  },
  {
    path: '/web/grammar/analyze',
    name: 'grammar-analyze',
    component: GrammarAnalyzePage,
    meta: { requiresAuth: true, title: '自动拆句', navGroup: 'grammar' },
  },
  {
    path: '/web/grammar/guide',
    name: 'grammar-guide',
    component: GrammarGuidePage,
    meta: { requiresAuth: true, title: '语法总览', navGroup: 'grammar' },
  },
  {
    path: '/web/grammar/guide/:volumeId?',
    name: 'grammar-guide-volume',
    component: GrammarGuideVolumePage,
    meta: { requiresAuth: true, title: '语法分册', navGroup: 'grammar' },
  },
  {
    path: '/web/ai',
    name: 'ai',
    component: AiCenterPage,
    meta: { requiresAuth: true, title: 'AI 中心', navGroup: 'main' },
  },
  {
    path: '/web/profile',
    name: 'profile',
    component: ProfilePage,
    meta: { requiresAuth: true, title: '我的', navGroup: 'main' },
  },
  {
    path: '/web/settings',
    name: 'settings',
    component: SettingsPage,
    meta: { requiresAuth: true, title: '学习设置', navGroup: 'profile' },
  },
  {
    path: '/web/stats',
    name: 'stats',
    component: StatsPage,
    meta: { requiresAuth: true, title: '统计', navGroup: 'profile' },
  },
  {
    path: '/web/exam',
    name: 'exam',
    component: ExamPage,
    meta: { requiresAuth: true, title: '测试', navGroup: 'study' },
  },
  {
    path: '/web/word/:id',
    name: 'word-detail',
    component: WordDetailPage,
    meta: { requiresAuth: true, title: '单词详情', navGroup: 'study' },
  },
  {
    path: '/web/wrong-words',
    name: 'wrong-words',
    component: WrongWordsPage,
    meta: { requiresAuth: true, title: '错词本', navGroup: 'profile' },
  },
  {
    path: '/web/favorites',
    name: 'favorites',
    component: FavoritesPage,
    meta: { requiresAuth: true, title: '收藏夹', navGroup: 'profile' },
  },
  {
    path: '/web/feedback',
    name: 'feedback',
    component: FeedbackPage,
    meta: { requiresAuth: true, title: '反馈', navGroup: 'profile' },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const sessionStore = useSessionStore();
  if (!sessionStore.hydrated) {
    sessionStore.hydrate();
  }
  if (to.meta.requiresAuth && !sessionStore.token) {
    return {
      name: 'login',
      query: {
        redirect: to.fullPath,
      },
    };
  }
  if (to.name === 'login' && sessionStore.token) {
    return { name: 'home' };
  }
  return true;
});

router.afterEach((to) => {
  document.title = `${to.meta.title || 'GAClearn'} - GAClearn Web`;
});

export default router;
