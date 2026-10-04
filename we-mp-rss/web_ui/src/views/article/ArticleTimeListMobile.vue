<template>
  <a-spin :loading="fullLoading" tip="正在刷新..." size="large">
    <a-layout class="article-list">
      <a-layout-content :style="{ padding: '20px', width: '100%', height: '100%', overflow: 'auto' }"
        @scroll="handleScroll">
        <a-page-header :title="activeFeed ? activeFeed.name : '全部'" :show-back="false">
          <template #extra>
            <a-space>
              <a-button type="primary" @click="showMpList">
                <template #icon><icon-eye /></template>
                阅读
              </a-button>
            </a-space>
          </template>
        </a-page-header>

        <a-card style="border:0">
          <div class="search-bar">
            <a-input-search v-model="searchText" placeholder="搜索文章标题" @search="handleSearch" @keyup.enter="handleSearch"
              allow-clear />
          </div>

          <div class="timeline">
            <div v-for="(item, index) in articles" :key="index" class="timeline-item">
              <!-- <div class="timeline-dot"></div> -->
              <div class="timeline-content">
                <div class="article-header">
                  <span class="time-badge">
                    <span class="time-part">{{ formatTime(item.created_at) }}</span>
                    <span class="date-part">{{ formatDate(item.created_at) }}</span>
                  </span>
                  <a-typography-text strong :heading="1"><strong>{{ item.title }}</strong></a-typography-text>
                </div>
                <a-typography-text strong :heading="2" @click="viewArticle(item)">{{ item.mp_name || '未知公众号'
                  }}</a-typography-text>
                <a-typography-text type="secondary"> {{ item.description }}</a-typography-text>
                <a-button type="text" @click="viewArticle(item)">
                  <template #icon><icon-eye /></template>
                  查看
                </a-button>
              </div>
            </div>
          </div>

          <div class="list-footer">
            <div v-if="loadingMore" class="loading-more">
              加载中...
            </div>
            <a-button v-else-if="hasMore" type="primary" @click="fetchArticles(true)" class="load-more-btn">
              加载更多
            </a-button>
            <div class="total-count">
              共 {{ pagination.total }} 条
            </div>
          </div>
        </a-card>
      </a-layout-content>
    </a-layout>
  </a-spin>

  <a-drawer v-model:visible="mpListVisible" title="选择公众号" @ok="handleMpSelect" @cancel="mpListVisible = false"
    placement="left" width="99%">
    <a-list :data="mpList" :loading="mpLoading" bordered>
      <template #item="{ item }">
        <a-list-item @click="handleMpClick(item.id)" :class="{ 'active-mp': activeMpId === item.id }">
          <img :src="Avatar(item.avatar)" width="40" style="float:left;margin-right:1rem;" />
          <a-typography-text style="line-height:40px;margin-left:1rem;" strong>{{ item.name || item.mp_name
            }}</a-typography-text>
        </a-list-item>
      </template>
    </a-list>
    <template #footer>
      <a-link href="/add-subscription" style="float:left;">
        <a-icon type="plus" />
        <span>添加订阅</span>
      </a-link>
      <a-button type="primary" @click="handleMpSelect">开始阅读</a-button>
    </template>
  </a-drawer>

  <a-drawer id="article-modal" v-model:visible="articleModalVisible" title="WeRss" placement="left" width="100vw"
    :footer="false" :fullscreen="false">
    <div style="padding: 20px; overflow-y: auto;clear:both;">
      <div>
        <h2>{{ currentArticle.title }}</h2>
      </div>
      <div style="margin-top: 20px; color: var(--color-text-3); text-align: left">
        <a-link :href="currentArticle.url" target="_blank">查看原文</a-link>
        更新时间 ：{{ currentArticle.time }}
      </div>
      <div v-html="currentArticle.content"></div>
      <div style="margin-top: 20px; color: var(--color-text-3); text-align: right">
        {{ currentArticle.time }}
      </div>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import dayjs from 'dayjs'
import { formatDateTime, formatTimestamp } from '@/utils/date'

const formatTime = (date: string | Date) => {
  return date ? dayjs(date).format('HH:mm') : ''
}

const formatDate = (date: string | Date) => {
  return date ? dayjs(date).format('MM/DD') : ''
}
import { Avatar } from '@/utils/constants'
import { ref, onMounted } from 'vue'
import { getArticles, getArticleDetail } from '@/api/article'
import { getSubscriptions } from '@/api/subscription'
import { Message } from '@arco-design/web-vue'
import { ProxyImage } from '@/utils/constants'
const articles = ref([])
const loading = ref(false)
const mpList = ref([])
const mpLoading = ref(false)
const activeMpId = ref('')
const searchText = ref('')
const mpListVisible = ref(false)

const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  showPageSize: true,
  pageSizeOptions: [10]
})

const activeFeed = ref({
  id: "",
  name: "全部",
})

const showMpList = () => {
  mpListVisible.value = true
}

const handleMpSelect = () => {
  mpListVisible.value = false
  fetchArticles()
}

const handleMpClick = (mpId: string) => {
  activeMpId.value = mpId
  activeFeed.value = mpList.value.find(item => item.id === activeMpId.value) || { id: "", name: "全部" }
}

const fetchArticles = async (isLoadMore = false) => {
  if (loading.value || (isLoadMore && !hasMore.value)) return;
  loading.value = true
  try {
    const res = await getArticles({
      page: isLoadMore ? pagination.value.current : 0,
      pageSize: pagination.value.pageSize,
      search: searchText.value,
      mp_id: activeMpId.value
    })

    if (isLoadMore) {
      articles.value = [...articles.value, ...(res.list || []).map(item => ({
        ...item,
        mp_name: item.mp_name || item.account_name || '未知公众号',
        url: item.url || "https://mp.weixin.qq.com/s/" + item.id
      }))]
    } else {
      articles.value = (res.list || []).map(item => ({
        ...item,
        mp_name: item.mp_name || item.account_name || '未知公众号',
        url: item.url || "https://mp.weixin.qq.com/s/" + item.id
      }))
    }

    pagination.value.total = res.total || 0
    hasMore.value = res.list && res.list.length >= pagination.value.pageSize
    if (isLoadMore) {
      pagination.value.current++
    }
  } catch (error) {
    console.error('获取文章列表错误:', error)
    Message.error(error)
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page: number, pageSize: number) => {
  pagination.value.current = page
  pagination.value.pageSize = pageSize
  fetchArticles()
}

const handleSearch = () => {
  pagination.value.current = 1
  fetchArticles()
}
const processedContent = (record: any) => {
  return ProxyImage(record.content)
}
const viewArticle = async (record: any) => {
  loading.value = true
  try {
    const article = await getArticleDetail(record.id)
    currentArticle.value = {
      title: article.title,
      content: processedContent(article),
      time: formatDateTime(article.created_at),
      url: article.url
    }
    articleModalVisible.value = true
  } catch (error) {
    console.error('获取文章详情错误:', error)
    Message.error(error)
  } finally {
    loading.value = false
  }
}

const currentArticle = ref({
  title: '',
  content: '',
  time: '',
  url: ''
})

const articleModalVisible = ref(false)

const fullLoading = ref(false)
const loadingMore = ref(false)
const hasMore = ref(true)

const handleScroll = (event: Event) => {
  const target = event.target as HTMLElement
  const { scrollTop, scrollHeight, clientHeight } = target
  if (scrollHeight - (scrollTop + clientHeight) < 100 && !loadingMore.value && hasMore.value) {
    loadingMore.value = true
    fetchArticles(true).finally(() => {
      loadingMore.value = false
    })
  }
}

const refresh = () => {
  fullLoading.value = true
  fetchArticles().finally(() => {
    fullLoading.value = false
  })
}

const clear_articles = () => {
  fullLoading.value = true
  fetchArticles().finally(() => {
    fullLoading.value = false
  })
}

const fetchMpList = async () => {
  mpLoading.value = true
  try {
    const res = await getSubscriptions({
      page: 0,
      pageSize: 100
    })

    mpList.value = res.list.map(item => ({
      id: item.id || item.mp_id,
      name: item.name || item.mp_name,
      avatar: item.avatar || item.mp_cover || '',
      mp_intro: item.mp_intro || item.mp_intro || ''
    }))
  } catch (error) {
    console.error('获取公众号列表错误:', error)
  } finally {
    mpLoading.value = false
  }
}

onMounted(() => {
  fetchMpList()
  fetchArticles()
})
</script>

<style scoped>
.article-list {
  height: 100%;
}

.search-bar {
  margin-bottom: 20px;
}

.active-mp {
  background-color: var(--color-primary-light-1);
}

.arco-drawer-body img {
  max-width: 100vw !important;
  margin: 0 auto !important;
  padding: 0 !important;
}

.timeline {
  position: relative;
  padding-left: 20px;
}

.timeline-item {
  position: relative;
  margin-bottom: 20px;
}

.article-header {
  position: relative;
}

.time-badge {
  position: absolute;
  left: -40px;
  top: -18px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  font-size: 11px;
  color: #fff;
  background-color: var(--primary-color);
  padding: 3px 8px;
  border-radius: 1px;
  transform: translateY(-50%);
  z-index: 1;
}

.time-part {
  font-size: 14px;
  font-weight: bold;
}

.date-part {
  font-size: 12px;
  opacity: 0.8;
}

.timeline-dot {
  position: absolute;
  left: -10px;
  top: 0;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: var(--primary-color);
}

.timeline-content {
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.timeline-content:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

a-button {
  margin-top: 8px;
}

.list-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 16px;
}

.loading-more {
  text-align: center;
  padding: 16px;
  color: var(--color-text-3);
}

.load-more-btn {
  margin: 16px 0;
}

.arco-typography {
  margin-right: 16px;
}

.total-count {
  color: var(--color-text-3);
  font-size: 14px;
  margin-bottom: 16px;
}

.arco-list-wrapper {
  width: 80vw;
}
</style>
<style>
#article-modal img {
  max-width: 100%;
}
</style>