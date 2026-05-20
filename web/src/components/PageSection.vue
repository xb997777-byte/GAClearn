<script setup>
defineProps({
  title: {
    type: String,
    default: '',
  },
  subtitle: {
    type: String,
    default: '',
  },
  tone: {
    type: String,
    default: 'panel',
  },
});
</script>

<template>
  <section class="page-section" :class="`tone-${tone}`">
    <header v-if="title || subtitle" class="page-section-head">
      <div v-if="title" class="page-section-title">{{ title }}</div>
      <div v-if="subtitle" class="page-section-subtitle">{{ subtitle }}</div>
    </header>
    <slot />
  </section>
</template>
