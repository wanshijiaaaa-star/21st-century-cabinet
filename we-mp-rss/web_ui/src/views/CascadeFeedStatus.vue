<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getFeedStatus } from '@/api/cascade'
import type { FeedStatus } from '@/api/cascade'
import { Message } from '@arco-design/web-vue'
import { IconRefresh, IconUser } from '@arco-design/web-vue/es/icon'

const feedStatusColumns = [
  { title: '公众号', slotName: 'mp_info', dataIndex: 'mp_name', ellipsis: true, sortable: { sortDirections: ['ascend', 'descend'] } },
  { title: '文章数', dataIndex: 'article_count', width: 100, sortable: { sortDirections: ['ascend', 'descend'] } },
  { title: '更新状态', slotName: 'update_status', dataIndex: 'update_status', width: 110, sortable: { sortDirections: ['ascend', 'descend'] } },
  { title: '最近文章', slotName: 'latest_article_time', dataIndex: 'latest_article_time', width: 160, sortable: { sortDirections: ['ascend', 'descend'] } },
  { title: '最后任务', slotName: 'last_task', width: 120 },
  { title: '执行节点', slotName: 'last_task_node', width: 120 },
  { title: '更新时间', slotName: 'updated_at', dataIndex: 'updated_at', width: 160, sortable: { sortDirections: ['ascend', 'descend'] } }
]

const feedStatusList = ref<FeedStatus[]>([])
const totalFeeds = ref(0)
const feedStatusLoading = ref(false)
const showTip = ref(true)

const feedStatusPagination = reactive({
  limit: 12,
  offset: 0
})

const sort = reactive({
  field: 'updated_at',
  order: 'descend' as 'ascend' | 'descend' | ''
})

const fetchFeedStatus = async () => {
  try {
    feedStatusLoading.value = true
    const res = await getFeedStatus({
      limit: feedStatusPagination.limit,
      offset: feedStatusPagination.offset,
      sort_by: sort.field,
      sort_order: sort.order === 'ascend' ? 'asc' : sort.order === 'descend' ? 'desc' : undefined
    })
    feedStatusList.value = res?.list || []
    totalFeeds.value = res?.total || 0
  } catch (err) {
    console.error('获取公众号状态失败:', err)
    Message.error('获取公众号状态失败')
  } finally {
    feedStatusLoading.value = false
  }
}

const handleFeedStatusPageChange = (page: number) => {
  feedStatusPagination.offset = (page - 1) * feedStatusPagination.limit
  fetchFeedStatus()
}

const handleSorterChange = (dataIndex: string, direction: 'ascend' | 'descend' | '') => {
  sort.field = dataIndex
  sort.order = direction
  feedStatusPagination.offset = 0
  fetchFeedStatus()
}

const formatDate = (dateStr: string | undefined) => {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN')
  } catch {
    return '-'
  }
}

const getUpdateStatusColor = (status: string) => {
  const map: Record<string, string> = {
    fresh: 'green',
    recent: 'blue',
    stale: 'orange',
    outdated: 'red',
    unknown: 'gray'
  }
  return map[status] || 'gray'
}

const getUpdateStatusText = (status: string) => {
  const map: Record<string, string> = {
    fresh: '最新',
    recent: '较新',
    stale: '陈旧',
    outdated: '过期',
    unknown: '未知'
  }
  return map[status] || status
}

const getAllocationStatusColor = (status: string) => {
  const map: Record<string, string> = {
    pending: 'orange',
    executing: 'blue',
    completed: 'green',
    failed: 'red'
  }
  return map[status] || 'gray'
}

const getAllocationStatusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '待认领',
    claimed: '已认领',
    executing: '执行中',
    completed: '已完成',
    failed: '失败',
    timeout: '超时'
  }
  return map[status] || status
}

onMounted(() => {
  setTimeout(() => {
    showTip.value = false
  }, 3000)
  fetchFeedStatus()
})
</script>

<template>
  <div class="cascade-feed-status">
    <a-card title="公众号状态" :bordered="false">
      <template #extra>
        <a-button @click="fetchFeedStatus" :loading="feedStatusLoading">
          <template #icon>
            <icon-refresh />
          </template>
          刷新
        </a-button>
      </template>

      <div v-if="showTip" class="tip-message">
        显示系统中所有公众号的更新状态和任务执行情况
      </div>

      <a-table
        :columns="feedStatusColumns"
        :data="feedStatusList"
        :loading="feedStatusLoading"
        row-key="id"
        :pagination="{
          current: Math.floor(feedStatusPagination.offset / feedStatusPagination.limit) + 1,
          pageSize: feedStatusPagination.limit,
          total: totalFeeds,
          showTotal: true,
          onChange: handleFeedStatusPageChange
        }"
        :sorter="{ field: sort.field, order: sort.order }"
        @sorter-change="handleSorterChange"
      >
        <template #mp_info="{ record }">
          <div style="display: flex; align-items: center; gap: 10px;">
            <img
              v-if="record.mp_cover"
              :src="record.mp_cover"
              :alt="record.mp_name"
              style="width: 32px; height: 32px; border-radius: 4px; object-fit: cover;"
            />
            <span v-else style="width: 32px; height: 32px; border-radius: 4px; background: #f2f3f5; display: flex; align-items: center; justify-content: center;">
              <icon-user style="color: #c9cdd4;" />
            </span>
            <span>{{ record.mp_name }}</span>
          </div>
        </template>

        <template #update_status="{ record }">
          <a-tag :color="getUpdateStatusColor(record.update_status)">
            {{ getUpdateStatusText(record.update_status) }}
          </a-tag>
        </template>

        <template #latest_article_time="{ record }">
          {{ formatDate(record.latest_article_time) }}
        </template>

        <template #last_task="{ record }">
          <template v-if="record.last_task">
            <a-tag :color="getAllocationStatusColor(record.last_task.status)" size="small">
              {{ getAllocationStatusText(record.last_task.status) }}
            </a-tag>
          </template>
          <span v-else style="color: #999;">-</span>
        </template>

        <template #last_task_node="{ record }">
          <span v-if="record.last_task?.node_name" style="color: #165dff;">
            {{ record.last_task.node_name }}
          </span>
          <span v-else-if="record.last_task?.node_id" style="color: #999;">
            {{ record.last_task.node_id.substring(0, 8) }}...
          </span>
          <span v-else style="color: #999;">-</span>
        </template>

        <template #updated_at="{ record }">
          {{ formatDate(record.updated_at) }}
        </template>
      </a-table>

      <a-empty v-if="!feedStatusLoading && feedStatusList.length === 0" description="暂无公众号数据" />
    </a-card>
  </div>
</template>

<style scoped>
.cascade-feed-status {
  padding: 20px;
}
.tip-message {
  padding: 8px 12px;
  margin-bottom: 16px;
  background: #e8f3ff;
  border-radius: 4px;
  color: #165dff;
  font-size: 14px;
  animation: fadeOut 0.3s ease-in-out 2.7s forwards;
}
@keyframes fadeOut {
  from { opacity: 1; }
  to { opacity: 0; }
}
</style>
