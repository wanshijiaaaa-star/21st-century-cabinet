<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Message, Modal } from '@arco-design/web-vue'
import {
  getFilterRules,
  deleteFilterRule,
  updateFilterRule,
  type FilterRule
} from '@/api/filterRule'
import { getSubscriptions, type Subscription } from '@/api/subscription'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const ruleList = ref<FilterRule[]>([])
const mpList = ref<Subscription[]>([])
const selectedMpId = ref<string>('')
const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0
})

const isMobile = ref(window.innerWidth < 768)

// 获取公众号列表
const fetchMpList = async () => {
  try {
    const res = await getSubscriptions({ page: 0, pageSize: 100 })
    mpList.value = res.list || []
  } catch (error) {
    console.error('获取公众号列表失败:', error)
  }
}

// 获取规则列表
const fetchRuleList = async () => {
  loading.value = true
  try {
    const params: { mp_id?: string; limit: number; offset: number } = {
      limit: pagination.value.pageSize,
      offset: (pagination.value.current - 1) * pagination.value.pageSize
    }
    if (selectedMpId.value) {
      params.mp_id = selectedMpId.value
    }
    const res = await getFilterRules(params)
    ruleList.value = res.list || []
    pagination.value.total = res.page?.total || 0
  } catch (error) {
    console.error('获取规则列表失败:', error)
    Message.error('获取规则列表失败')
  } finally {
    loading.value = false
  }
}

// 获取公众号名称（支持单个或多个）
const getMpNames = (mpIds: string[] | string) => {
  if (!mpIds) return '全局规则'
  const ids = Array.isArray(mpIds) ? mpIds : [mpIds]
  if (ids.length === 0) return '全局规则'
  const names = ids.map(id => {
    const mp = mpList.value.find(m => m.id === id)
    return mp?.mp_name || id
  })
  return names.join(', ')
}

// 获取第一个公众号名称（用于头像显示）
const getFirstMpName = (mpIds: string[] | string) => {
  if (!mpIds) return '全'
  const ids = Array.isArray(mpIds) ? mpIds : [mpIds]
  if (ids.length === 0) return '全'
  const mp = mpList.value.find(m => m.id === ids[0])
  return mp?.mp_name?.charAt(0) || ids[0]?.charAt(0) || '?'
}

// 处理筛选变化
const handleFilterChange = () => {
  pagination.value.current = 1
  fetchRuleList()
}

// 分页变化
const handlePageChange = (page: number) => {
  pagination.value.current = page
  fetchRuleList()
}

// 加载更多（移动端）
const handleLoadMore = async () => {
  loading.value = true
  try {
    pagination.value.current += 1
    const params: { mp_id?: string; limit: number; offset: number } = {
      limit: pagination.value.pageSize,
      offset: (pagination.value.current - 1) * pagination.value.pageSize
    }
    if (selectedMpId.value) {
      params.mp_id = selectedMpId.value
    }
    const res = await getFilterRules(params)
    ruleList.value = [...ruleList.value, ...res.list]
    pagination.value.total = res.page?.total || 0
  } finally {
    loading.value = false
  }
}

// 添加规则
const handleAdd = () => {
  router.push('/filter-rules/add')
}

// 编辑规则
const handleEdit = (id: number) => {
  router.push(`/filter-rules/edit/${id}`)
}

// 切换状态
const handleToggleStatus = async (rule: FilterRule) => {
  const newStatus = rule.status === 1 ? 2 : 1
  try {
    await updateFilterRule(rule.id, { status: newStatus })
    Message.success(newStatus === 1 ? '规则已启用' : '规则已禁用')
    fetchRuleList()
  } catch (error) {
    Message.error('操作失败')
  }
}

// 删除规则
const handleDelete = (id: number) => {
  Modal.confirm({
    title: '确认删除',
    content: '确定要删除这条过滤规则吗？删除后无法恢复',
    okText: '确认',
    cancelText: '取消',
    onOk: async () => {
      try {
        await deleteFilterRule(id)
        Message.success('删除成功')
        fetchRuleList()
      } catch (error) {
        Message.error('删除失败')
      }
    }
  })
}

// 预览规则配置
const previewRule = (rule: FilterRule) => {
  const config: string[] = []
  if (rule.remove_ids?.length) config.push(`移除ID: ${rule.remove_ids.join(', ')}`)
  if (rule.remove_classes?.length) config.push(`移除Class: ${rule.remove_classes.join(', ')}`)
  if (rule.remove_selectors?.length) config.push(`CSS选择器: ${rule.remove_selectors.join(', ')}`)
  if (rule.remove_regex?.length) config.push(`正则: ${rule.remove_regex.length}条`)
  if (rule.remove_normal_tag) config.push('移除常见元素')
  return config.length ? config.join(' | ') : '无过滤配置'
}

onMounted(() => {
  fetchMpList()
  // 从路由参数获取mp_id
  if (route.query.mp_id) {
    selectedMpId.value = route.query.mp_id as string
  }
  fetchRuleList()
})
</script>

<template>
  <a-spin :loading="loading">
    <div class="filter-rule-list">
      <div class="header">
        <h2>HTML过滤规则</h2>
        <a-select
          v-model="selectedMpId"
          placeholder="选择公众号筛选"
          allow-clear
          style="width: 200px; margin-right: 10px;"
          @change="handleFilterChange"
        >
          <a-option value="">全部公众号</a-option>
          <a-option
            v-for="mp in mpList"
            :key="mp.id"
            :value="mp.id"
            :label="mp.mp_name"
          />
        </a-select>
        <a-button type="primary" @click="handleAdd">
          <template #icon><icon-plus /></template>
          添加规则
        </a-button>
      </div>
      <a-alert type="info" closable style="margin-bottom: 16px">
        过滤规则用于在采集文章后自动清理HTML内容，可移除广告、无关元素等。每个公众号可配置多条规则，按优先级依次执行。
      </a-alert>

      <div v-if="!isMobile" class="table-wrapper">
        <a-table
          :data="ruleList"
          :pagination="pagination"
          :loading="loading"
          @page-change="handlePageChange"
        >
          <template #columns>
            <a-table-column title="公众号" :width="200">
              <template #cell="{ record }">
                <div class="mp-info">
                  <a-avatar :size="24" :style="{ backgroundColor: '#3370ff' }">
                    {{ getFirstMpName(record.mp_ids) }}
                  </a-avatar>
                  <a-tooltip :content="getMpNames(record.mp_ids)">
                    <span class="mp-name">{{ getMpNames(record.mp_ids) }}</span>
                  </a-tooltip>
                </div>
              </template>
            </a-table-column>
            <a-table-column title="规则名称" data-index="rule_name" :width="180" />
            <a-table-column title="过滤配置" ellipsis>
              <template #cell="{ record }">
                <a-tooltip :content="previewRule(record)">
                  <span class="rule-preview">{{ previewRule(record) }}</span>
                </a-tooltip>
              </template>
            </a-table-column>
            <a-table-column title="优先级" data-index="priority" :width="80" align="center" />
            <a-table-column title="状态" :width="100" align="center">
              <template #cell="{ record }">
                <a-tag :color="record.status === 1 ? 'green' : 'red'">
                  {{ record.status === 1 ? '启用' : '禁用' }}
                </a-tag>
              </template>
            </a-table-column>
            <a-table-column title="操作" :width="200" align="center">
              <template #cell="{ record }">
                <a-space>
                  <a-button size="mini" type="primary" @click="handleEdit(record.id)">编辑</a-button>
                  <a-button
                    size="mini"
                    :type="record.status === 1 ? 'outline' : 'primary'"
                    :status="record.status === 1 ? 'warning' : 'success'"
                    @click="handleToggleStatus(record)"
                  >
                    {{ record.status === 1 ? '禁用' : '启用' }}
                  </a-button>
                  <a-button size="mini" status="danger" @click="handleDelete(record.id)">删除</a-button>
                </a-space>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </div>

      <a-list v-else :bordered="false">
          <a-list-item v-for="item in ruleList" :key="item.id">
            <a-list-item-meta>
              <template #title>
                <div class="mobile-title">
                  <span>{{ item.rule_name }}</span>
                  <a-tag :color="item.status === 1 ? 'green' : 'red'" size="small">
                    {{ item.status === 1 ? '启用' : '禁用' }}
                  </a-tag>
                </div>
              </template>
              <template #description>
                <div class="mobile-desc">
                  <div>公众号: {{ getMpNames(item.mp_ids) }}</div>
                  <div class="rule-preview">{{ previewRule(item) }}</div>
                  <div>优先级: {{ item.priority }}</div>
                </div>
              </template>
            </a-list-item-meta>
            <template #actions>
              <a-space direction="vertical" size="mini">
                <a-button size="mini" type="primary" long @click="handleEdit(item.id)">编辑</a-button>
                <a-button
                  size="mini"
                  :type="item.status === 1 ? 'outline' : 'primary'"
                  :status="item.status === 1 ? 'warning' : 'success'"
                  long
                  @click="handleToggleStatus(item)"
                >
                  {{ item.status === 1 ? '禁用' : '启用' }}
                </a-button>
                <a-button size="mini" status="danger" long @click="handleDelete(item.id)">删除</a-button>
              </a-space>
            </template>
          </a-list-item>
          <template #footer>
            <div v-if="ruleList.length < pagination.total" class="load-more">
              <a-button long @click="handleLoadMore" :loading="loading">加载更多</a-button>
            </div>
          </template>
        </a-list>
    </div>
  </a-spin>
</template>

<style scoped>
.filter-rule-list {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  flex: 1;
}

.header .arco-btn {
  margin-left: 10px;
}

h2 {
  margin: 0;
  color: var(--color-text-1);
}

.table-wrapper {
  width: 100%;
}

.table-wrapper :deep(.arco-table-container) {
  width: 100%;
}

.mp-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mp-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rule-preview {
  color: var(--color-text-3);
  font-size: 12px;
}

.mobile-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mobile-desc {
  font-size: 12px;
  color: var(--color-text-3);
}

.mobile-desc div {
  margin-bottom: 4px;
}

.load-more {
  width: 120px;
  margin: 0 auto;
  text-align: center;
}

@media (max-width: 768px) {
  .filter-rule-list {
    padding: 12px;
  }
}
</style>
