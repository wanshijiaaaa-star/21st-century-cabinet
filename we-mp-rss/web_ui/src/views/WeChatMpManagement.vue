<template>
  <div class="wechat-mp-management">
    <a-card title="公众号管理" :bordered="false">
      <a-button type="primary" @click="showAddModal">添加公众号</a-button>
      
      <a-table 
        :columns="columns" 
        :data="mpList" 
        :pagination="pagination"
        @page-change="handlePageChange"
      >
        <template #status="{ record }">
          <a-tag :color="record.status ? 'green' : 'red'">
            {{ record.status ? '已启用' : '已禁用' }}
          </a-tag>
        </template>
        
        <template #action="{ record }">
          <a-space>
            <a-button size="mini" @click="editMp(record)">编辑</a-button>
            <a-button 
              size="mini" 
              type="outline"
              @click="goToFilterRules(record.id)"
            >
              规则
            </a-button>
            <a-button 
              size="mini" 
              status="danger" 
              @click="deleteMp(record.mp_id)"
            >
              删除
            </a-button>
          </a-space>
        </template>
      </a-table>
    </a-card>

    <a-modal 
      v-model:visible="visible" 
      :title="modalTitle"
      @ok="handleOk"
      @cancel="handleCancel"
    >
      <a-form :model="form">
        <a-form-item label="公众号ID" field="mp_id">
          <a-input v-model="form.mp_id" />
        </a-form-item>
        <a-form-item label="公众号名称" field="mp_name">
          <a-input v-model="form.mp_name" />
        </a-form-item>
        <a-form-item label="封面图" field="mp_cover">
          <a-upload
            action="/wx/mps/upload"
            :headers="headers"
            @success="handleUploadSuccess"
          />
        </a-form-item>
        <a-form-item label="简介" field="mp_intro">
          <a-textarea v-model="form.mp_intro" />
        </a-form-item>
        <a-form-item label="状态" field="status">
          <a-switch v-model="form.status" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getSubscriptions, addSubscription, updateSubscription, deleteSubscription } from '@/api/subscription'
import { getToken } from '@/utils/auth'
import { Message } from '@arco-design/web-vue'

const router = useRouter()

const headers = { Authorization: `Bearer ${getToken()}` }

const columns = [
  { title: '公众号ID', dataIndex: 'mp_id' },
  { title: '名称', dataIndex: 'mp_name' },
  { title: '状态', slotName: 'status' },
  { title: '最后同步', dataIndex: 'sync_time' },
  { title: '操作', slotName: 'action' }
]

const mpList = ref([])
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0
})

const visible = ref(false)
const modalTitle = ref('添加公众号')
const form = reactive({
  mp_id: '',
  mp_name: '',
  mp_cover: '',
  mp_intro: '',
  status: true
})

const loadData = async () => {
  try {
    const res = await getSubscriptions({
      page: pagination.current - 1, // 转换为0-based
      pageSize: pagination.pageSize
    })
    
    if (res.code === 0) {
      mpList.value = res.data.list || []
      pagination.total = res.data.total || 0
    } else {
      throw new Error(res.message || '获取公众号列表失败')
    }
  } catch (error) {
    console.error('获取公众号列表错误:', error)
    Message.error(error.message)
  }
}

const showAddModal = () => {
  modalTitle.value = '添加公众号'
  Object.keys(form).forEach(key => {
    if (key === 'status') {
      form[key] = true
    } else {
      form[key] = ''
    }
  })
  visible.value = true
}

const editMp = (record) => {
  modalTitle.value = '编辑公众号'
  Object.assign(form, record)
  visible.value = true
}

const handleOk = async () => {
  if (modalTitle.value === '添加公众号') {
    await addSubscription(form)
  } else {
    await updateSubscription(form.mp_id, form)
  }
  visible.value = false
  loadData()
}

const deleteMp = async (id) => {
  await deleteSubscription(id)
  loadData()
}

const goToFilterRules = (mpId: string) => {
  router.push({ path: '/filter-rules', query: { mp_id: mpId } })
}

const handlePageChange = (page) => {
  pagination.current = page
  loadData()
}

const handleUploadSuccess = (file) => {
  form.mp_cover = file.response.url
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.wechat-mp-management {
  padding: 20px;
}
</style>