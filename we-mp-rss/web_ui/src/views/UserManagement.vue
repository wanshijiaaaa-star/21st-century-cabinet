<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import { 
  getUserList, 
  addUser, 
  updateUserById, 
  deleteUser,
  getUserInfo,
  resetUserPassword
} from '@/api/user'
import type { UserListResponse, AddUserParams } from '@/api/user'
import { Modal, Message } from '@arco-design/web-vue'
import { IconPlus, IconEdit, IconDelete } from '@arco-design/web-vue/es/icon'

// 检查当前用户权限
const checkPermission = async () => {
  try {
    const userInfo = await getUserInfo()
    console.log('当前用户信息:', userInfo)
    if (userInfo && userInfo.role !== 'admin') {
      Message.error('您没有管理员权限，无法访问用户管理页面')
    }
  } catch (err) {
    console.error('获取用户信息失败:', err)
  }
}

const columns = [
  { title: '用户名', dataIndex: 'username', width: '15%' },
  { title: '昵称', dataIndex: 'nickname', width: '15%' },
  { title: '邮箱', dataIndex: 'email', width: '18%' },
  { title: '角色', slotName: 'role', width: '10%' },
  { title: '权限', slotName: 'permissions', width: '15%' },
  { title: '状态', slotName: 'status', width: '8%' },
  { title: '创建时间', slotName: 'created_at', width: '12%' },
  { title: '操作', slotName: 'action', width: '10%' }
]

const userList = ref<UserListResponse[]>([])
const loading = ref(false)
const error = ref('')
const visible = ref(false)
const modalTitle = ref('添加用户')
const selectedUser = ref<UserListResponse | null>(null)
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0
})

// 重置密码相关
const resetPasswordVisible = ref(false)
const resetPasswordUser = ref<UserListResponse | null>(null)
const newPassword = ref('')
const confirmPassword = ref('')

const form = reactive<AddUserParams>({
  username: '',
  password: '',
  nickname: '',
  email: '',
  role: 'user',
  permissions: []
})

const roleOptions = [
  { label: '管理员', value: 'admin' },
  { label: '编辑', value: 'editor' },
  { label: '普通用户', value: 'user' }
]

const permissionOptions = [
  { label: '读', value: 'read' },
  { label: '写', value: 'write' },
  { label: '删除', value: 'delete' },
  { label: '管理', value: 'admin' }
]

const fetchUsers = async () => {
  try {
    loading.value = true
    error.value = ''
    const res = await getUserList({
      page: pagination.current,
      page_size: pagination.pageSize
    })
    if (res) {
      // 如果 res 本身就是数组，直接使用
      if (Array.isArray(res)) {
        userList.value = res
        pagination.total = res.length
      } else {
        userList.value = res.list || []
        pagination.total = res.total || 0
      }
    }
  } catch (err) {
    console.error('获取用户列表失败:', err)
    error.value = err instanceof Error ? err.message : '获取用户列表失败'
    Message.error(error.value)
  } finally {
    loading.value = false
  }
}

const showAddModal = () => {
  modalTitle.value = '添加用户'
  selectedUser.value = null
  Object.assign(form, {
    username: '',
    password: '',
    nickname: '',
    email: '',
    role: 'user',
    permissions: []
  })
  visible.value = true
}

const editUser = (record: UserListResponse) => {
  modalTitle.value = '编辑用户'
  selectedUser.value = record
  Object.assign(form, {
    username: record.username,
    password: '',
    nickname: record.nickname,
    email: record.email,
    role: record.role,
    permissions: record.permissions || []
  })
  visible.value = true
}

const handleSubmit = async () => {
  try {
    if (!form.username.trim()) {
      Message.error('请输入用户名')
      return
    }

    if (modalTitle.value === '添加用户') {
      if (!form.password.trim()) {
        Message.error('请输入密码')
        return
      }
      await addUser(form)
      Message.success('添加成功')
    } else if (selectedUser.value) {
      await updateUserById(selectedUser.value.id, {
        nickname: form.nickname,
        email: form.email,
        role: form.role,
        permissions: form.permissions
      })
      Message.success('更新成功')
    }
    
    visible.value = false
    fetchUsers()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '操作失败'
    Message.error(error.value)
  }
}

const handleToggleStatus = (record: UserListResponse) => {
  const newStatus = !record.is_active
  const action = newStatus ? '启用' : '停用'
  
  Modal.confirm({
    title: `${action}用户`,
    content: `确定要${action}用户 "${record.username}" 吗？`,
    okText: action,
    cancelText: '取消',
    okButtonProps: { status: newStatus ? 'normal' : 'warning' },
    onOk: async () => {
      try {
        await updateUserById(record.id, { is_active: newStatus })
        Message.success(`已${action}`)
        fetchUsers()
      } catch (err) {
        error.value = err instanceof Error ? err.message : `${action}失败`
        Message.error(error.value)
      }
    }
  })
}

const handleDelete = (record: UserListResponse) => {
  Modal.confirm({
    title: '删除用户',
    content: `确定要删除用户 "${record.username}" 吗？此操作不可恢复。`,
    okText: '删除',
    cancelText: '取消',
    okButtonProps: { status: 'danger' },
    onOk: async () => {
      try {
        await deleteUser(record.id)
        Message.success('已删除')
        fetchUsers()
      } catch (err) {
        error.value = err instanceof Error ? err.message : '删除失败'
        Message.error(error.value)
      }
    }
  })
}

const showResetPasswordModal = (record: UserListResponse) => {
  resetPasswordUser.value = record
  newPassword.value = ''
  confirmPassword.value = ''
  resetPasswordVisible.value = true
}

const handleResetPassword = async () => {
  if (!resetPasswordUser.value) return

  if (!newPassword.value.trim()) {
    Message.error('请输入新密码')
    return
  }

  if (newPassword.value.length < 8) {
    Message.error('密码长度不能少于8位')
    return
  }

  if (!confirmPassword.value.trim()) {
    Message.error('请确认新密码')
    return
  }

  if (newPassword.value !== confirmPassword.value) {
    Message.error('两次输入的密码不一致')
    return
  }

  try {
    await resetUserPassword(resetPasswordUser.value.id, newPassword.value)
    Message.success('密码重置成功')
    resetPasswordVisible.value = false
    newPassword.value = ''
    confirmPassword.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '密码重置失败'
    Message.error(error.value)
  }
}

const handlePageChange = (page: number) => {
  pagination.current = page
  fetchUsers()
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

const getRoleText = (role: string) => {
  const roleMap: Record<string, string> = {
    admin: '管理员',
    editor: '编辑',
    user: '普通用户'
  }
  return roleMap[role] || role
}

onMounted(() => {
  checkPermission()
  fetchUsers()
})
</script>

<template>
  <div class="user-management">
    <a-card title="用户管理" :bordered="false">
      <template #extra>
        <a-button type="primary" @click="showAddModal">
          <template #icon>
            <icon-plus />
          </template>
          添加用户
        </a-button>
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
          管理系统用户，可以添加、编辑、启用/停用和删除用户。管理员拥有所有权限。
        </a-alert>

        <a-table
          :columns="columns"
          :data="userList"
          :loading="loading"
          row-key="id"
          :pagination="{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showTotal: true
          }"
          :scroll="{ x: 1200 }"
          @page-change="handlePageChange"
        >
          <template #role="{ record }">
            <a-tag :color="record.role === 'admin' ? 'red' : record.role === 'editor' ? 'blue' : 'green'">
              {{ getRoleText(record.role) }}
            </a-tag>
          </template>

          <template #permissions="{ record }">
            <a-space size="small" wrap>
              <a-tag v-for="perm in record.permissions" :key="perm" size="small">
                {{ perm }}
              </a-tag>
              <span v-if="!record.permissions || record.permissions.length === 0" class="text-gray">
                无限制
              </span>
            </a-space>
          </template>

          <template #status="{ record }">
            <a-tag :color="record.is_active ? 'green' : 'red'">
              {{ record.is_active ? '活跃' : '已停用' }}
            </a-tag>
          </template>

          <template #created_at="{ record }">
            {{ formatDate(record.created_at) }}
          </template>

          <template #action="{ record }">
            <a-space size="small">
              <a-button
                type="text"
                size="small"
                @click="editUser(record)"
              >
                <template #icon>
                  <icon-edit />
                </template>
              </a-button>
              <a-button
                type="text"
                size="small"
                status="success"
                @click="showResetPasswordModal(record)"
              >
                重置密码
              </a-button>
              <a-button 
                type="text" 
                size="small"
                :status="record.is_active ? 'warning' : 'success'"
                @click="handleToggleStatus(record)"
              >
                {{ record.is_active ? '停用' : '启用' }}
              </a-button>
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

        <a-empty v-if="!loading && userList.length === 0" description="暂无用户" />
      </a-space>
    </a-card>

    <!-- 添加/编辑用户模态框 -->
    <a-modal
      v-model:visible="visible"
      :title="modalTitle"
      width="600px"
      @ok="handleSubmit"
      @cancel="visible = false"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="用户名" field="username" required>
          <a-input 
            v-model="form.username" 
            placeholder="请输入用户名"
            :disabled="modalTitle === '编辑用户'"
          />
        </a-form-item>

        <a-form-item 
          v-if="modalTitle === '添加用户'" 
          label="密码" 
          field="password" 
          required
        >
          <a-input-password 
            v-model="form.password" 
            placeholder="请输入密码"
          />
        </a-form-item>

        <a-form-item label="昵称" field="nickname">
          <a-input 
            v-model="form.nickname" 
            placeholder="请输入昵称（可选）"
          />
        </a-form-item>

        <a-form-item label="邮箱" field="email">
          <a-input 
            v-model="form.email" 
            placeholder="请输入邮箱（可选）"
          />
        </a-form-item>

        <a-form-item label="角色" field="role">
          <a-select v-model="form.role" :options="roleOptions" />
          <div class="form-hint">管理员拥有所有权限</div>
        </a-form-item>

        <a-form-item label="权限" field="permissions">
          <a-checkbox-group v-model="form.permissions" :options="permissionOptions" />
          <div class="form-hint">不选择任何权限则使用角色默认权限</div>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 重置密码模态框 -->
    <a-modal
      v-model:visible="resetPasswordVisible"
      title="重置用户密码"
      width="400px"
      @ok="handleResetPassword"
      @cancel="resetPasswordVisible = false"
    >
      <a-form layout="vertical">
        <a-form-item label="新密码" required>
          <a-input-password
            v-model="newPassword"
            placeholder="请输入新密码（至少8位）"
          />
        </a-form-item>
        <a-form-item label="确认密码" required>
          <a-input-password
            v-model="confirmPassword"
            placeholder="请再次输入新密码"
          />
        </a-form-item>
        <a-alert type="warning" show-icon>
          重置后，用户需要使用新密码重新登录
        </a-alert>
      </a-form>
    </a-modal>
  </div>
</template>

<style scoped>
.user-management {
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
