<template>
  <a-layout-header>
    <a-menu
      mode="horizontal"
      :selected-keys="selectedKeys"
      @menu-item-click="handleMenuClick"
    >
      <a-menu-item key="/">
        <template #icon>
          <icon-home />
        </template>
        订阅管理
      </a-menu-item>
      <a-menu-item key="/wechat-status">
        <template #icon>
          <icon-wechat />
        </template>
        授权管理
      </a-menu-item>
      <a-menu-item key="/export/records">
        <template #icon>
          <icon-export />
        </template>
        导出记录
      </a-menu-item>
      <a-menu-item key="/tags">
        <template #icon>
          <icon-tag />
        </template>
        标签管理
      </a-menu-item>
      <a-menu-item key="/message-tasks">
        <template #icon>
          <icon-notification />
        </template>
        消息任务
      </a-menu-item>
      <a-menu-item key="/filter-rules">
        <template #icon>
          <icon-filter />
        </template>
        过滤规则
      </a-menu-item>
      <a-menu-item key="/task-queue">
        <template #icon>
          <icon-list />
        </template>
        任务队列
      </a-menu-item>
       <a-menu-item key="/cascade/feed-status">
        <template #icon>
          <icon-storage />
        </template>
        公众号状态
      </a-menu-item>
      <a-menu-item key="/cascade">
        <template #icon>
          <icon-share-external />
        </template>
        级联管理
      </a-menu-item>
      <a-menu-item key="/access-keys">
        <template #icon>
          <icon-lock />
        </template>
        Access Key
      </a-menu-item>
      <a-menu-item key="/weread">
        <template #icon>
          <icon-book />
        </template>
        微信读书
      </a-menu-item>
      <a-menu-item key="/users">
        <template #icon>
          <icon-user />
        </template>
        用户管理
      </a-menu-item>
      <a-menu-item key="/env-exception">
        <template #icon>
          <icon-exclamation-circle />
        </template>
        异常统计
      </a-menu-item>
       <a-menu-item key="/configs">
        <template #icon>
          <icon-settings />
        </template>
        配置信息
      </a-menu-item>
      <a-menu-item key="/sys-info">
        <template #icon>
          <icon-info-circle />
        </template>
        系统信息
      </a-menu-item>
    </a-menu>
  </a-layout-header>
</template>

<script setup lang="ts">
import { ref, watchEffect } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import TextIcon from '@/components/TextIcon.vue'
import { translatePage, setCurrentLanguage } from '@/utils/translate';

const router = useRouter()
const route = useRoute()
const selectedKeys = ref<string[]>(['/'])

watchEffect(() => {
  selectedKeys.value = [route.path]
  // translatePage()
})

const handleMenuClick = (key: string) => {
  // 避免重复点击当前路由
  if (route.path === key) return
  router.push(key).catch((err) => {
    // 忽略导航到当前路由的错误
    if (!err.message?.includes('Avoided redundant navigation')) {
      console.error('路由导航失败:', err)
    }
  })
}
</script>