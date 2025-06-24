<template>
  <div v-if="visible" class="bg-green-100 border-l-4 border-green-500 text-green-700 p-4 mb-4 rounded-xl">
    ✅ Registration successful! Please check your inbox to verify your email.
  </div>
</template>

<script setup lang="ts">
// Component props - controls visibility of the notification
defineProps<{
  visible: boolean
}>()
</script>
