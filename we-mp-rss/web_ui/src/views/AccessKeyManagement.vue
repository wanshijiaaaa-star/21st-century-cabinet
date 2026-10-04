<script setup lang="ts">
import { ref, reactive, onMounted, computed, h } from 'vue'
import { 
  createAccessKey, 
  listAccessKeys, 
  updateAccessKey,
  deactivateAccessKey,
  deleteAccessKey 
} from '@/api/accessKey'
import type { AccessKeyResponse, AccessKeyCreateRequest } from '@/api/accessKey'
import { Modal, Message } from '@arco-design/web-vue'
import { IconCopy, IconDelete, IconEdit } from '@arco-design/web-vue/es/icon'

const columns = [
  { title: 'AK 名称', dataIndex: 'name' },
  { title: 'Access Key', dataIndex: 'key', width: '20%', ellipsis: true },
  { title: '权限', dataIndex: 'permissions', width: '15%' },
  { title: '状态', slotName: 'status' },
  { title: '创建时间', dataIndex: 'created_at', width: '12%' },
  { title: '最后使用', dataIndex: 'last_used_at', width: '12%' },
  { title: '操作', slotName: 'action', width: '10%' }
]

const akList = ref<AccessKeyResponse[]>([])
const loading = ref(false)
const error = ref('')
const visible = ref(false)
const modalTitle = ref('创建 Access Key')
const selectedAK = ref<AccessKeyResponse | null>(null)
const showSecretKey = ref(false)

const form = reactive({
  name: '',
  description: '',
  permissions: [] as string[],
  expires_in_days: null as number | null
})

const permissionOptions = [
  { label: '读', value: 'read' },
  { label: '写', value: 'write' },
  { label: '删除', value: 'delete' },
  { label: '管理', value: 'admin' }
]

const fetchAccessKeys = async () => {
  try {
    loading.value = true
    error.value = ''
    const res = await listAccessKeys()
    akList.value = res || []
  } catch (err) {
    error.value = err instanceof Error ? err.message : '获取 Access Key 列表失败'
  } finally {
    loading.value = false
  }
}

const showCreateModal = () => {
  modalTitle.value = '创建 Access Key'
  selectedAK.value = null
  showSecretKey.value = false
  Object.assign(form, {
    name: '',
    description: '',
    permissions: [],
    expires_in_days: null
  })
  visible.value = true
}

const editAccessKey = (record: AccessKeyResponse) => {
  modalTitle.value = '编辑 Access Key'
  selectedAK.value = record
  showSecretKey.value = false
  Object.assign(form, {
    name: record.name,
    description: record.description,
    permissions: record.permissions || [],
    expires_in_days: null
  })
  visible.value = true
}

const handleSubmit = async () => {
  try {
    if (!form.name.trim()) {
      Message.error('请输入 Access Key 名称')
      return
    }

    if (modalTitle.value === '创建 Access Key') {
      const res = await createAccessKey(form as AccessKeyCreateRequest)
      if (res && res.secret) {
        Modal.info({
          title: '创建成功',
          content: h('div', [
            h('p', '请妥善保管 Secret Key，它只会显示一次！'),
            h('p', [h('strong', 'Access Key: '), res.key]),
            h('p', [h('strong', 'Secret Key: '), res.secret]),
          ]),
          okText: '我已记下',
          onOk: () => {
            copyToClipboard(`Access Key: ${res.key}\nSecret Key: ${res.secret}`)
          }
        })
        showSecretKey.value = false
      }
    } else if (selectedAK.value) {
      await updateAccessKey(selectedAK.value.id, {
        name: form.name,
        description: form.description,
        permissions: form.permissions
      })
      Message.success('更新成功')
    }
    
    visible.value = false
    fetchAccessKeys()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '操作失败'
    Message.error(error.value)
  }
}

const handleDeactivate = (record: AccessKeyResponse) => {
  Modal.confirm({
    title: '停用 Access Key',
    content: `确定要停用 "${record.name}" 吗？停用后将无法使用此密钥进行认证。`,
    okText: '停用',
    cancelText: '取消',
    okButtonProps: { status: 'warning' },
    onOk: async () => {
      try {
        await deactivateAccessKey(record.id)
        Message.success('已停用')
        fetchAccessKeys()
      } catch (err) {
        error.value = err instanceof Error ? err.message : '停用失败'
        Message.error(error.value)
      }
    }
  })
}

const handleDelete = (record: AccessKeyResponse) => {
  Modal.confirm({
    title: '删除 Access Key',
    content: `确定要删除 "${record.name}" 吗？此操作不可恢复。`,
    okText: '删除',
    cancelText: '取消',
    okButtonProps: { status: 'danger' },
    onOk: async () => {
      try {
        await deleteAccessKey(record.id)
        Message.success('已删除')
        fetchAccessKeys()
      } catch (err) {
        error.value = err instanceof Error ? err.message : '删除失败'
        Message.error(error.value)
      }
    }
  })
}

const copyToClipboard = (text: string) => {
  // 优先使用现代 Clipboard API
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      Message.success('已复制到剪贴板')
    }).catch(() => {
      fallbackCopy(text)
    })
  } else {
    // 降级方案：使用 execCommand
    fallbackCopy(text)
  }
}

const fallbackCopy = (text: string) => {
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    textarea.style.top = '-9999px'
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()
    const successful = document.execCommand('copy')
    document.body.removeChild(textarea)
    if (successful) {
      Message.success('已复制到剪贴板')
    } else {
      Message.error('复制失败')
    }
  } catch {
    Message.error('复制失败')
  }
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

const getStatusColor = (record: AccessKeyResponse) => {
  if (!record.is_active) return 'red'
  if (record.is_expired) return 'orange'
  return 'green'
}

const getStatusText = (record: AccessKeyResponse) => {
  if (!record.is_active) return '已停用'
  if (record.is_expired) return '已过期'
  return '活跃'
}

onMounted(() => {
  fetchAccessKeys()
})
</script>

<template>
  <div class="ak-management">
    <a-card title="Access Key 管理" :bordered="false">
      <template #extra>
        <a-button type="primary" @click="showCreateModal">+ 创建 Access Key</a-button>
      </template>

      <a-space direction="vertical" fill>
        <a-alert 
          v-if="error" 
          type="error" 
          show-icon 
          closable
          @close="error = ''"
        >
          {{ error }}
        </a-alert>
        
        <a-alert 
          type="info" 
          show-icon
        >
          Access Key 用于程序化访问 API。请妥善保管 Secret Key，它只会在创建时显示一次。
        </a-alert>

        <a-table
          :columns="columns"
          :data="akList"
          :loading="loading"
          row-key="id"
          :pagination="false"
          :scroll="{ x: 1200 }"
        >
          <template #permissions="{ record }">
            <a-space size="small">
              <a-tag v-for="perm in record.permissions" :key="perm" size="small">
                {{ perm }}
              </a-tag>
              <span v-if="!record.permissions || record.permissions.length === 0" class="text-gray">
                无限制
              </span>
            </a-space>
          </template>

          <template #status="{ record }">
            <a-tag :color="getStatusColor(record)">
              {{ getStatusText(record) }}
            </a-tag>
          </template>

          <template #created_at="{ record }">
            {{ formatDate(record.created_at) }}
          </template>

          <template #last_used_at="{ record }">
            {{ formatDate(record.last_used_at) }}
          </template>

          <template #action="{ record }">
            <a-space size="small">
              <a-button 
                type="text" 
                size="small"
                @click="copyToClipboard(record.key)"
                v-if="record.key"
              >
                <template #icon>
                  <icon-copy />
                </template>
              </a-button>
              <a-button 
                type="text" 
                size="small"
                @click="editAccessKey(record)"
                v-if="record.is_active"
              >
                <template #icon>
                  <icon-edit />
                </template>
              </a-button>
              <a-dropdown v-if="record.is_active">
                <template #default>
                  <a-button type="text" size="small">更多</a-button>
                </template>
                <template #content>
                  <a-doption @click="handleDeactivate(record)">停用</a-doption>
                </template>
              </a-dropdown>
              <a-popconfirm 
                content="确定要删除吗？"
                ok-text="删除"
                cancel-text="取消"
                @ok="handleDelete(record)"
              >
                <a-button 
                  type="text" 
                  size="small"
                  status="danger"
                >
                  <template #icon>
                    <icon-delete />
                  </template>
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </a-table>

        <a-empty v-if="!loading && akList.length === 0" description="暂无 Access Key" />
      </a-space>
    </a-card>

    <!-- 创建/编辑模态框 -->
    <a-modal
      v-model:visible="visible"
      :title="modalTitle"
      width="600px"
      @ok="handleSubmit"
      @cancel="visible = false"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="AK 名称" field="name" required>
          <a-input 
            v-model="form.name" 
            placeholder="例如：生产环境爬虫"
            @keyup.enter="handleSubmit"
          />
        </a-form-item>

        <a-form-item label="描述" field="description">
          <a-textarea 
            v-model="form.description" 
            placeholder="可选：用途说明、备注等"
            :rows="3"
          />
        </a-form-item>

        <a-form-item label="权限范围" field="permissions">
          <a-checkbox-group v-model="form.permissions" :options="permissionOptions" />
          <div class="form-hint">不选择任何权限则使用账户默认权限</div>
        </a-form-item>

        <a-form-item label="过期时间" field="expires_in_days">
          <a-input-number 
            v-model="form.expires_in_days" 
            placeholder="天数（留空表示永不过期）"
            :min="1"
            :max="36500"
          />
          <div class="form-hint">为安全起见，建议设置合理的过期时间</div>
        </a-form-item>

        <a-alert 
          v-if="modalTitle === '创建 Access Key'"
          type="warning"
          show-icon
        >
          创建后，Secret Key 只会显示一次，请妥善保管！
        </a-alert>
      </a-form>
    </a-modal>
  </div>
</template>

<style scoped>
.ak-management {
  padding: 20px;
}

.form-hint {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

:deep(.text-gray) {
  color: #999;
}

:deep(.arco-table-cell) {
  padding: 12px 16px;
}
</style>