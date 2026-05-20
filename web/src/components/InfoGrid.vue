<script setup>
defineProps({
  items: {
    type: Array,
    default: () => [],
  },
  cardClass: {
    type: [String, Array, Object],
    default: '',
  },
});
</script>

<template>
  <div class="info-grid">
    <article v-for="item in items" :key="item.label" class="info-card" :class="cardClass">
      <div class="info-label">{{ item.label }}</div>
      <div class="info-value">{{ item.value }}</div>
      <div v-if="item.description" class="info-description">{{ item.description }}</div>
    </article>
  </div>
</template>
