<template>
  <div class="task-queue-view">
    <!-- 顶部状态栏 -->
    <div class="header-bar">
      <div class="header-left">
        <span class="title">任务队列</span>
        <a-tag :color="wsConnected ? 'green' : 'orange'" size="small">
          {{ wsConnected ? '实时' : '轮询' }}
        </a-tag>
      </div>
      <div class="header-right">
        <a-button type="primary" size="small" @click="refreshAll" :loading="loading">
          <template #icon><icon-refresh /></template>
          刷新
        </a-button>
      </div>
    </div>

    <a-spin :loading="loading" style="width: 100%">
      <!-- 两列布局：主队列 + 内容队列 -->
      <div class="queues-container">
        <!-- 主队列（文章采集） -->
        <div class="queue-section">
          <div class="queue-header">
            <span class="queue-title">文章采集队列</span>
            <a-tag :color="mainQueueStatus.is_running ? 'green' : 'red'" size="small">
              {{ mainQueueStatus.is_running ? '运行中' : '已停止' }}
            </a-tag>
            <div class="queue-actions">
              <a-popconfirm content="确定要清空主队列吗？" @ok="handleClearQueue('main')">
                <a-button size="mini" status="warning" :loading="clearingQueueMain">
                  清空队列
                </a-button>
              </a-popconfirm>
              <a-popconfirm content="确定要清空历史记录吗？" @ok="handleClearHistory('main')">
                <a-button size="mini" status="danger" :loading="clearingHistoryMain">
                  清空历史
                </a-button>
              </a-popconfirm>
            </div>
          </div>
          
          <div class="queue-content">
            <!-- 状态概览 -->
            <div class="status-row">
              <div class="status-item">
                <span class="label">待执行</span>
                <span class="value pending">{{ mainQueueStatus.pending_count ?? 0 }}</span>
              </div>
              <div class="status-item">
                <span class="label">历史数</span>
                <span class="value">{{ mainQueueStatus.history_count ?? 0 }}</span>
              </div>
            </div>
            
            <!-- 当前任务 -->
            <div class="current-task-section">
              <div class="section-title">当前任务</div>
              <div v-if="mainQueueStatus.current_task" class="current-task">
                <div class="task-name">
                  <icon-play-arrow-fill style="color: #165dff" />
                  {{ mainQueueStatus.current_task.task_name }}
                </div>
                <div class="task-info">
                  <span>{{ mainQueueStatus.current_task.start_time }}</span>
                  <a-tag color="blue" size="small">{{ mainQueueStatus.current_task.status }}</a-tag>
                </div>
              </div>
              <div v-else class="no-task">
                <icon-pause-circle style="font-size: 18px; color: #c9cdd4" />
                <span>暂无执行中任务</span>
              </div>
            </div>
            
            <!-- 待执行任务 -->
            <div class="pending-section">
              <div class="section-title">待执行任务</div>
              <div class="task-list" v-if="mainQueueStatus.pending_tasks && mainQueueStatus.pending_tasks.length > 0">
                <a-tag v-for="(task, index) in mainQueueStatus.pending_tasks.slice(0, 8)" :key="index" color="arcoblue" size="small">
                  {{ task.task_name }}
                </a-tag>
                <span v-if="mainQueueStatus.pending_tasks.length > 8" class="more">
                  +{{ mainQueueStatus.pending_tasks.length - 8 }}
                </span>
              </div>
              <div v-else class="no-task-small">暂无</div>
            </div>
            
            <!-- 执行历史 -->
            <div class="history-section">
              <div class="section-title">执行历史</div>
              <div class="history-list" v-if="mainHistory.length > 0">
                <div v-for="(record, index) in mainHistory.slice(0, 5)" :key="index" class="history-item">
                  <div class="history-row1">
                    <span class="task-name">{{ record.task_name }}</span>
                    <a-tag :color="getStatusColor(record.status)" size="small">{{ getStatusText(record.status) }}</a-tag>
                  </div>
                  <div class="history-row2">
                    <span class="history-time">{{ record.start_time }}</span>
                    <span class="history-duration" v-if="record.duration">{{ record.duration.toFixed(1) }}s</span>
                  </div>
                </div>
              </div>
              <div v-else class="no-task-small">暂无历史</div>
            </div>
          </div>
        </div>

        <!-- 内容队列（补抓内容） -->
        <div class="queue-section">
          <div class="queue-header">
            <span class="queue-title">内容补抓队列</span>
            <a-tag :color="contentQueueStatus.is_running ? 'green' : 'red'" size="small">
              {{ contentQueueStatus.is_running ? '运行中' : '已停止' }}
            </a-tag>
            <div class="queue-actions">
              <a-popconfirm content="确定要清空内容队列吗？" @ok="handleClearQueue('content')">
                <a-button size="mini" status="warning" :loading="clearingQueueContent">
                  清空队列
                </a-button>
              </a-popconfirm>
              <a-popconfirm content="确定要清空历史记录吗？" @ok="handleClearHistory('content')">
                <a-button size="mini" status="danger" :loading="clearingHistoryContent">
                  清空历史
                </a-button>
              </a-popconfirm>
            </div>
          </div>
          
          <div class="queue-content">
            <!-- 状态概览 -->
            <div class="status-row">
              <div class="status-item">
                <span class="label">待执行</span>
                <span class="value pending">{{ contentQueueStatus.pending_count ?? 0 }}</span>
              </div>
              <div class="status-item">
                <span class="label">历史数</span>
                <span class="value">{{ contentQueueStatus.history_count ?? 0 }}</span>
              </div>
            </div>
            
            <!-- 当前任务 -->
            <div class="current-task-section">
              <div class="section-title">当前任务</div>
              <div v-if="contentQueueStatus.current_task" class="current-task">
                <div class="task-name">
                  <icon-play-arrow-fill style="color: #165dff" />
                  {{ contentQueueStatus.current_task.task_name }}
                </div>
                <div class="task-info">
                  <span>{{ contentQueueStatus.current_task.start_time }}</span>
                  <a-tag color="blue" size="small">{{ contentQueueStatus.current_task.status }}</a-tag>
                </div>
              </div>
              <div v-else class="no-task">
                <icon-pause-circle style="font-size: 18px; color: #c9cdd4" />
                <span>暂无执行中任务</span>
              </div>
            </div>
            
            <!-- 待执行任务 -->
            <div class="pending-section">
              <div class="section-title">待执行任务</div>
              <div class="task-list" v-if="contentQueueStatus.pending_tasks && contentQueueStatus.pending_tasks.length > 0">
                <a-tag v-for="(task, index) in contentQueueStatus.pending_tasks.slice(0, 8)" :key="index" color="orangered" size="small">
                  {{ task.task_name }}
                </a-tag>
                <span v-if="contentQueueStatus.pending_tasks.length > 8" class="more">
                  +{{ contentQueueStatus.pending_tasks.length - 8 }}
                </span>
              </div>
              <div v-else class="no-task-small">暂无</div>
            </div>
            
            <!-- 执行历史 -->
            <div class="history-section">
              <div class="section-title">执行历史</div>
              <div class="history-list" v-if="contentHistory.length > 0">
                <div v-for="(record, index) in contentHistory.slice(0, 5)" :key="index" class="history-item">
                  <div class="history-row1">
                    <span class="task-name">{{ record.task_name }}</span>
                    <a-tag :color="getStatusColor(record.status)" size="small">{{ getStatusText(record.status) }}</a-tag>
                  </div>
                  <div class="history-row2">
                    <span class="history-time">{{ record.start_time }}</span>
                    <span class="history-duration" v-if="record.duration">{{ record.duration.toFixed(1) }}s</span>
                  </div>
                </div>
              </div>
              <div v-else class="no-task-small">暂无历史</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 定时调度器 -->
      <div class="panel scheduler-panel">
        <div class="panel-title">
          定时调度器
          <a-tag :color="schedulerStatus.running ? 'green' : 'red'" size="small">
            {{ schedulerStatus.running ? '运行中' : '已停止' }}
          </a-tag>
        </div>
        <div class="scheduler-content">
          <div class="scheduler-list" v-if="schedulerJobs.length > 0">
            <div v-for="job in schedulerJobs" :key="job.id" class="scheduler-item">
              <span class="job-id">{{ job.id }}</span>
              <span class="job-next">下次执行: {{ job.next_run_time || '-' }}</span>
            </div>
          </div>
          <div v-else class="no-task">
            <span>暂无定时任务</span>
          </div>
        </div>
      </div>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import {
  IconRefresh,
  IconPlayArrowFill,
  IconPauseCircle,
} from '@arco-design/web-vue/es/icon'
import {
  getQueueStatus,
  clearQueue,
  clearHistory,
  getSchedulerStatus,
  getSchedulerJobs,
  getQueueHistory,
  type QueueStatus,
  type SchedulerStatus,
  type SchedulerJob,
  type TaskRecord,
} from '@/api/taskQueue'
import { getToken } from '@/utils/auth'

const loading = ref(false)
const wsConnected = ref(false)

// 清空状态
const clearingQueueMain = ref(false)
const clearingQueueContent = ref(false)
const clearingHistoryMain = ref(false)
const clearingHistoryContent = ref(false)

// 主队列状态
const mainQueueStatus = ref<QueueStatus>({
  tag: '',
  is_running: false,
  pending_count: 0,
  pending_tasks: [],
  current_task: null,
  history_count: 0,
  recent_history: [],
})

// 内容队列状态
const contentQueueStatus = ref<QueueStatus>({
  tag: '',
  is_running: false,
  pending_count: 0,
  pending_tasks: [],
  current_task: null,
  history_count: 0,
  recent_history: [],
})

// 历史记录
const mainHistory = ref<TaskRecord[]>([])
const contentHistory = ref<TaskRecord[]>([])

const schedulerStatus = ref<SchedulerStatus>({
  running: false,
  job_count: 0,
  next_run_times: [],
})

const schedulerJobs = ref<SchedulerJob[]>([])

// WebSocket 连接
let ws: WebSocket | null = null
let reconnectTimer: number | null = null
let refreshTimer: number | null = null

// 获取 WebSocket URL
const getWsUrl = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const apiBase = '/api/v1/wx'
  const token = getToken()
  const tokenParam = token ? `?token=${encodeURIComponent(token)}` : ''
  return `${protocol}//${host}${apiBase}/task-queue/ws${tokenParam}`
}

// 连接 WebSocket
const connectWebSocket = () => {
  if (ws) {
    ws.close()
  }

  try {
    const wsUrl = getWsUrl()
    console.log('[WebSocket] 连接中...', wsUrl)
    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('[WebSocket] 连接成功')
      wsConnected.value = true
      if (reconnectTimer) {
        clearInterval(reconnectTimer)
        reconnectTimer = null
      }
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        if (message.type === 'queue_status' && message.data) {
          console.log('[WebSocket] 收到状态更新')
          // 更新队列状态
          if (message.data.main_queue) {
            mainQueueStatus.value = message.data.main_queue
            mainHistory.value = message.data.main_queue.recent_history || []
          }
          if (message.data.content_queue) {
            contentQueueStatus.value = message.data.content_queue
            contentHistory.value = message.data.content_queue.recent_history || []
          }
        }
      } catch (e) {
        console.error('解析 WebSocket 消息失败:', e)
      }
    }

    ws.onclose = (event) => {
      console.log('[WebSocket] 连接关闭', event.code, event.reason)
      wsConnected.value = false
      if (!reconnectTimer) {
        reconnectTimer = window.setInterval(() => {
          if (!wsConnected.value) {
            connectWebSocket()
          }
        }, 5000)
      }
    }

    ws.onerror = (error) => {
      console.error('[WebSocket] 连接错误', error)
      wsConnected.value = false
    }
  } catch (error) {
    console.error('WebSocket 连接失败:', error)
    wsConnected.value = false
  }
}

// 获取状态颜色
const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed':
      return 'green'
    case 'running':
      return 'blue'
    case 'failed':
      return 'red'
    default:
      return 'gray'
  }
}

// 获取状态文本
const getStatusText = (status: string) => {
  switch (status) {
    case 'completed':
      return '成功'
    case 'running':
      return '执行中'
    case 'failed':
      return '失败'
    default:
      return status
  }
}

// 加载所有数据
const refreshAll = async () => {
  loading.value = true
  try {
    const [queueData, schedulerData, jobsData] = await Promise.all([
      getQueueStatus(),
      getSchedulerStatus(),
      getSchedulerJobs(),
    ])
    
    // 更新队列状态
    if (queueData.main_queue) {
      mainQueueStatus.value = queueData.main_queue
      mainHistory.value = queueData.main_queue.recent_history || []
    }
    if (queueData.content_queue) {
      contentQueueStatus.value = queueData.content_queue
      contentHistory.value = queueData.content_queue.recent_history || []
    }
    
    schedulerStatus.value = schedulerData
    schedulerJobs.value = jobsData.jobs || []
  } catch (error: any) {
    console.error('Refresh error:', error)
    Message.error(error.message || '加载数据失败')
  } finally {
    loading.value = false
  }
}

// 清空队列
const handleClearQueue = async (queueType: 'main' | 'content') => {
  if (queueType === 'main') {
    clearingQueueMain.value = true
  } else {
    clearingQueueContent.value = true
  }
  try {
    await clearQueue(queueType)
    Message.success('队列已清空')
    await refreshAll()
  } catch (error: any) {
    Message.error(error.message || '清空队列失败')
  } finally {
    if (queueType === 'main') {
      clearingQueueMain.value = false
    } else {
      clearingQueueContent.value = false
    }
  }
}

// 清空历史
const handleClearHistory = async (queueType: 'main' | 'content') => {
  if (queueType === 'main') {
    clearingHistoryMain.value = true
  } else {
    clearingHistoryContent.value = true
  }
  try {
    await clearHistory(queueType)
    Message.success('历史记录已清空')
    await refreshAll()
  } catch (error: any) {
    Message.error(error.message || '清空历史失败')
  } finally {
    if (queueType === 'main') {
      clearingHistoryMain.value = false
    } else {
      clearingHistoryContent.value = false
    }
  }
}

onMounted(() => {
  refreshAll()
  connectWebSocket()
  refreshTimer = window.setInterval(() => {
    if (!wsConnected.value) {
      refreshAll()
    }
  }, 10000)
})

onUnmounted(() => {
  if (ws) {
    ws.close()
    ws = null
  }
  if (reconnectTimer) {
    clearInterval(reconnectTimer)
    reconnectTimer = null
  }
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<style scoped>
.task-queue-view {
  padding: 12px;
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 顶部状态栏 */
.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: var(--color-bg-2);
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-left .title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-1);
}

.header-right {
  display: flex;
  gap: 8px;
}

/* 两列队列布局 */
.queues-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.queue-section {
  background: var(--color-bg-2);
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.queue-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--color-fill-1);
  border-bottom: 1px solid var(--color-border);
}

.queue-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-1);
}

.queue-actions {
  margin-left: auto;
  display: flex;
  gap: 6px;
}

.queue-content {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 状态行 */
.status-row {
  display: flex;
  gap: 12px;
}

.status-item {
  flex: 1;
  text-align: center;
  padding: 8px;
  background: var(--color-fill-1);
  border-radius: 4px;
}

.status-item .label {
  display: block;
  font-size: 11px;
  color: var(--color-text-3);
  margin-bottom: 2px;
}

.status-item .value {
  display: block;
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-1);
}

.status-item .value.pending {
  color: #ff7d00;
}

/* 当前任务 */
.current-task-section {
  background: var(--color-fill-1);
  border-radius: 4px;
  padding: 8px 10px;
}

.section-title {
  font-size: 11px;
  color: var(--color-text-3);
  margin-bottom: 6px;
}

.current-task {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.current-task .task-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
}

.current-task .task-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--color-text-3);
}

.no-task {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--color-text-3);
  font-size: 12px;
  padding: 4px 0;
}

.no-task-small {
  color: var(--color-text-3);
  font-size: 12px;
  padding: 4px 0;
}

/* 待执行任务 */
.pending-section {
  background: var(--color-fill-1);
  border-radius: 4px;
  padding: 8px 10px;
}

.task-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.task-list .more {
  font-size: 11px;
  color: var(--color-text-3);
  padding: 2px 6px;
}

/* 历史记录 */
.history-section {
  background: var(--color-fill-1);
  border-radius: 4px;
  padding: 8px 10px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-item {
  font-size: 12px;
  padding: 4px 0;
  border-bottom: 1px solid var(--color-border);
}

.history-item:last-child {
  border-bottom: none;
}

.history-row1 {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2px;
}

.history-row2 {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: var(--color-text-3);
}

.history-item .task-name {
  color: var(--color-text-1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
}

.history-time {
  color: var(--color-text-3);
}

.history-duration {
  color: var(--color-text-3);
}

/* 定时调度器 */
.scheduler-panel {
  background: var(--color-bg-2);
  border-radius: 6px;
  padding: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.panel-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-2);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.scheduler-content {
  background: var(--color-fill-1);
  border-radius: 4px;
  padding: 8px 10px;
}

.scheduler-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.scheduler-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 10px;
  background: var(--color-bg-2);
  border-radius: 4px;
  font-size: 12px;
}

.scheduler-item .job-id {
  color: var(--color-text-1);
  font-weight: 500;
}

.scheduler-item .job-next {
  color: var(--color-text-3);
  font-size: 11px;
}

/* 响应式 */
@media (max-width: 900px) {
  .queues-container {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .task-queue-view {
    padding: 8px;
    height: auto;
    min-height: calc(100vh - 100px);
  }
  
  .header-bar {
    flex-direction: column;
    gap: 8px;
    padding: 8px 12px;
  }
  
  .header-right {
    width: 100%;
    justify-content: flex-end;
  }
  
  .queue-section {
    margin-bottom: 0;
  }
  
  .queue-header {
    flex-wrap: wrap;
    padding: 8px 10px;
  }
  
  .queue-title {
    font-size: 13px;
  }
  
  .queue-actions {
    width: 100%;
    margin-left: 0;
    margin-top: 6px;
    justify-content: flex-end;
  }
  
  .queue-content {
    padding: 8px;
    gap: 8px;
  }
  
  .status-item .value {
    font-size: 16px;
  }
  
  .history-item .task-name {
    max-width: 100px;
  }
  
  .scheduler-item {
    padding: 5px 8px;
  }
}
</style>
