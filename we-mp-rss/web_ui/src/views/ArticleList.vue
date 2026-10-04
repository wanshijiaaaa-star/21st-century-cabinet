<template>
  <ArticleList v-if="!isMobile" />
  <ArticleListMobile v-else />
</template>
<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import { ref } from 'vue'
import { computed } from 'vue'
import ArticleList from '@/views/article/ArticleListDesktop.vue'
import ArticleListMobile from '@/views/article/ArticleListMobile.vue'
const isMobile = ref(window.innerWidth < 768)
const handleResize = () => {
  isMobile.value = window.innerWidth < 768
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
})
</script>
<style>
#article-modal img{
   max-width:100% !important;
   border-width:0 !important;
}
</style>