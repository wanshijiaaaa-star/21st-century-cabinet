<script setup lang="ts">
import { ref } from 'vue'
import type { MessageTask } from '@/types/messageTask'

const props = defineProps<{
  taskList: MessageTask[]
  loading: boolean
  pagination: {
    current: number
    pageSize: number
    total: number
  }
  isMobile: boolean
}>()

const emit = defineEmits<{
  (e: 'pageChange', page: number): void
  (e: 'loadMore'): void
  (e: 'edit', id: number): void
  (e: 'test', id: number): void
  (e: 'run', id: number): void
  (e: 'delete', id: number): void
}>()

const parseCronExpression = (exp: string) => {
  const parts = exp.split(' ')
  if (parts.length !== 5) return exp
  
  const [minute, hour, day, month, week] = parts
  
  // 解析单个部分的辅助函数
  const parsePart = (value: string, unit: string) => {
    if (value === '*') {
      return `每${unit}`
    }
    // 支持 9-23/3 这种格式（范围+步长）
    if (value.includes('/') && value.includes('-')) {
      const [range, step] = value.split('/')
      const [start, end] = range.split('-')
      return `${start}到${end}${unit}每${step}${unit}`
    }
    if (value.includes('/')) {
      const [_, interval] = value.split('/')
      return `每${interval}${unit}`
    }
    if (value.includes('-')) {
      const [start, end] = value.split('-')
      return `${start}到${end}${unit}`
    }
    if (value.includes(',')) {
      return `在${value.split(',').join('、')}${unit}`
    }
    return `在${value}${unit}`
  }
  
  let result = ''
  
  // 解析分钟
  result += parsePart(minute, '分钟')
  
  // 解析小时
  result += ' ' + parsePart(hour, '小时')
  
  // 解析日期
  result += ' ' + parsePart(day, '天')
  
  // 解析月份
  result += ' ' + parsePart(month, '月')
  
  // 解析星期
  if (week !== '*') {
    result += ' 星期' + week
  }
  
  return result || exp
}
</script>

<template>
  <div>
    <a-table v-if="!props.isMobile"
      :data="taskList"
      :pagination="pagination"
      @page-change="emit('pageChange', $event)"
    >
      <template #columns>
        <a-table-column title="名称" data-index="name" ellipsis :width="200"/>
        <a-table-column title="Cron表达式">
          <template #cell="{ record }">
            {{ parseCronExpression(record.cron_exp) }}
          </template>
        </a-table-column>
        <a-table-column title="类型" :width="100">
          <template #cell="{ record }">
            <a-tag :color="record.message_type === 1 ? 'green' : 'red'">
              {{ record.message_type === 1 ? 'WeekHook' : 'Message' }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="状态" :width="100">
          <template #cell="{ record }">
            <a-tag :color="record.status === 1 ? 'green' : 'red'">
              {{ record.status === 1 ? '启用' : '禁用' }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="操作" :width="260">
          <template #cell="{ record }">
            <slot name="actions" :record="record"></slot>
          </template>
        </a-table-column>
      </template>
    </a-table>
    <a-list v-else :data="props.taskList" :bordered="false">
      <template #item="{ item }">
        <a-list-item>
          <a-list-item-meta>
            <template #title>
              {{ item.name }}
            </template>
            <template #description>
              <div>{{ parseCronExpression(item.cron_exp) }}</div>
              <div>
                <a-tag :color="item.message_type === 1 ? 'green' : 'red'">
                  {{ item.message_type === 1 ? 'WeekHook' : 'Message' }}
                </a-tag>
                <a-tag :color="item.status === 1 ? 'green' : 'red'">
                  {{ item.status === 1 ? '启用' : '禁用' }}
                </a-tag>
              </div>
            </template>
          </a-list-item-meta>
          
          <slot name="mobile-actions" :record="item"></slot>
        </a-list-item>
      </template>
      <template #footer>
        <div v-if="pagination.current * pagination.pageSize < pagination.total" class="load-more">
          <a-button type="primary" long :loading="loading" @click="emit('loadMore')">加载更多</a-button>
          <div class="total-count">
                共 {{ pagination.total }} 条
              </div>
        </div>
      </template>
    </a-list>
  </div>
</template>

<style scoped>
/* 移动端列表样式 */
.a-list {
  margin-top: 16px;
}

.a-list-item {
  padding: 12px 16px;
  margin-bottom: 8px;
  background-color: var(--color-bg-2);
  border-radius: 4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  transition: all 0.2s;
}

.a-list-item:hover {
  background-color: var(--color-bg-3);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.a-list-item-meta-title {
  font-weight: 500;
  margin-bottom: 4px;
}

.a-list-item-meta-description {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.a-list-item-meta-description .arco-tag {
  margin-right: 8px;
}

.a-list-item-extra {
  display: flex;
  gap: 8px;
}

.load-more{
    width: 120px;
    margin: 0px auto;
    text-align: center;
}
</style>