<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { 
  getConfig, 
  updateConfig, 
  deleteConfig 
} from '@/api/configManagement'
import type { ConfigManagement, ConfigManagementUpdate } from '@/types/configManagement'
import { Modal } from '@arco-design/web-vue'

const route = useRoute()
const router = useRouter()
const config = ref<ConfigManagement | null>(null)
const loading = ref(false)
const error = ref('')
const isEditing = ref(false)
const form = reactive<ConfigManagementUpdate>({
  config_value: '',
  description: ''
})

const fetchConfig = async (key: string) => {
  try {
    loading.value = true
    const { data } = await getConfig(key)
    config.value = data
    Object.assign(form, {
      config_value: data.config_value,
      description: data.description
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : '获取配置详情失败'
  } finally {
    loading.value = false
  }
}

const handleUpdate = async () => {
  try {
    loading.value = true
    if (config.value) {
      await updateConfig(config.value.config_key, form)
      await fetchConfig(route.params.key as string)
      isEditing.value = false
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '更新配置失败'
  } finally {
    loading.value = false
  }
}

const handleDelete = () => {
  if (!config.value) return
  
  Modal.confirm({
    title: '确认删除',
    content: '确定要删除此配置吗？',
    okText: '删除',
    cancelText: '取消',
    onOk: async () => {
      try {
        await deleteConfig(config.value!.config_key)
        router.push('/configs')
      } catch (err) {
        error.value = err instanceof Error ? err.message : '删除配置失败'
      }
    }
  })
}

onMounted(() => {
  fetchConfig(route.params.key as string)
})
</script>

<template>
  <div class="config-detail">
    <a-page-header 
      :title="config ? `配置详情 - ${config.config_key}` : '配置详情'"
      @back="router.push('/configs')"
    >
      <template #extra>
        <a-space>
          <a-button v-if="!isEditing" type="primary" @click="isEditing = true">
            <template #icon>
              <icon-edit />
            </template>
            编辑
          </a-button>
          <a-button v-if="!isEditing" status="danger" @click="handleDelete">
            <template #icon>
              <icon-delete />
            </template>
            删除
          </a-button>
          <a-button v-if="isEditing" type="primary" @click="handleUpdate">
            <template #icon>
              <icon-save />
            </template>
            保存
          </a-button>
          <a-button v-if="isEditing" @click="isEditing = false">
            <template #icon>
              <icon-close />
            </template>
            取消
          </a-button>
        </a-space>
      </template>
    </a-page-header>

    <a-card>
      <a-space direction="vertical" fill>
        <a-alert v-if="error" type="error" show-icon>{{ error }}</a-alert>
        
        <div v-if="loading">
          <a-skeleton :animation="true">
            <a-skeleton-line :rows="5" />
          </a-skeleton>
        </div>
        <div v-else-if="config">
          <a-descriptions v-if="!isEditing" :column="1" bordered>
            <a-descriptions-item label="配置键">
              {{ config.config_key }}
            </a-descriptions-item>
            <a-descriptions-item label="配置值">
              {{ config.config_value }}
            </a-descriptions-item>
            <a-descriptions-item label="描述">
              {{ config.description }}
            </a-descriptions-item>
            <a-descriptions-item label="创建时间">
              {{ config.created_at }}
            </a-descriptions-item>
            <a-descriptions-item label="更新时间">
              {{ config.updated_at }}
            </a-descriptions-item>
          </a-descriptions>

          <a-form v-else :model="form" layout="vertical">
            <a-form-item label="配置键">
              <a-input v-model="config.config_key" disabled />
            </a-form-item>
            <a-form-item label="配置值" field="config_value" required>
              <a-input v-model="form.config_value" />
            </a-form-item>
            <a-form-item label="描述" field="description">
              <a-textarea v-model="form.description" />
            </a-form-item>
          </a-form>
        </div>
      </a-space>
    </a-card>
  </div>
</template>

<style scoped>
.config-detail {
  padding: 20px;
}
</style>