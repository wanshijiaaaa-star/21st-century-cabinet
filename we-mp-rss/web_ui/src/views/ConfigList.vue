<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { 
  listConfigs, 
  createConfig, 
  updateConfig, 
  deleteConfig 
} from '@/api/configManagement'
import type { ConfigManagement } from '@/types/configManagement'
import { Modal } from '@arco-design/web-vue'

const columns = [
  { title: '配置键', dataIndex: 'config_key' },
  { title: '配置值', dataIndex: 'config_value', width: '30%', ellipsis: true },
  { title: '描述', dataIndex: 'description' },
  // { title: '状态', slotName: 'status' },
  // { title: '操作', slotName: 'action' }
]

const configList = ref<any>([])
const loading = ref(false)
const error = ref('')
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0
})

const visible = ref(false)
const modalTitle = ref('添加配置')
const form = reactive({
  config_key: '',
  config_value: '',
  description: ''
})

const fetchConfigs = async () => {
  try {
    loading.value = true
    const res= await listConfigs({
      page: pagination.current,
      pageSize: pagination.pageSize
    })
    configList.value = res.list
    pagination.total = res.total
  } catch (err) {
    error.value = err instanceof Error ? err.message : '获取配置列表失败'
  } finally {
    loading.value = false
  }
}

const showAddModal = () => {
  modalTitle.value = '添加配置'
  Object.keys(form).forEach(key => {
    form[key] = ''
  })
  visible.value = true
}

const editConfig = (record: ConfigManagement) => {
  modalTitle.value = '编辑配置'
  Object.assign(form, record)
  visible.value = true
}

const handleSubmit = async () => {
  try {
    if (modalTitle.value === '添加配置') {
      await createConfig(form)
    } else {
      await updateConfig(form.config_key, form)
    }
    visible.value = false
    fetchConfigs()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '保存配置失败'
  }
}

const deleteConfigItem = async (key: string) => {
  Modal.confirm({
    title: '确认删除',
    content: '确定要删除此配置吗？',
    okText: '删除',
    cancelText: '取消',
    onOk: async () => {
      try {
        await deleteConfig(key)
        fetchConfigs()
      } catch (err) {
        error.value = err instanceof Error ? err.message : '删除配置失败'
      }
    }
  })
}

const handlePageChange = (page: number) => {
  pagination.current = page
  fetchConfigs()
}

onMounted(() => {
  fetchConfigs()
})
</script>

<template>
  <div class="config-management">
    <a-card title="配置" :bordered="false">
      <a-space direction="vertical" fill>
        <a-alert v-if="error" type="error" show-icon>{{ error }}</a-alert>
        
        <a-table
          :columns="columns"
          :data="configList"
          :loading="loading"
          :pagination="pagination"
          @page-change="handlePageChange"
          row-key="config_key"
        >
          <template #status="{ record }">
            <a-tag color="green">已启用</a-tag>
          </template>
          
          <template #action="{ record }">
            <a-space>
              <!-- 操作按钮已隐藏 -->
            </a-space>
          </template>
        </a-table>
      </a-space>
    </a-card>

    <a-modal
      v-model:visible="visible"
      :title="modalTitle"
      @ok="handleSubmit"
      @cancel="visible = false"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="配置键" field="config_key" required>
          <a-input v-model="form.config_key" :disabled="modalTitle === '编辑配置'" />
        </a-form-item>
        <a-form-item label="配置值" field="config_value" required>
          <a-input v-model="form.config_value" />
        </a-form-item>
        <a-form-item label="描述" field="description">
          <a-textarea v-model="form.description" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<style scoped>
.config-management {
  padding: 20px;
}
</style>