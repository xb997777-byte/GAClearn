<script setup>
import { computed } from 'vue';

const props = defineProps({
  runtime: {
    type: Object,
    default: () => null,
  },
  health: {
    type: Object,
    default: () => null,
  },
  steps: {
    type: Array,
    default: () => [],
  },
  artifacts: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  showActions: {
    type: Boolean,
    default: true,
  },
});

const emit = defineEmits(['retry', 'resume', 'cancel', 'approve', 'reject', 'refresh']);

const summary = computed(() => props.runtime?.runtime_summary || props.runtime || {});
const latestApproval = computed(() => props.runtime?.latest_approval || null);
const canRetry = computed(() => !!props.runtime?.retryable);
const canResume = computed(() => !!summary.value?.resumable && props.runtime?.status !== 'running');
const canCancel = computed(() => ['queued', 'running', 'waiting_approval'].includes(props.runtime?.status));
const approvalPending = computed(() => props.runtime?.approval_state === 'pending');
const health = computed(() => props.health || null);
</script>

<template>
  <div v-if="runtime" class="runtime-card">
    <div class="runtime-head">
      <div>
        <div class="runtime-title">运行态</div>
        <div class="runtime-summary">{{ summary.status_text || runtime.status_text || '进行中' }}</div>
      </div>
      <div class="chip-row compact">
        <span class="chip-light">{{ runtime.feature_type || 'ai' }}</span>
        <span class="chip-light">{{ runtime.current_agent || summary.active_agent || 'coordinator' }}</span>
        <span v-if="summary.stale" class="chip-light warning">待恢复</span>
      </div>
    </div>

    <div class="info-grid compact-grid">
      <article class="info-card">
        <div class="info-label">运行状态</div>
        <div class="info-value">{{ summary.status_text || runtime.status }}</div>
        <div class="info-description">{{ summary.summary || '等待更多运行信息' }}</div>
      </article>
      <article class="info-card">
        <div class="info-label">当前智能体</div>
        <div class="info-value">{{ runtime.current_agent || summary.active_agent || '--' }}</div>
        <div class="info-description">当前步骤执行角色</div>
      </article>
      <article class="info-card">
        <div class="info-label">步骤数</div>
        <div class="info-value">{{ summary.step_count || steps.length || 0 }}</div>
        <div class="info-description">真实落账的 step 数</div>
      </article>
      <article class="info-card">
        <div class="info-label">审批状态</div>
        <div class="info-value">{{ approvalPending ? '等待审批' : runtime.approval_state || 'not_required' }}</div>
        <div class="info-description">{{ latestApproval?.title || '当前没有待审批动作' }}</div>
      </article>
    </div>

    <div v-if="showActions" class="button-row wrap">
      <button class="ghost-button small" type="button" :disabled="loading" @click="emit('refresh')">刷新状态</button>
      <button v-if="canRetry" class="ghost-button small" type="button" :disabled="loading" @click="emit('retry')">重试</button>
      <button v-if="canResume" class="ghost-button small" type="button" :disabled="loading" @click="emit('resume')">恢复</button>
      <button v-if="canCancel" class="ghost-button small danger" type="button" :disabled="loading" @click="emit('cancel')">取消</button>
      <button v-if="approvalPending" class="primary-button small" type="button" :disabled="loading" @click="emit('approve')">批准执行</button>
      <button v-if="approvalPending" class="ghost-button small" type="button" :disabled="loading" @click="emit('reject')">拒绝</button>
    </div>

    <details v-if="health" class="details-box">
      <summary>运行时健康</summary>
      <div class="info-grid compact-grid">
        <article class="info-card">
          <div class="info-label">Worker</div>
          <div class="info-value">{{ health.worker_healthy ? '健康' : '异常' }}</div>
          <div class="info-description">{{ (health.workers || []).join('，') || '当前未探测到在线 worker' }}</div>
        </article>
        <article class="info-card">
          <div class="info-label">队列</div>
          <div class="info-value">{{ (health.observed_queues || []).length || 0 }}</div>
          <div class="info-description">{{ (health.observed_queues || []).join('，') || '尚未读取到队列信息' }}</div>
        </article>
        <article class="info-card">
          <div class="info-label">自动恢复</div>
          <div class="info-value">{{ health.auto_recover_enabled ? '已开启' : '未开启' }}</div>
          <div class="info-description">每 {{ health.auto_recover_every_seconds || 0 }} 秒最多恢复 {{ health.auto_recover_limit || 0 }} 个失活任务</div>
        </article>
        <article class="info-card">
          <div class="info-label">失活任务</div>
          <div class="info-value">{{ health.stale_run_count || 0 }}</div>
          <div class="info-description">{{ health.degraded_reason || '标准 Agent 运行时正在持续检查失活任务。' }}</div>
        </article>
      </div>
      <div v-if="health.stale_runs_preview?.length" class="list-stack details-stack">
        <div v-for="item in health.stale_runs_preview" :key="item.run_id" class="list-line">
          <strong>{{ item.feature_type }}</strong>
          <span class="line-meta">{{ item.run_id }} · {{ item.status }} · {{ item.queue_name }}</span>
        </div>
      </div>
    </details>

    <details class="details-box">
      <summary>步骤时间线</summary>
      <div v-if="steps.length" class="list-stack details-stack">
        <div v-for="step in steps" :key="step.id || `${step.step_index}-${step.step_key}`" class="list-line">
          <strong>#{{ step.step_index }} {{ step.title || step.step_key }}</strong>
          <span class="line-meta">{{ step.agent_name || step.step_kind }} · {{ step.status }} · {{ step.latency_ms || 0 }}ms</span>
          <span v-if="step.summary" class="soft-caption">{{ step.summary }}</span>
        </div>
      </div>
      <div v-else class="soft-caption">当前还没有加载到步骤明细。</div>
    </details>

    <details class="details-box">
      <summary>产物与依据</summary>
      <div v-if="artifacts.length" class="list-stack details-stack">
        <div v-for="artifact in artifacts" :key="artifact.id || `${artifact.artifact_type}-${artifact.artifact_key}`" class="list-line">
          <strong>{{ artifact.title || artifact.artifact_key || artifact.artifact_type }}</strong>
          <span class="line-meta">{{ artifact.artifact_type }}</span>
          <span v-if="artifact.summary" class="soft-caption">{{ artifact.summary }}</span>
        </div>
      </div>
      <div v-else class="soft-caption">当前还没有加载到运行产物。</div>
    </details>
  </div>
</template>
