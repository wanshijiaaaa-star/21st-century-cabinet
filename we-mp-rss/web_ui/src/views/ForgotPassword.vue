<template>
  <div class="forgot-container">
    <div class="forgot-layout">
      <!-- 左侧介绍区域 -->
      <div class="forgot-left">
        <div class="forgot-intro">
          <h1 class="intro-title">{{ appTitle }}</h1>
          <p class="intro-text">
            一个用于订阅和管理微信公众号内容的工具，提供RSS订阅功能
          </p>
        </div>
      </div>

      <!-- 右侧表单区域 -->
      <div class="forgot-right">
        <a-card class="forgot-card" :bordered="false">
          <div class="forgot-header">
            <h2>找回密码</h2>
            <p>验证码将通过系统通知发送，请联系管理员获取</p>
          </div>

          <!-- 步骤指示器 -->
          <a-steps :current="currentStep" class="steps">
            <a-step title="输入用户名" />
            <a-step title="验证身份" />
            <a-step title="重置密码" />
          </a-steps>

          <!-- 步骤1: 输入用户名 -->
          <div v-if="currentStep === 1" class="step-content">
            <a-form :model="form" layout="vertical">
              <a-form-item field="username" label="用户名">
                <a-input v-model="form.username" placeholder="请输入用户名">
                  <template #prefix><icon-user /></template>
                </a-input>
              </a-form-item>

              <a-form-item>
                <a-button type="primary" :loading="loading" long @click="handleRequestCode">
                  发送验证码
                </a-button>
              </a-form-item>
            </a-form>
          </div>

          <!-- 步骤2: 输入验证码和新密码 -->
          <div v-if="currentStep === 2" class="step-content">
            <a-form :model="form" layout="vertical">
              <a-form-item field="code" label="验证码">
                <a-input v-model="form.code" placeholder="请输入6位验证码" :max-length="6">
                  <template #prefix><icon-safe /></template>
                </a-input>
              </a-form-item>

              <a-form-item field="new_password" label="新密码">
                <a-input-password v-model="form.new_password" placeholder="请输入新密码（至少6位）">
                  <template #prefix><icon-lock /></template>
                </a-input-password>
              </a-form-item>

              <a-form-item field="confirm_password" label="确认密码">
                <a-input-password v-model="form.confirm_password" placeholder="请再次输入新密码">
                  <template #prefix><icon-lock /></template>
                </a-input-password>
              </a-form-item>

              <a-form-item>
                <a-space direction="vertical" fill>
                  <a-button type="primary" :loading="loading" long @click="handleResetPassword">
                    重置密码
                  </a-button>
                  <a-button long @click="currentStep = 1">
                    返回上一步
                  </a-button>
                </a-space>
              </a-form-item>
            </a-form>
          </div>

          <!-- 步骤3: 完成 -->
          <div v-if="currentStep === 3" class="step-content success-content">
            <icon-check-circle-fill class="success-icon" />
            <h3>密码重置成功</h3>
            <p>请使用新密码登录</p>
            <a-button type="primary" @click="goToLogin">
              返回登录
            </a-button>
          </div>

          <div class="back-to-login">
            <a-link @click="goToLogin">
              <icon-left /> 返回登录
            </a-link>
          </div>
        </a-card>
      </div>
    </div>

    <div class="forgot-footer">
      <div class="copyright">Design By Rachel</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { requestResetCode, resetPassword } from '@/api/auth'

const appTitle = computed(() => import.meta.env.VITE_APP_TITLE || '微信公众号订阅助手')

const router = useRouter()
const loading = ref(false)
const currentStep = ref(1)

const form = ref({
  username: '',
  code: '',
  new_password: '',
  confirm_password: ''
})

const handleRequestCode = async () => {
  if (!form.value.username) {
    Message.warning('请输入用户名')
    return
  }

  loading.value = true
  try {
    await requestResetCode({ username: form.value.username })
    Message.success('验证码已发送，请联系管理员获取')
    currentStep.value = 2
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail?.message ||
      error.response?.data?.message ||
      error.message ||
      '发送验证码失败'
    Message.error(errorMsg)
  } finally {
    loading.value = false
  }
}

const handleResetPassword = async () => {
  if (!form.value.code) {
    Message.warning('请输入验证码')
    return
  }
  if (form.value.code.length !== 6) {
    Message.warning('验证码应为6位数字')
    return
  }
  if (!form.value.new_password) {
    Message.warning('请输入新密码')
    return
  }
  if (form.value.new_password.length < 6) {
    Message.warning('密码长度不能少于6位')
    return
  }
  if (form.value.new_password !== form.value.confirm_password) {
    Message.warning('两次输入的密码不一致')
    return
  }

  loading.value = true
  try {
    await resetPassword({
      username: form.value.username,
      code: form.value.code,
      new_password: form.value.new_password
    })
    Message.success('密码重置成功')
    currentStep.value = 3
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail?.message ||
      error.response?.data?.message ||
      error.message ||
      '密码重置失败'
    Message.error(errorMsg)
  } finally {
    loading.value = false
  }
}

const goToLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
.forgot-container {
  height: 100vh;
  padding: 0;
  margin: 0;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.95) 0%, rgba(168, 85, 247, 0.9) 100%);
  background-size: 200% 200%;
  animation: gradientBG 12s ease infinite;
}

@keyframes gradientBG {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.forgot-layout {
  display: flex;
  height: 100%;
}

.forgot-left {
  flex: 0 0 55%;
  padding: 80px;
  color: #ffffff;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.forgot-intro {
  max-width: 600px;
}

.intro-title {
  font-size: 2.5rem;
  margin-bottom: 24px;
  font-weight: 600;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.intro-text {
  font-size: 1.1rem;
  line-height: 1.6;
  opacity: 0.9;
}

.forgot-right {
  flex: 0 0 45%;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(5px);
}

.forgot-card {
  width: 450px;
  padding: 40px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

.forgot-header {
  text-align: center;
  margin-bottom: 24px;
}

.forgot-header h2 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1a202c;
}

.forgot-header p {
  font-size: 14px;
  color: #718096;
}

.steps {
  margin-bottom: 32px;
}

.step-content {
  margin-top: 24px;
}

.success-content {
  text-align: center;
  padding: 20px 0;
}

.success-icon {
  font-size: 64px;
  color: #52c41a;
  margin-bottom: 16px;
}

.success-content h3 {
  font-size: 20px;
  color: #1a202c;
  margin-bottom: 8px;
}

.success-content p {
  color: #718096;
  margin-bottom: 24px;
}

.back-to-login {
  text-align: center;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

:deep(.arco-form-item-label) {
  color: #333 !important;
}

:deep(.arco-input-wrapper) {
  height: 44px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

:deep(.arco-input-wrapper:hover),
:deep(.arco-input-wrapper:focus-within) {
  border-color: #4299e1;
  background: #fff;
}

:deep(.arco-btn-primary) {
  height: 44px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 15px;
  background: #4299e1;
  border-color: #4299e1;
}

:deep(.arco-btn-primary:hover) {
  background: #3182ce;
  border-color: #3182ce;
}

.forgot-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  text-align: center;
  padding: 24px 0;
  color: #fff;
  font-size: 14px;
}

@media (max-width: 992px) {
  .forgot-layout {
    flex-direction: column;
  }

  .forgot-left,
  .forgot-right {
    flex: 1;
    padding: 40px;
  }

  .forgot-card {
    width: 100%;
    max-width: 450px;
  }

  .intro-title {
    font-size: 2rem;
  }
}

@media (max-width: 720px) {
  .forgot-left {
    display: none;
  }

  .forgot-right {
    width: 100%;
    flex: none;
  }

  .forgot-card {
    width: 100%;
    padding: 24px;
  }
}
</style>
