<template>
  <a-layout class="app-container">
    <!-- 头部 -->
    <a-layout-header class="app-header" v-if="route.path !== '/login'">
      <div class="header-left">
        <div class="logo">
          <img :src="logo" alt="avatar" :width="60" style="margin-right:1rem;">
          <router-link to="/">{{ appTitle }}</router-link>
          <a-tooltip v-if="hasLogined" :content="!haswxLogined ? '未授权，请扫码登录' : '点我扫码授权'" position="bottom" :default-popup="!haswxLogined">
            <icon-scan @click="showAuthQrcode()" :style="{ marginLeft: '10px', cursor: 'pointer', color: !haswxLogined ? '#f00' : '#000' }"/>
          </a-tooltip>
          <a-tooltip v-if="hasLogined" :content="!hasWereadLogined ? '微信读书未授权，请扫码' : '微信读书已授权，点我重新扫码'" position="bottom" :default-popup="!hasWereadLogined">
            <icon-book @click="showWereadAuthQrcode()" :style="{ marginLeft: '10px', cursor: 'pointer', color: !hasWereadLogined ? '#f00' : '#4e8cff' }"/>
          </a-tooltip>
        </div>
        <a-space>
            <a-select :defaultValue="currentLanguage" v-model:value="currentLanguage" @change="handleLanguageChange" >
              <a-option value="">禁用</a-option>
              <a-option value="chinese_simplified">简体中文</a-option>
              <a-option value="chinese_traditional">繁體中文</a-option>
              <a-option value="english" selected="selected">English</a-option>
              <a-option value="russian">Русский язык</a-option>
              <a-option value="corsican">hinaassicurasol</a-option>
              <a-option value="guarani">ondoho</a-option>
              <a-option value="kinyarwanda">Kinyarwanda</a-option>
              <a-option value="hausa">dictionary variant</a-option>
              <a-option value="norwegian">Norge</a-option>
              <a-option value="dutch">nederlands</a-option>
              <a-option value="yoruba">Yoruba</a-option>
              <a-option value="gongen">गोंगेन हें नांव</a-option>
              <a-option value="latin">Latina</a-option>
              <a-option value="nepali">नेपालीName</a-option>
              <a-option value="french">Français</a-option>
              <a-option value="czech">český</a-option>
              <a-option value="hawaiian">panekeʻhaka</a-option>
              <a-option value="georgian">ჯორჯიანიName</a-option>
             
              <a-option value="serbian">Српски</a-option>
              <a-option value="persian">Persian</a-option>
              <a-option value="bhojpuri">हमार कपार दर्द करता।</a-option>
              <a-option value="hindi">हिन्दी</a-option>
              <a-option value="belarusian">БеларускаяName</a-option>
              <a-option value="kazakh">қазақ</a-option>
              <a-option value="swahili">Kiswahili</a-option>
              <a-option value="icelandic">ÍslandName</a-option>
              <a-option value="yiddish">ייַדיש</a-option>
              <a-option value="twi">Ma frɛ</a-option>
              <a-option value="irish">Íris</a-option>
              <a-option value="gujarati">ગુજરાતી</a-option>
              <a-option value="khmer">ភាសា&ZeroWidthSpace;ខ្មែរName</a-option>
              <a-option value="slovak">Slovenská</a-option>
              <a-option value="hebrew">היברית</a-option>
              <a-option value="kannada">ಕನ್ನಡ್Name</a-option>
              <a-option value="hungarian">magyar</a-option>
              <a-option value="tamil">தாமில்</a-option>
              <a-option value="arabic">بالعربية</a-option>
              <a-option value="bengali">বেঙ্গালী</a-option>
              <a-option value="azerbaijani">azerbaijani</a-option>
              <a-option value="samoan">lifiava</a-option>
              <a-option value="afrikaans">afrikaans</a-option>
              <a-option value="indonesian">IndonesiaName</a-option>
              <a-option value="danish">dansk</a-option>
              <a-option value="shona">Shona</a-option>
              <a-option value="bambara">Bamanankan</a-option>
              <a-option value="lithuanian">Lietuva</a-option>
              <a-option value="vietnamese">Tiếng Việt</a-option>
              <a-option value="maltese">Malti</a-option>
              <a-option value="turkmen">Türkmençe</a-option>
              <a-option value="assamese">assamese</a-option>
              <a-option value="catalan">català</a-option>
              <a-option value="singapore">සිංගාපුර්</a-option>
              <a-option value="cebuano">cebuano</a-option>
              <a-option value="sanskrit">Sanskrit</a-option>
              <a-option value="polish">Polski</a-option>
              <a-option value="galician">galico</a-option>
              <a-option value="latvian">latviešu</a-option>
              <a-option value="ukrainian">Україна</a-option>
              <a-option value="tatar">Татар</a-option>
              <a-option value="scottish_gaelic">Gàidhlig na h-Alba</a-option>
              <a-option value="welsh">Iaith Weleg</a-option>
              <a-option value="japanese">日本語</a-option>
              <a-option value="filipino">Pilipino</a-option>
              <a-option value="aymara">aymara.</a-option>
              <a-option value="lao">ກະຣຸນາ</a-option>
              <a-option value="telugu">తెలుగుName</a-option>
              <a-option value="romanian">Română</a-option>
              <a-option value="haitian_creole">Kreyòl ayisyen</a-option>
              <a-option value="dogrid">कुकुरमुत्ता</a-option>
              <a-option value="swedish">Svenska</a-option>
              <a-option value="maithili">मरातिलीName</a-option>
              <a-option value="thai">คนไทย</a-option>
              <a-option value="armenian">Արմենյան</a-option>
              <a-option value="burmese">ဗာရမ်</a-option>
              <a-option value="pashto">پښتوName</a-option>
              <a-option value="hmong">hmong</a-option>
              <a-option value="dhivehi">ދިވާރީވް</a-option>
              <a-option value="luxembourgish">LëtzebuergeschName</a-option>
              <a-option value="sindhi">سنڌي</a-option>
              <a-option value="kurdish">Kurdî</a-option>
              <a-option value="turkish">Türkçe</a-option>
              <a-option value="macedonian">Македонски</a-option>
              <a-option value="bulgarian">български</a-option>
              <a-option value="malay">Malay</a-option>
              <a-option value="luganda">luganda</a-option>
              <a-option value="marathi">मराठीName</a-option>
              <a-option value="estonian">eesti keel</a-option>
              <a-option value="malayalam">മലമാലം</a-option>
              <a-option value="deutsch">Deutsch</a-option>
              <a-option value="slovene">slovenščina</a-option>
              <a-option value="urdu">اوردو</a-option>
              <a-option value="portuguese">português</a-option>
              <a-option value="igbo">igbo</a-option>
              <a-option value="kurdish_sorani">کوردی سۆرانی</a-option>
              <a-option value="oromo">adeta</a-option>
              <a-option value="greek">ελληνικά</a-option>
              <a-option value="spanish">Español</a-option>
              <a-option value="frisian">frysk</a-option>
              <a-option value="somali">Soomaali</a-option>
              <a-option value="amharic">amharic</a-option>
              <a-option value="nyanja">potakuyan</a-option>
              <a-option value="punjabi">ਪੰਜਾਬੀName</a-option>
              <a-option value="basque">baskoa</a-option>
              <a-option value="italian">italiano</a-option>
              <a-option value="albanian">albanian</a-option>
              <a-option value="korean">한국어</a-option>
              <a-option value="tajik">ТаjikӣName</a-option>
              <a-option value="finnish">suomi</a-option>
              <a-option value="kyrgyz">Кыргыз тили</a-option>
              <a-option value="ewe">Eʋegbe</a-option>
              <a-option value="croatian">hrvatski</a-option>
              <a-option value="creole">a n:n</a-option>
              <a-option value="quechua">Quechua</a-option>
              <a-option value="bosnian">bosnian</a-option>
              <a-option value="maori">Maori</a-option>
            </a-select>
        </a-space>
      </div>
      <div class="header-right" v-if="hasLogined">
        <a-link href="/views/home" target="_blank" style="margin-right: 20px;">Views</a-link>
        <a-link href="/api/docs" target="_blank" style="margin-right: 20px;">Docs</a-link>
        <a-link href="https://gitee.com/rachel_os/we-mp-rss" target="_blank" style="margin-right: 20px;">Gitee</a-link>
        <a-link href="https://github.com/rachelos/we-mp-rss" target="_blank" style="margin-right: 20px;">GitHub</a-link>
        <a-tooltip content="GitHub或者Google账户注册登录，获得首月5美元奖励。注册180+天的GitHub账户还可以解锁每月5美元的额度赠送。" position="bottom">
          <a-link href="https://console.run.claw.cloud/signin?link=FJ0VXS42W2P9" target="_blank"
            style="margin-right: 20px;">ClawCloud</a-link>
        </a-tooltip>
        <a-tooltip content="如果您需要部署此项目，建议采用腾讯云服务器，您懂得" position="bottom">
          <a-link
            href="https://cloud.tencent.com/act/cps/redirect?redirect=2446&cps_key=f8ce741e7b24cd68141ab2115122ea94&from=console"
            target="_blank" style="margin-right: 20px;">云部署</a-link>
        </a-tooltip>
        <a-tooltip content="您的支持是作者的最大动力，来一杯咖啡吧" position="bottom">
          <a-link @click="showSponsorModal" style="margin-right: 20px; cursor: pointer;" type="text">支持</a-link>
        </a-tooltip>
        <a-link href="https://www.paypal.com/ncp/payment/PUA72WYLAV5KW" target="_blank"
          style="margin-right: 20px;">赞助</a-link>



        <a-dropdown position="br" trigger="click">
          <div class="user-info">
            <a-avatar :size="36">
              <img v-if="userInfo.avatar" :src="userInfo.avatar" alt="avatar">
              <icon-user v-else />
            </a-avatar>
            <span class="username">{{ userInfo.username }}</span>
          </div>
          <template #content>
            <a-doption v-if="haswxLogined && wxLoginInfo?.ext_data" @click="showWxAccountInfo">
              <template #icon><icon-wechat /></template>
              公众号信息
            </a-doption>
            <a-doption @click="goToEditUser">
              <template #icon><icon-user /></template>
              个人中心
            </a-doption>
            <a-doption @click="goToChangePassword">
              <template #icon><icon-lock /></template>
              修改密码
            </a-doption>
            <a-doption @click="showAuthQrcode">
              <template #icon><icon-scan /></template>
              扫码授权
            </a-doption>
            <a-doption @click="showWereadAuthQrcode">
              <template #icon><icon-book /></template>
              微信读书授权
            </a-doption>
            <a-doption @click="handleLogout">
              <template #icon><icon-user /></template>
              退出登录
            </a-doption>
          </template>
        </a-dropdown>
        <!-- 公众号信息弹窗 -->
        <a-modal v-model:visible="wxAccountVisible" title="公众号信息" :footer="false" :width="400">
          <div class="wx-account-info" v-if="wxLoginInfo?.ext_data">
            <div class="wx-account-header">
              <a-avatar :size="64" class="wx-account-avatar">
                <img v-if="wxLoginInfo.ext_data.wx_logo" :src="wxLoginInfo.ext_data.wx_logo" alt="公众号头像">
                <icon-wechat v-else />
              </a-avatar>
              <div class="wx-account-name">{{ wxLoginInfo.ext_data.wx_app_name || '未知公众号' }}</div>
            </div>
            <a-descriptions :column="1" bordered size="small">
              <a-descriptions-item label="昨日阅读">
                {{ wxLoginInfo.ext_data.wx_read_yesterday || 0 }}
              </a-descriptions-item>
              <a-descriptions-item label="昨日分享">
                {{ wxLoginInfo.ext_data.wx_share_yesterday || 0 }}
              </a-descriptions-item>
              <a-descriptions-item label="Token状态">
                <a-tag :color="haswxLogined ? 'green' : 'red'">{{ haswxLogined ? '已授权' : '未授权' }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="Token" v-if="wxLoginInfo?.token">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span style="font-family: monospace; font-size: 12px; word-break: break-all;">{{ wxLoginInfo.token }}</span>
                  <a-button size="mini" @click="copyToken">
                    <template #icon><icon-copy /></template>
                  </a-button>
                </div>
              </a-descriptions-item>
              <a-descriptions-item label="到期时间" v-if="wxLoginInfo?.expiry?.expiry_time">
                {{ wxLoginInfo.expiry.expiry_time }}
              </a-descriptions-item>
            </a-descriptions>
          </div>
          <div v-else class="wx-account-empty">
            <a-empty description="暂无公众号信息" />
          </div>
        </a-modal>
        <WechatAuthQrcode ref="qrcodeRef" @success="handleQrAuthSuccess" />
        <WereadAuthQrcode ref="wereadQrcodeRef" @success="handleWereadQrAuthSuccess" />
        <a-modal v-model:visible="sponsorVisible" title="感谢支持" :footer="false" :style="{ zIndex: 1000 }" unmount-on-close>
          <div style="text-align: center;">
            <p>如果您觉得这个项目对您有帮助,请给Rachel来一杯Coffee吧~ </p>
            <img src="@/assets/images/sponsor.jpg" alt="赞赏码" style="max-width: 300px; margin-top: 20px;">
            <p>您打赏的金额将用于维护项目的运行成本，感谢您的支持！</p>
            <p>打赏后可以发送单号到<a href="mailto:rachelos@qq.com">rachelos@qq.com</a></p>
          </div>
        </a-modal>
      </div>
    </a-layout-header>

    <a-layout>

      <!-- 主内容区 -->
      <a-layout>
        <a-layout-content class="app-content">
          <router-view />
        </a-layout-content>
      </a-layout>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import translate from 'i18n-jsautotranslate'
import { ref,watchEffect, computed, onMounted, watch, provide } from 'vue'
import { Modal } from '@arco-design/web-vue/es/modal'
import {getSysInfo} from '@/api/sysInfo'
const currentLanguage = ref(localStorage.getItem('language') || 'chinese_simplified');


const handleLanguageChange = (language: string) => {
  setCurrentLanguage(language);
  currentLanguage.value = language;
};
const sponsorCount:number = parseInt(localStorage.getItem('sponsor'))|| 0
localStorage.setItem('sponsor', (sponsorCount+1).toString())
const sponsorVisible = ref(sponsorCount<3)
const showSponsorModal = (e: Event) => {
  e.preventDefault()
  sponsorVisible.value = true
  localStorage.setItem('sponsor',"0")
  console.log('Sponsor modal triggered') // 添加调试日志
}
import { 
  initBrowserNotification 
} from '@/utils/browserNotification'
import { useRouter, useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { getCurrentUser } from '@/api/auth'
import { logout } from '@/api/auth'
import { getWereadStatus } from '@/api/weread'
import WechatAuthQrcode from '@/components/WechatAuthQrcode.vue'
import WereadAuthQrcode from '@/components/WereadAuthQrcode.vue'

const qrcodeRef = ref()
const showAuthQrcode = () => {
  qrcodeRef.value?.startAuth()
}

const handleQrAuthSuccess = () => {
  haswxLogined.value = true
  Message.success('微信授权成功')
}
provide('showAuthQrcode', showAuthQrcode)

const wereadQrcodeRef = ref()
const showWereadAuthQrcode = () => {
  wereadQrcodeRef.value?.startAuth()
}

const handleWereadQrAuthSuccess = (result: any) => {
  // 只更新微信读书通道状态，不影响公众号通道的 haswxLogined
  hasWereadLogined.value = true
  Message.success(`微信读书授权成功，用户 VID: ${result?.vid || ''}`)
}
provide('showWereadAuthQrcode', showWereadAuthQrcode)

// 微信读书通道独立授权状态（与公众号 haswxLogined 完全区分）
const hasWereadLogined = ref(false)
const fetchWereadStatus = async () => {
  try {
    const res = await getWereadStatus() as any
    hasWereadLogined.value = !!res?.configured
  } catch (error) {
    console.error('获取微信读书状态失败', error)
  }
}
// 提供给子页面（如微信读书管理页）在扫码成功后刷新顶栏授权状态
provide('refreshWereadStatus', fetchWereadStatus)
const appTitle = computed(() => import.meta.env.VITE_APP_TITLE || '微信公众号订阅助手')
const logo = ref("/static/logo.svg")
const router = useRouter()
const route = useRoute()
const collapsed = ref(false)
const userInfo = ref({
  username: '',
  avatar: ''
})
const haswxLogined = ref(true)
const hasLogined = ref(false)
const wxLoginInfo = ref<any>(null)
const wxAccountVisible = ref(false)
const isAuthenticated = computed(() => {
  hasLogined.value = !!localStorage.getItem('token')
  return hasLogined.value
})

const fetchUserInfo = async () => {
  try {
    const res = await getCurrentUser()
    userInfo.value = res
  } catch (error) {
    console.error('获取用户信息失败', error)
  }
}

const fetchSysInfo = async () => {
  try {
    const res = await getSysInfo()
    haswxLogined.value = res?.wx?.login||false
    wxLoginInfo.value = res?.wx?.info||null
  } catch (error) {
    console.error('获取系统信息失败', error)
  }
}

const showWxAccountInfo = () => {
  wxAccountVisible.value = true
}

const copyToken = () => {
  if (wxLoginInfo.value?.token) {
    navigator.clipboard.writeText(wxLoginInfo.value.token)
    Message.success('Token已复制到剪贴板')
  }
}

const handleCollapse = (val: boolean) => {
  collapsed.value = val
}

const handleMenuClick = (key: string) => {
  router.push({ name: key })
}

const goToEditUser = () => {
  router.push({ name: 'EditUser' })
}

const goToChangePassword = () => {
  router.push({ name: 'ChangePassword' })
}

const handleLogout = async () => {
  try {
    await logout()
    localStorage.removeItem('token')
    router.push('/login')
  } catch (error) {
    Message.error('退出登录失败')
  }
}

onMounted(() => {
 
  if (isAuthenticated.value) {
    fetchUserInfo()
  }
  initBrowserNotification()
  translatePage();
  fetchSysInfo();
  fetchWereadStatus();
})
import { translatePage, setCurrentLanguage } from '@/utils/translate';

watch(
  () => route.path,
  () => {
    hasLogined.value = !!localStorage.getItem('token')
    if (hasLogined.value) {
      fetchUserInfo()
    }
  }
)
</script>

<style scoped>
.app-container {
  min-height: 100vh;
}


.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 64px;
  background: var(--color-bg-2);
  border-bottom: 1px solid var(--color-border);
}

.header-left {
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  font-size: 18px;
  font-weight: 500;
}

.logo svg {
  margin-right: 10px;
  font-size: 24px;
  color: var(--primary-color);
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.username {
  margin-left: 10px;
}

.app-content {
  /* padding: 20px; */
  background: var(--color-bg-1);
  min-height: calc(100vh - 64px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 720px) {
  .app-header .header-right {
    display: none !important;
  }
}

.wx-account-info {
  padding: 16px 0;
}

.wx-account-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 20px;
}

.wx-account-name {
  margin-top: 12px;
  font-size: 18px;
  font-weight: 500;
}

.wx-account-empty {
  padding: 40px 0;
}
</style>