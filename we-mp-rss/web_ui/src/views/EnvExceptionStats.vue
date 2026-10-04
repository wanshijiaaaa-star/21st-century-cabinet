<template>
  <div class="env-exception-stats">
    <a-page-header title="环境异常统计" subtitle="微信公众号环境异常监控">
      <!-- 日期选择器 -->
      <a-card :bordered="false" class="stats-card">
        <a-space>
          <a-date-picker
            v-model="selectedDate"
            style="width: 200px"
            @change="handleDateChange"
            :disabled-date="disabledDate"
          />
          <a-button type="primary" @click="loadStats" :loading="loading">
            <template #icon><icon-search /></template>
            查询
          </a-button>
          <a-button @click="loadToday" :loading="loading">
            <template #icon><icon-calendar /></template>
            今日统计
          </a-button>
          <a-button @click="refreshStats" :loading="loading">
            <template #icon><icon-refresh /></template>
            刷新
          </a-button>
        </a-space>
      </a-card>

      <!-- 加载状态 -->
      <a-spin :loading="loading" style="width: 100%">
        <!-- 统计概览 -->
        <a-card :bordered="false" class="stats-card" title="统计概览">
          <a-row :gutter="16">
            <a-col :xs="24" :sm="12" :md="6">
              <a-statistic
                title="异常总数"
                :value="stats.total"
                :value-style="stats.total > 0 ? { color: '#f53f3f' } : { color: '#00b42a' }"
              >
                <template #prefix>
                  <icon-exclamation-circle-fill />
                </template>
              </a-statistic>
            </a-col>
            <a-col :xs="24" :sm="12" :md="6">
              <a-statistic
                title="异常URL数"
                :value="Object.keys(stats.urls || {}).length"
              >
                <template #prefix>
                  <icon-link />
                </template>
              </a-statistic>
            </a-col>
          </a-row>
        </a-card>

        <!-- 公众号维度统计 -->
        <a-card
          :bordered="false"
          class="stats-card"
          title="公众号异常统计"
          v-if="Object.keys(stats.mp_stats || {}).length > 0"
        >
          <a-table
            :columns="mpColumns"
            :data="mpTableData"
            :pagination="{ pageSize: 10 }"
            :stripe="true"
            size="small"
          >
            <template #count="{ record }">
              <a-tag :color="record.count > 10 ? 'red' : record.count > 5 ? 'orange' : 'blue'">
                {{ record.count }}
              </a-tag>
            </template>
          </a-table>
        </a-card>

        <!-- 异常URL列表 -->
        <a-card
          :bordered="false"
          class="stats-card"
          title="异常URL列表"
          v-if="Object.keys(stats.urls || {}).length > 0"
        >
          <a-table
            :columns="urlColumns"
            :data="urlTableData"
            :pagination="{ pageSize: 10 }"
            :stripe="true"
            size="small"
          >
            <template #url="{ record }">
              <a-link :href="record.url" target="_blank" hoverable>
                {{ record.url }}
              </a-link>
            </template>
          </a-table>
        </a-card>

      </a-spin>
    </a-page-header>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Message } from '@arco-design/web-vue'
import {
  IconSearch,
  IconCalendar,
  IconRefresh,
  IconExclamationCircleFill,
  IconLink,
  IconUser,
  IconClockCircle,
  IconExclamationCircle,
} from '@arco-design/web-vue/es/icon'
import { getEnvExceptionStats, getTodayStats, type EnvExceptionStats } from '@/api/envException'

const loading = ref(false)
const selectedDate = ref<string>('')
const stats = ref<EnvExceptionStats>({
  date: '',
  total: 0,
  urls: {},
  mp_stats: {},
  recent_logs: [],
})

// 表格列定义
const mpColumns = [
  {
    title: '公众号ID',
    dataIndex: 'mp_id',
    width: '40%',
  },
  {
    title: '异常次数',
    dataIndex: 'count',
    slotName: 'count',
    width: '20%',
    sortable: {
      sortDirections: ['descend', 'ascend'],
    },
  },
  {
    title: '占比',
    dataIndex: 'percentage',
    width: '20%',
  },
]

const urlColumns = [
  {
    title: 'URL',
    dataIndex: 'url',
    slotName: 'url',
  },
  {
    title: '异常时间',
    dataIndex: 'timestamp',
    width: '180px',
  },
]

// 表格数据
const mpTableData = computed(() => {
  const data: any[] = []
  const mpStats = stats.value.mp_stats || {}

  Object.entries(mpStats).forEach(([mpId, count]) => {
    data.push({
      mp_id: mpId,
      count: parseInt(count) || 0,
      percentage: stats.value.total > 0
        ? ((parseInt(count) / stats.value.total) * 100).toFixed(2) + '%'
        : '0%',
    })
  })

  return data.sort((a, b) => b.count - a.count)
})

const urlTableData = computed(() => {
  const data: any[] = []
  const urls = stats.value.urls || {}

  Object.entries(urls).forEach(([url, timestamp]) => {
    data.push({
      url,
      timestamp,
    })
  })

  return data
})

// 禁用未来日期
const disabledDate = (current: Date) => {
  return current && current > new Date()
}

// 解析日志
const parseLog = (logString: string) => {
  try {
    return JSON.parse(logString)
  } catch {
    return {
      url: '',
      mp_name: '',
      mp_id: '',
      timestamp: '',
    }
  }
}

// 加载统计
const loadStats = async () => {
  loading.value = true
  try {
    const date = selectedDate.value || new Date().toISOString().split('T')[0]
    const result = await getEnvExceptionStats(date)
    
    // 确保数据有效
    stats.value = {
      date: result.date || date,
      total: result.total || 0,
      urls: result.urls || {},
      mp_stats: result.mp_stats || {},
      recent_logs: result.recent_logs || []
    }
    
    // 如果没有数据，显示提示
    if (stats.value.total === 0) {
      Message.info('该日期暂无环境异常记录')
    }
  } catch (error: any) {
    Message.error(error.message || '加载统计失败')
    // 设置默认值
    stats.value = {
      date: selectedDate.value || new Date().toISOString().split('T')[0],
      total: 0,
      urls: {},
      mp_stats: {},
      recent_logs: []
    }
  } finally {
    loading.value = false
  }
}

// 加载今日统计
const loadToday = async () => {
  selectedDate.value = ''
  loading.value = true
  try {
    const result = await getTodayStats()
    
    // 确保数据有效
    stats.value = {
      date: result.date || new Date().toISOString().split('T')[0],
      total: result.total || 0,
      urls: result.urls || {},
      mp_stats: result.mp_stats || {},
      recent_logs: result.recent_logs || []
    }
    
    // 如果没有数据，显示提示
    if (stats.value.total === 0) {
      Message.info('今日暂无环境异常记录')
    }
  } catch (error: any) {
    Message.error(error.message || '加载统计失败')
    // 设置默认值
    stats.value = {
      date: new Date().toISOString().split('T')[0],
      total: 0,
      urls: {},
      mp_stats: {},
      recent_logs: []
    }
  } finally {
    loading.value = false
  }
}

// 刷新统计
const refreshStats = () => {
  loadStats()
}

// 日期变化
const handleDateChange = (value: string) => {
  selectedDate.value = value
}

onMounted(() => {
  loadToday()
})
</script>

<style scoped>
.env-exception-stats {
  padding: 16px;
}

.stats-card {
  margin-bottom: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
}

.stats-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

:deep(.arco-statistic-title) {
  font-size: 14px;
  margin-bottom: 8px;
}

:deep(.arco-statistic-content) {
  font-size: 24px;
}

:deep(.arco-table-wrapper) {
  margin-top: -8px;
}
</style>
