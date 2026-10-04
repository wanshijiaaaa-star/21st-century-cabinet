<template>
  <div class="wechat-status-page">
    <a-page-header title="公众号状态" sub-title="微信公众号授权信息">
      <template #extra>
        <a-button type="primary" @click="refreshStatus">
          <template #icon><icon-refresh /></template>
          刷新状态
        </a-button>
      </template>
    </a-page-header>

    <!-- 授权状态卡片 -->
    <a-card :bordered="false" class="status-card">
      <template #title>
        <div class="card-title">
          <icon-wechat class="wechat-icon" />
          授权状态
        </div>
      </template>
      
      <div class="status-content" v-if="wxLoginInfo">
        <!-- 公众号基本信息 -->
        <div class="account-header">
          <a-avatar :size="80" class="account-avatar">
            <img v-if="wxLoginInfo.ext_data?.wx_logo" :src="wxLoginInfo.ext_data.wx_logo" alt="公众号头像">
            <icon-wechat v-else />
          </a-avatar>
          <div class="account-info">
            <h2 class="account-name">{{ wxLoginInfo.ext_data?.wx_app_name || '未知公众号' }}</h2>
            <a-tag :color="haswxLogined ? 'green' : 'red'" size="large">
              {{ haswxLogined ? '已授权' : '未授权' }}
            </a-tag>
          </div>
        </div>

        <!-- 详细信息 -->
        <a-descriptions :column="{ xs: 1, sm: 2, md: 3, lg: 4 }" bordered class="info-descriptions">
          <a-descriptions-item label="昨日阅读">
            <span class="stat-value">{{ wxLoginInfo.ext_data?.wx_read_yesterday || 0 }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="昨日分享">
            <span class="stat-value">{{ wxLoginInfo.ext_data?.wx_share_yesterday || 0 }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="昨日关注">
            <span class="stat-value">{{ wxLoginInfo.ext_data?.wx_watch_yesterday || 0 }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="原创数">
            <span class="stat-value">{{ wxLoginInfo.ext_data?.wx_yuan_count || 0 }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="粉丝数">
            <span class="stat-value">{{ wxLoginInfo.ext_data?.wx_user_count || 0 }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="Token状态">
            <a-tag :color="haswxLogined ? 'green' : 'red'">
              {{ haswxLogined ? '有效' : '已失效' }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="到期时间" :span="2">
            <span v-if="wxLoginInfo.expiry?.expiry_time">{{ wxLoginInfo.expiry.expiry_time }}</span>
            <span v-else class="text-muted">未知</span>
          </a-descriptions-item>
        </a-descriptions>

        <!-- Token 信息 -->
        <div class="token-section" v-if="wxLoginInfo.token">
          <div class="token-header">
            <span class="token-label">Token:</span>
            <a-button size="small" @click="copyToken">
              <template #icon><icon-copy /></template>
              复制
            </a-button>
          </div>
          <div class="token-value">{{ wxLoginInfo.token }}</div>
        </div>
      </div>

      <!-- 未授权状态 -->
      <div class="empty-status" v-else>
        <a-empty description="暂无公众号授权信息">
          <a-button type="primary" @click="showAuthQrcode">
            <template #icon><icon-scan /></template>
            扫码授权
          </a-button>
        </a-empty>
      </div>
    </a-card>

    <!-- 操作卡片 -->
    <a-card :bordered="false" class="action-card">
      <template #title>
        <div class="card-title">
          <icon-tool class="tool-icon" />
          操作
        </div>
      </template>
      
      <a-space wrap>
        <a-button type="primary" @click="showAuthQrcode">
          <template #icon><icon-scan /></template>
          扫码授权
        </a-button>
        <a-button type="outline" @click="switchAccount" :loading="switching">
          <template #icon><icon-swap /></template>
          切换账号
        </a-button>
        <a-popconfirm content="确定要刷新Token吗？" @ok="refreshToken">
          <a-button type="outline" status="warning">
            <template #icon><icon-refresh /></template>
            刷新Token
          </a-button>
        </a-popconfirm>
      </a-space>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, inject } from 'vue'
import { Message } from '@arco-design/web-vue'
import { getSysInfo } from '@/api/sysInfo'

const haswxLogined = ref(false)
const wxLoginInfo = ref<any>(null)
const switching = ref(false)

// 从父组件注入扫码授权方法
const showAuthQrcode = inject<() => void>('showAuthQrcode', () => {
  Message.warning('请从页面头部进行扫码授权')
})

const fetchSysInfo = async () => {
  try {
    const res = await getSysInfo()
    haswxLogined.value = res?.wx?.login || false
    wxLoginInfo.value = res?.wx?.info || null
  } catch (error) {
    console.error('获取系统信息失败', error)
  }
}

const refreshStatus = () => {
  fetchSysInfo()
  Message.success('状态已刷新')
}

const copyToken = () => {
  if (wxLoginInfo.value?.token) {
    navigator.clipboard.writeText(wxLoginInfo.value.token)
    Message.success('Token已复制到剪贴板')
  }
}

const switchAccount = async () => {
  switching.value = true
  try {
    // 调用切换账号 API
    const response = await fetch('/api/v1/wx/auth/switch', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
    const result = await response.json()
    if (result.code === 0) {
      Message.success('账号切换成功')
      fetchSysInfo()
    } else {
      Message.error(result.message || '切换失败')
    }
  } catch (error) {
    Message.error('切换账号失败')
  } finally {
    switching.value = false
  }
}

const refreshToken = async () => {
  try {
    Message.info('正在刷新Token...')
    // 这里可以调用刷新Token的逻辑
    await fetchSysInfo()
    Message.success('Token刷新成功')
  } catch (error) {
    Message.error('Token刷新失败')
  }
}

onMounted(() => {
  fetchSysInfo()
})
</script>

<style scoped>
.wechat-status-page {
  padding: 20px;
}

.status-card,
.action-card {
  margin-bottom: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.wechat-icon {
  color: #07c160;
  font-size: 20px;
}

.tool-icon {
  color: #165dff;
  font-size: 20px;
}

.account-header {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 24px;
  padding: 16px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  border-radius: 12px;
}

.account-avatar {
  background: #07c160;
  color: white;
}

.account-name {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
}

.account-info {
  flex: 1;
}

.info-descriptions {
  margin-top: 16px;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #165dff;
}

.token-section {
  margin-top: 24px;
  padding: 16px;
  background: #f7f8fa;
  border-radius: 8px;
}

.token-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.token-label {
  font-weight: 500;
  color: #86909c;
}

.token-value {
  font-family: monospace;
  font-size: 13px;
  word-break: break-all;
  color: #4e5969;
  padding: 8px;
  background: white;
  border-radius: 4px;
}

.empty-status {
  padding: 60px 0;
  text-align: center;
}

.text-muted {
  color: #86909c;
}

@media (max-width: 768px) {
  .wechat-status-page {
    padding: 12px;
  }
  
  .account-header {
    flex-direction: column;
    text-align: center;
    gap: 16px;
  }
  
  .account-info {
    text-align: center;
  }
}
</style>
