<template>
  <a-page-header title="系统信息" :sub-title="`版本: ${sysInfo.version}`">
    <a-card :bordered="false" class="sys-info-card" title="系统资源">
       <SystemResources :resources="sysInfo.resources" />
    </a-card>
    <a-card :bordered="false" class="sys-info-card" title="文章统计">
      <template #extra>
        <a-button 
          type="primary" 
          size="small" 
          :loading="refreshing"
          @click="handleRefreshArticleStats"
        >
          <template #icon><reload-outlined /></template>
          刷新
        </a-button>
      </template>
      <a-descriptions bordered :column="{ xs: 1, sm: 1, md: 1, lg: 2 }">
         <a-descriptions-item label="公众号总数">
          <template #label> <desktop-outlined /> 公众号总数 </template>
          {{ sysInfo.article?.mp_all_count || 0 }}
        </a-descriptions-item>
        <a-descriptions-item label="文章总数">
          <template #label> <desktop-outlined /> 文章总数 </template>
          {{ sysInfo.article?.all_count || 0 }}
        </a-descriptions-item>
        <a-descriptions-item label="无正文数量">
          <template #label> <desktop-outlined /> 无正文数量 </template>
          {{ sysInfo.article?.no_content_count || 0 }}
        </a-descriptions-item>
        <a-descriptions-item label="有正文数量">
          <template #label> <desktop-outlined /> 有正文数量 </template>
          {{ sysInfo.article?.has_content_count || 0 }}
        </a-descriptions-item>
        <a-descriptions-item label="已删除">
          <template #label> <desktop-outlined /> 已删除 </template>
          {{ sysInfo.article?.wrong_count || 0 }}
        </a-descriptions-item>
      </a-descriptions>
    </a-card>
    <a-card :bordered="false" class="sys-info-card" title="系统信息">
      <a-descriptions bordered :column="{ xs: 1, sm: 1, md: 1, lg: 2 }">
        <a-descriptions-item label="操作系统">
          <template #label> <desktop-outlined /> 操作系统 </template>
          {{ sysInfo.os.name }}
        </a-descriptions-item>
        <a-descriptions-item label="Docker版本">
          <template #label> <desktop-outlined /> Docker版本 </template>
          {{ sysInfo.os.docker_version }}
        </a-descriptions-item>
        <a-descriptions-item label="系统版本">
          <template #label> <code-outlined /> 系统版本 </template>
          {{ sysInfo.os.version }} ({{ sysInfo.os.release }})
        </a-descriptions-item>
        <a-descriptions-item label="Python版本">
          <template #label> <code-outlined /> Python版本 </template>
          {{ sysInfo.python_version }}
        </a-descriptions-item>
        <a-descriptions-item label="运行时间">
          <template #label> <clock-circle-outlined /> 运行时间 </template>
          {{ formatUptime(sysInfo.uptime) }}
        </a-descriptions-item>
        <a-descriptions-item label="系统架构">
          <template #label> <deployment-unit-outlined /> 系统架构 </template>
          {{ sysInfo.system.node }} / {{ sysInfo.system.machine }} ({{
            sysInfo.system.processor
          }})
        </a-descriptions-item>
        <a-descriptions-item label="TOKEN">
          <template #label> <api-outlined /> TOKEN </template>
          {{ sysInfo.wx.token }}
        </a-descriptions-item>
        <a-descriptions-item label="过期时间">
          <template #label> <api-outlined /> 过期时间 </template>
          {{ !sysInfo.wx.login? '未登录': sysInfo.wx.expiry_time }}
        </a-descriptions-item>
        <a-descriptions-item label="API版本">
          <template #label> <api-outlined /> API版本 </template>
          {{ sysInfo.api_version }}
        </a-descriptions-item>
        <a-descriptions-item label="队列状态">
          <template #label> <api-outlined /> 队列状态 </template>
          {{ sysInfo.queue.is_running || false }}
        </a-descriptions-item>
        <a-descriptions-item label="队列数量">
          <template #label> <api-outlined /> 挂起队列数量 </template>
          {{ sysInfo.queue.pending_tasks || 0 }}
        </a-descriptions-item>
        <a-descriptions-item label="核心版本">
          <template #label> <appstore-outlined /> 核心版本 </template>
          {{ sysInfo.core_version }}
        </a-descriptions-item>
        <a-descriptions-item label="最新版本">
          <template #label> <cloud-download-outlined /> 最新版本 </template>
          {{ sysInfo.latest_version }}
          <!-- 添加点击事件 -->
          <a-button
            v-if="sysInfo.need_update"
            type="text"
            size="small"
            style="margin-left: 8px"
            @click="openUpdateLink"
            >立即更新</a-button
          >
        </a-descriptions-item>
      </a-descriptions>
    </a-card>
  </a-page-header>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { getSysInfo, refreshArticleStats } from "@/api/sysInfo";
import type { SysInfo } from "@/api/sysInfo";
import SystemResources from "@/components/SystemResources.vue";
import { message } from 'ant-design-vue';

const refreshing = ref(false);

const sysInfo = ref<SysInfo>({
  os: {
    name: "",
    version: "",
    release: "",
  },
  python_version: "",
  uptime: 0,
  system: {
    node: "",
    machine: "",
    processor: "",
  },
  api_version: "/api/v1/wx",
  core_version: "",
  latest_version: "",
  need_update: true,
  wx: {
    token: "",
    expiry_time: "",
  },
  queue: {
    is_running: false,
    pending_tasks: 0,
  },
});

const formatUptime = (seconds: number): string => {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${days}天 ${hours}小时 ${minutes}分钟`;
};

// 定义打开链接的函数
const openUpdateLink = () => {
  window.open("https://github.com/rachelos/we-mp-rss", "_blank");
};

// 手动刷新文章统计
const handleRefreshArticleStats = async () => {
  try {
    refreshing.value = true;
    await refreshArticleStats();
    message.success('文章统计刷新任务已启动,请稍后刷新页面查看最新数据');
    // 3秒后自动刷新数据
    setTimeout(async () => {
      sysInfo.value = await getSysInfo();
      message.success('文章统计已更新');
    }, 3000);
  } catch (error: any) {
    message.error(error.message || '刷新失败');
  } finally {
    refreshing.value = false;
  }
};

onMounted(async () => {
  sysInfo.value = await getSysInfo()
});
</script>

<style scoped>
.sys-info-container {
  margin-top: 16px;
}

.sys-info-card {
  margin-bottom: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
  transition: all 0.3s ease;
  background: var(--color-bg-2);
  height: 100%;
}

.sys-info-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.16);
  transform: translateY(-2px);
}

.sys-info-card :deep(.ant-card-head) {
  border-bottom: none;
}

.sys-info-card :deep(.ant-descriptions-item-label) {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.sys-info-card :deep(.ant-descriptions-item-content) {
  color: var(--color-text-1);
}

.sys-info-card :deep(.anticon) {
  font-size: 16px;
}

.sys-info-card :deep(.ant-descriptions-row) {
  padding: 12px 0;
}

.sys-info-card :deep(.ant-descriptions-item) {
  padding-bottom: 0;
}
</style>