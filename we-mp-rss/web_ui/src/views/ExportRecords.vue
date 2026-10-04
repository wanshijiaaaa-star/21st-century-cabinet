<template>
      <ExportRecords :mp_id="mp_id" />
</template>

<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import { ref } from 'vue'
import { computed } from 'vue'
import ExportRecords from '@/components/ExportRecords.vue'
const mp_id = ref('')
</script>

<style scoped>
</style>