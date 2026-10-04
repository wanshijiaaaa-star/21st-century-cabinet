<script setup lang="ts">
import { ref, onMounted, nextTick} from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getTag, createTag, updateTag } from '@/api/tagManagement'
import type { Tag, TagCreate } from '@/types/tagManagement'
import { Message } from '@arco-design/web-vue'
import { uploadFile } from '@/api/file'
import MpMultiSelect from '@/components/MpMultiSelect.vue'

const route = useRoute()
const router = useRouter()
const isEdit = ref(false)
const loading = ref(false)
const formLoading = ref(false)

const formModel = ref<TagCreate>({
  name: '',
  cover: null,
  intro: null,
  status: 1,
  mps_id: []
})

const rules = {
  name: [{ required: true, message: '请输入标签名称' }]
}

const fetchTag = async (id: string) => {
  try {
    loading.value = true
    const res = await getTag(id)
    formModel.value = {
      ...res,
      mps_id: JSON.parse(res.mps_id||[]),
    }
     // 初始化选择器数据
    nextTick(() => {
      if (mpSelectorRef.value) {
        mpSelectorRef.value.parseSelected(formModel.value.mps_id)
      }
    })
  } catch (error) {
    Message.error('获取标签详情失败')
  } finally {
    loading.value = false
  }
}

const handleUploadChange = async (options: any) => {
  const file = options.fileItem?.file || options.file
  
  // 文件类型验证
  if (!file?.type?.startsWith('image/')) {
    Message.error('请选择图片文件 (JPEG/PNG)')
    return
  }

  // 文件大小验证 (2MB)
  if (file.size > 2 * 1024 * 1024) {
    Message.error('图片大小不能超过2MB')
    return
  }

  try {
    const res = await uploadFile(file)
    console.log(res)
    formModel.value.cover = res.url
  } catch (error) {
    console.error('上传错误:', error)
    Message.error(`上传失败: ${error.response?.data?.message || error.message || '服务器错误'}`)
  } 
  return false
}

const handleExceed = () => {
  Message.warning('只能上传一个封面文件')
}

const handleUploadError = (error: Error) => {
  Message.error(`上传出错: ${error.message || '文件上传失败'}`)
}

const showMpSelector = ref(false)
const mpSelectorRef = ref<InstanceType<typeof MpMultiSelect> | null>(null)

const handleImageError = (e: Event) => {
  const img = e.target as HTMLImageElement
  img.src = '/default-cover.png'
}

const handleSubmit = async () => {
  try {
    formLoading.value = true
     // 将mps_id转换为字符串
    const submitData = {
      ...formModel.value,
      mps_id: JSON.stringify(formModel.value.mps_id)
    }
    
    if (isEdit.value) {
      await updateTag(route.params.id as string,submitData)
      Message.success('更新成功')
    } else {
      await createTag(submitData)
      Message.success('创建成功')
    }
    router.push('/tags')
  } catch (error) {
    Message.error(isEdit.value ? '更新失败' : '创建失败')
  } finally {
    formLoading.value = false
  }
}

onMounted(() => {
  if (route.params.id) {
    isEdit.value = true
    fetchTag(route.params.id as string)
  }
})
</script>

<template>
  <div class="tag-form">
    <a-page-header
      :title="isEdit ? '编辑标签' : '添加标签'"
      subtitle="标签信息"
      @back="router.go(-1)"
    />

    <a-card :loading="loading">
      <a-form
        :model="formModel"
        :rules="rules"
        layout="vertical"
        @submit="handleSubmit"
      >
        <a-form-item label="标签名称" field="name">
          <a-input v-model="formModel.name" placeholder="请输入标签名称" />
        </a-form-item>

        <a-form-item label="封面图" field="cover">
          <a-upload
            :custom-request="handleUploadChange"
            :show-file-list="false"
            accept="image/*"
            :limit="1"
            :max-size="2048"
            @exceed="handleExceed"
            @error="handleUploadError"
          >
            <template #upload-button>
              <div class="cover-upload">
                <img 
                  v-if="formModel.cover" 
                  :src="formModel.cover" 
                  alt="cover"
                  @error="handleImageError"
                />
                <icon-image v-else />
                <div class="upload-mask">
                  <icon-edit />
                </div>
              </div>
            </template>
          </a-upload>
        </a-form-item>

        <a-form-item label="简介" field="intro">
          <a-textarea
            v-model="formModel.intro"
            placeholder="请输入标签简介"
            :auto-size="{ minRows: 3 }"
          />
        </a-form-item>

        <a-form-item label="状态" field="status">
          <a-switch
            v-model="formModel.status"
            :checked-value="1"
            :unchecked-value="0"
          />
        </a-form-item>

        <a-form-item label="公众号" field="mps_id">
          <a-space>
            <a-input
              :model-value="(formModel.mps_id||[]).map(mp => mp.id.toString()).join(',')"
              placeholder="请选择公众号"
              readonly
              style="width: 300px"
            />
            <a-button @click="showMpSelector = true">选择</a-button>
          </a-space>
        </a-form-item>

        <a-form-item>
          <a-space>
            <a-button type="primary" html-type="submit" :loading="formLoading">
              提交
            </a-button>
            <a-button @click="router.go(-1)">取消</a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
  <!-- 公众号选择器模态框 -->
<a-modal
  v-model:visible="showMpSelector"
  title="选择公众号"
  :footer="false"
  width="800px"
>
  <MpMultiSelect 
    ref="mpSelectorRef"
    v-model="formModel.mps_id"
  />
  <template #footer>
    <a-button type="primary" @click="showMpSelector = false">确定</a-button>
  </template>
</a-modal>
</template>



<style scoped>
.tag-form {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.cover-upload {
  position: relative;
  width: 120px;
  height: 120px;
  cursor: pointer;
  border: 1px dashed var(--color-border-2);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.cover-upload img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.upload-mask {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
}

.cover-upload:hover .upload-mask {
  opacity: 1;
}
</style>