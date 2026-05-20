<script setup>
defineProps({
  items: {
    type: Array,
    default: () => [],
  },
});
</script>

<template>
  <div class="action-card-list">
    <article v-for="item in items" :key="item.title" class="action-card">
      <div class="action-card-head">
        <div>
          <div class="action-card-title">{{ item.title }}</div>
          <div v-if="item.subtitle" class="action-card-subtitle">{{ item.subtitle }}</div>
        </div>
        <div v-if="item.badge" class="soft-pill">{{ item.badge }}</div>
      </div>
      <div v-if="item.description" class="action-card-description">{{ item.description }}</div>
      <div v-if="item.tags && item.tags.length" class="chip-row">
        <span v-for="tag in item.tags" :key="tag" class="chip-light">{{ tag }}</span>
      </div>
      <div v-if="item.actions && item.actions.length" class="button-row">
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
</template>
