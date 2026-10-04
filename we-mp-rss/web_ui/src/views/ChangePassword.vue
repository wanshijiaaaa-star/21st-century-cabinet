<template>
  <div class="change-password">
    <a-page-header
      title="修改密码"
      subtitle="定期修改密码有助于账户安全"
      :show-back="true"
      @back="goBack"
    />
    
    <a-card>
      <a-form
        :model="form"
        :rules="rules"
        @submit="handleSubmit"
        layout="vertical"
      >
        <a-form-item label="当前密码" field="currentPassword">
          <a-input-password 
            v-model="form.currentPassword" 
            placeholder="请输入当前密码"
            allow-clear
          >
            <template #prefix><icon-lock /></template>
          </a-input-password>
        </a-form-item>
        
        <a-form-item label="新密码" field="newPassword">
          <a-input-password 
            v-model="form.newPassword" 
            placeholder="请输入新密码"
            allow-clear
          >
            <template #prefix><icon-lock /></template>
          </a-input-password>
        </a-form-item>
        
        <a-form-item label="确认新密码" field="confirmPassword">
          <a-input-password 
            v-model="form.confirmPassword" 
            placeholder="请再次输入新密码"
            allow-clear
          >
            <template #prefix><icon-lock /></template>
          </a-input-password>
        </a-form-item>
        
        <a-form-item>
          <a-space>
            <a-button type="primary" html-type="submit" :loading="loading">
              确认修改
            </a-button>
            <a-button @click="resetForm">重置</a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { changePassword } from '@/api/user'

const router = useRouter()
const loading = ref(false)

const form = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const validatePassword = (value: string, callback: any) => {
  if (!value) {
    callback('请输入密码')
    return
  }
  
  if (value.length < 8) {
    callback('密码长度不能少于8位')
    return
  }
  
  if (value.length > 20) {
    callback('密码长度不能超过20位')
    return
  }
  
  
  if (!/[a-z]/.test(value)) {
    callback('必须包含至少一个小写字母')
    return
  }
  
  if (!/[0-9]/.test(value)) {
    callback('必须包含至少一个数字')
    return
  }
  
  if (!/[^A-Za-z0-9]/.test(value)) {
    callback('必须包含至少一个特殊字符')
    return
  }
  
  callback()
}

const validateConfirmPassword = (value: string, callback: any) => {
  if (!value) {
    callback('请确认密码')
  } else if (value !== form.value.newPassword) {
    callback('两次输入的密码不一致')
  } else {
    callback()
  }
}

const rules = {
  currentPassword: [{ validator: validatePassword, trigger: 'blur' }],
  newPassword: [{ validator: validatePassword, trigger: 'blur' }],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }]
}

const handleSubmit = async () => {
  if (form.value.newPassword !== form.value.confirmPassword) {
    Message.error('新密码与确认密码不一致')
    return
  }
  loading.value = true
  try {
    const response = await changePassword({
      old_password: form.value.currentPassword,
      new_password: form.value.newPassword
    })
    console.log(response)
    if (response.code === 0) {
      Message.success('密码修改成功')
      // 清除token强制重新登录
      localStorage.removeItem('token')
      setTimeout(() => {
        router.push('/login')
      }, 1500)
    } else {
      Message.warning(`密码修改失败: ${response.data.message}`)
    }
    
  } catch (error) {
    
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.value = {
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  }
}

const goBack = () => {
  router.go(-1)
}
</script>

<style scoped>
.change-password {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.arco-form-item {
  margin-bottom: 20px;
}
</style>