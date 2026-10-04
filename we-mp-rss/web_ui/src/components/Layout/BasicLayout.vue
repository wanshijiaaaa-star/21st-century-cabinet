<template>
  <a-watermark :content="appTitle" 
  :alpha="0.1"
  :rotate="-22" 
  :anti-tamper="true" 
   >
    <a-layout id="main">
      <Navbar />
      <a-layout >
        <a-layout-content >
          <router-view />
        </a-layout-content>
      </a-layout>
    </a-layout>
  </a-watermark>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, provide } from 'vue'
import Navbar from './Navbar.vue'
const appTitle = computed(() => {
  const ip = window.location.hostname;
  return `${import.meta.env.VITE_APP_COPYRIGHT || 'Power By Rachel Design'}@${ip}`;
})
</script>
