<template>
  <a :href="url" target="_blank" rel="noopener noreferrer" class="commit-info">
    Built from commit <code>{{ sha }}</code>
  </a>
</template>

<script setup lang="ts">
declare const __GIT_SHA__: string
declare const __GIT_SHA_SHORT__: string

const sha = __GIT_SHA_SHORT__
const url = `https://github.com/codebude/librislog/commit/${__GIT_SHA__}`
</script>

<style scoped>
.commit-info {
  font-size: 0.8rem;
  color: var(--vp-c-text-2);
}
.commit-info code {
  font-size: 0.8rem;
}
</style>
