<template>
  <a-spin :loading="fullLoading" tip="正在刷新..." size="large">
    <a-layout class="article-list">
      <a-layout-content :style="{ padding: '20px', width: '100%', height: '100%', overflow: 'auto' }" @scroll="handleScroll">
        <a-page-header 
          :title="activeFeed ? activeFeed.name : '全部'" 
           :show-back="false">
          <template #extra>
            <a-space>
              <a-button type="primary" @click="showMpList">
                <template #icon><icon-eye /></template>
                阅读
              </a-button>
            </a-space>
          </template>
        </a-page-header>

        <a-card style="border:0; width: 100%;">
          <div class="search-bar">
            <a-input-search v-model="searchText" placeholder="搜索文章标题" @search="handleSearch" @keyup.enter="handleSearch" allow-clear />
          </div>

          <a-list :data="articles" :loading="loading" bordered style="width: 100%;">
            <template #empty>
              <a-empty description="暂无文章" />
            </template>
            <template #item="{ item }">
              <a-list-item>
                <a-list-item-meta>
                  <template #title>
                    <div class="article-title-container">
                      <div
                        @click="toggleReadStatus(item)"
                        class="read-status-icon"
                        :class="{ 'read': item.is_read === 1 }"
                      >
                        <icon-check v-if="item.is_read === 1" />
                        <icon-close v-else />
                      </div>
                      <div
                        @click="toggleFavoriteStatus(item)"
                        class="favorite-icon"
                        :class="{ 'favorited': item.is_favorite === 1 }"
                      >
                        <icon-star-fill v-if="item.is_favorite === 1" />
                        <icon-star v-else />
                      </div>
                      <a-typography-text
                        strong
                        :heading="1"
                        :class="{ 'article-title-read': item.is_read === 1 }"
                      >
                        <strong>{{ item.title }}</strong>
                      </a-typography-text>
                    </div>
                  </template>
                  <template #description>
                    <a-typography-text
                      strong
                      :heading="2"
                      style="color: rgb(var(--primary-6)); cursor: pointer"
                      @click.stop="handleMpClick(item.mp_id)"
                    >{{ item.mp_name || '未知公众号' }}</a-typography-text>
                    <a-typography-text type="secondary"> {{ item.description }}</a-typography-text>
                    <a-typography-text type="secondary" strong> {{ formatDateTime(item.created_at) }}</a-typography-text>
                  </template>
                </a-list-item-meta>
                <a-button type="text" @click="viewArticle(item)">
                  <template #icon><icon-eye /></template>
                  查看
                </a-button>
              </a-list-item>
            </template>
          </a-list>

          <div class="list-footer">
  <div v-if="loadingMore" class="loading-more">
    加载中...
  </div>
  <a-button 
    v-else-if="hasMore" 
    type="primary" 
    @click="fetchArticles(true)"
    class="load-more-btn"
  >
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

  <a-drawer v-model:visible="mpListVisible" title="选择公众号" @ok="handleMpSelect" @cancel="mpListVisible = false" placement="left" width="99%">
    <div style="margin-bottom: 12px; padding: 0 8px;">
      <a-input-search v-model="mpSearchText" placeholder="搜索公众号" @search="handleMpSearch" @keyup.enter="handleMpSearch" allow-clear style="margin-bottom: 8px;" />
      <a-radio-group v-model="mpFilterType" type="button" size="small" style="width: 100%;">
        <a-radio value="all" style="flex: 1; text-align: center;">全部</a-radio>
        <a-radio value="active" style="flex: 1; text-align: center;">启用</a-radio>
        <a-radio value="disabled" style="flex: 1; text-align: center;">停用</a-radio>
      </a-radio-group>
    </div>
    <div class="mp-list-container" @scroll="handleMpScroll">
      <a-list :data="mpList" :loading="mpLoading && !mpLoadingMore" bordered>
        <template #item="{ item }">
          <a-list-item @click="handleMpClick(item.id)" :class="{ 'active-mp': activeMpId === item.id }"
            style="display: flex; align-items: center; justify-content: flex-start; text-align: left;">
            <div style="display: flex; align-items: center; flex: 1;">
              <img :src="Avatar(item.avatar)" width="40" style="float:left;margin-right:1rem;"/>
              <a-typography-text style="line-height:40px;margin-left:1rem;" strong :style="{ opacity: item.status === 0 ? 0.5 : 1 }">
                {{ item.name || item.mp_name }}
              </a-typography-text>
            </div>
            <a-space v-if="activeMpId === item.id && item.id != ''">
              <a-button size="mini" type="text" @click="$event.stopPropagation(); copyMpId(item.id)">
                <template #icon><icon-copy /></template>
              </a-button>
              <a-button size="mini" type="text" @click="$event.stopPropagation(); toggleMpStatus(item.id, item.status === 1 ? 0 : 1)">
                <template #icon>
                  <icon-stop v-if="item.status === 1" />
                  <icon-play-arrow v-else />
                </template>
              </a-button>
            </a-space>
          </a-list-item>
        </template>
      </a-list>
      <div v-if="mpLoadingMore" class="mp-loading-more">加载中...</div>
      <div v-else-if="!mpHasMore && mpList.length > 0" class="mp-no-more">没有更多了</div>
    </div>
      <template #footer>
        <a-link href="/add-subscription"  style="float:left;">
          <a-icon type="plus" />
          <span>添加订阅</span>
        </a-link>
        <a-button type="primary" @click="handleMpSelect">开始阅读</a-button>
      </template>
  </a-drawer>

  <a-drawer id="article-modal"
    v-model:visible="articleModalVisible" 
    title="WeRss"
    placement="left"
    width="100vw"
    :footer="false"
    :fullscreen="false"
  >
    <div style="padding: 20px; overflow-y: auto;clear:both;">
      <div style="display: flex; align-items: center; gap: 12px;">
        <h2 id="topreader" style="flex: 1; margin: 0;">{{currentArticle.title}}</h2>
        <div
          @click="toggleDetailFavorite"
          class="favorite-icon"
          :class="{ 'favorited': currentArticle.is_favorite === 1 }"
          style="font-size: 24px;"
        >
          <icon-star-fill v-if="currentArticle.is_favorite === 1" />
          <icon-star v-else />
        </div>
      </div>
        <div style="margin-top: 20px; color: var(--color-text-3); text-align: left;position:fixed;left:40%;top:-3px;">
        <a-link @click="viewArticle(currentArticle,-1)" target="_blank">上一篇 </a-link>
        <a-space/>
        <a-link @click="viewArticle(currentArticle,1)" target="_blank">下一篇 </a-link>
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
import { formatDateTime,formatTimestamp } from '@/utils/date'
import { Avatar } from '@/utils/constants'
import { ref, onMounted, computed, watch } from 'vue'
import { IconCheck, IconClose, IconStop, IconPlayArrow, IconCopy, IconStar, IconStarFill } from '@arco-design/web-vue/es/icon'
import { getArticles, getArticleDetail,getPrevArticle,getNextArticle,toggleArticleReadStatus,toggleArticleFavoriteStatus } from '@/api/article'
import { getSubscriptions, toggleMpStatus as toggleMpStatusApi } from '@/api/subscription'
import { Message } from '@arco-design/web-vue'
import { ProxyImage } from '@/utils/constants'
const articles = ref([])
const loading = ref(false)
const mpList = ref([])
const mpLoading = ref(false)
const activeMpId = ref('')
const searchText = ref('')
const mpListVisible = ref(false)
const mpFilterType = ref('all') // 'active' | 'disabled' | 'all'
const mpSearchText = ref('')

// 公众号列表分页状态
const mpPagination = ref({
  current: 1,
  pageSize: 20,
  total: 0
})
const mpHasMore = ref(true)
const mpLoadingMore = ref(false)

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
  pagination.value.current = 1
  articles.value = []
  fetchArticles()
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
const viewArticle = async (record: any,action_type: number) => {
  loading.value = true
  try {
    // console.log(record)
    const article = await getArticleDetail(record.id,action_type)
    currentArticle.value = {
      id: article.id,
      title: article.title,
      content: processedContent(article),
      time: formatDateTime(article.created_at),
      url: article.url,
      is_favorite: article.is_favorite ?? record.is_favorite ?? 0,
      is_read: article.is_read ?? record.is_read ?? 0
    }
    articleModalVisible.value = true
    window.location="#topreader"
    
    // 自动标记为已读（仅在查看当前文章时，不是上一篇/下一篇）
    if (action_type === 0 && record.is_read !== 1) {
      await toggleReadStatus(record)
    }
  } catch (error) {
    console.error('获取文章详情错误:', error)
    Message.error(error)
  } finally {
    loading.value = false
  }
}

const currentArticle = ref({
  id: '',
  title: '',
  content: '',
  time: '',
  url: '',
  is_favorite: 0,
  is_read: 0
})

const articleModalVisible = ref(false)

const fullLoading = ref(false)
const loadingMore = ref(false)
const hasMore = ref(true)

// 监听筛选类型变化，重新请求公众号列表
watch(mpFilterType, () => {
  mpPagination.value.current = 1
  mpList.value = []
  mpHasMore.value = true
  fetchMpList()
})

// 公众号搜索
const handleMpSearch = () => {
  mpPagination.value.current = 1
  mpList.value = []
  mpHasMore.value = true
  fetchMpList()
}

// 公众号列表滚动加载更多
const handleMpScroll = (event: Event) => {
  const target = event.target as HTMLElement
  const { scrollTop, scrollHeight, clientHeight } = target
  if (scrollHeight - (scrollTop + clientHeight) < 100 && !mpLoadingMore.value && mpHasMore.value) {
    mpLoadingMore.value = true
    fetchMpList(true).finally(() => {
      mpLoadingMore.value = false
    })
  }
}

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

const fetchMpList = async (isLoadMore = false) => {
  if (mpLoading.value || (isLoadMore && !mpHasMore.value)) return
  mpLoading.value = true
  try {
    // 根据筛选类型确定 status 参数
    let statusParam: number | undefined = undefined
    if (mpFilterType.value === 'active') {
      statusParam = 1
    } else if (mpFilterType.value === 'disabled') {
      statusParam = 0
    }
    // 'all' 时不传 status 参数

    // 选择"全部"时，第一页请求少2条（因为会添加"全部"选项，后端也会添加"精选文章"）
    const isFirstPage = mpPagination.value.current === 1
    const adjustedPageSize = mpFilterType.value === 'all' && isFirstPage
      ? mpPagination.value.pageSize - 2
      : mpPagination.value.pageSize

    const res = await getSubscriptions({
      page: mpPagination.value.current - 1,
      pageSize: adjustedPageSize,
      status: statusParam,
      kw: mpSearchText.value
    })

    const newItems = res.list.map(item => ({
      id: item.id || item.mp_id,
      name: item.name || item.mp_name,
      avatar: item.avatar || item.mp_cover || '',
      mp_intro: item.mp_intro || item.mp_intro || '',
      status: item.status ?? 1
    }))

    if (isLoadMore) {
      mpList.value = [...mpList.value, ...newItems]
    } else {
      mpList.value = newItems
      // 只在筛选全部且无搜索时添加'全部'选项
      if (mpFilterType.value === 'all' && !mpSearchText.value) {
        mpList.value.unshift({
          id: '',
          name: '全部',
          avatar: '/static/logo.svg',
          mp_intro: '显示所有公众号文章',
          status: 1
        })
      }
    }

    mpPagination.value.total = res.total || 0
    mpHasMore.value = newItems.length >= adjustedPageSize
    if (mpHasMore.value) {
      mpPagination.value.current++
    }
  } catch (error) {
    console.error('获取公众号列表错误:', error)
  } finally {
    mpLoading.value = false
  }
}

// 切换文章阅读状态
const toggleReadStatus = async (record: any) => {
  try {
    const newReadStatus = record.is_read === 1 ? false : true;
    await toggleArticleReadStatus(record.id, newReadStatus);

    // 更新本地数据
    const index = articles.value.findIndex(item => item.id === record.id);
    if (index !== -1) {
      articles.value[index].is_read = newReadStatus ? 1 : 0;
    }

    Message.success(`文章已标记为${newReadStatus ? '已读' : '未读'}`);
  } catch (error) {
    console.error('更新阅读状态失败:', error);
    Message.error('更新阅读状态失败');
  }
};

// 切换文章收藏状态
const toggleFavoriteStatus = async (record: any) => {
  try {
    const newFavoriteStatus = record.is_favorite === 1 ? false : true;
    await toggleArticleFavoriteStatus(record.id, newFavoriteStatus);

    // 更新本地数据
    const index = articles.value.findIndex(item => item.id === record.id);
    if (index !== -1) {
      articles.value[index].is_favorite = newFavoriteStatus ? 1 : 0;
    }

    Message.success(`文章已${newFavoriteStatus ? '收藏' : '取消收藏'}`);
  } catch (error) {
    console.error('更新收藏状态失败:', error);
    Message.error('更新收藏状态失败');
  }
};

// 在详情弹窗中切换收藏状态
const toggleDetailFavorite = async () => {
  try {
    const newFavoriteStatus = currentArticle.value.is_favorite === 1 ? false : true;
    await toggleArticleFavoriteStatus(currentArticle.value.id, newFavoriteStatus);

    // 更新详情弹窗中的状态
    currentArticle.value.is_favorite = newFavoriteStatus ? 1 : 0;

    // 同步更新列表中的状态
    const index = articles.value.findIndex(item => item.id === currentArticle.value.id);
    if (index !== -1) {
      articles.value[index].is_favorite = newFavoriteStatus ? 1 : 0;
    }

    Message.success(`文章已${newFavoriteStatus ? '收藏' : '取消收藏'}`);
  } catch (error) {
    console.error('更新收藏状态失败:', error);
    Message.error('更新收藏状态失败');
  }
};

// 切换公众号状态
const toggleMpStatus = async (mpId: string, newStatus: number) => {
  try {
    await toggleMpStatusApi(mpId, newStatus);
    Message.success(newStatus === 0 ? '公众号已禁用' : '公众号已启用');
    // 更新本地数据
    const index = mpList.value.findIndex(item => item.id === mpId);
    if (index !== -1) {
      mpList.value[index].status = newStatus;
    }
  } catch (error) {
    console.error('更新公众号状态失败:', error);
    Message.error('更新公众号状态失败');
  }
}

// 复制MP ID
const copyMpId = async (mpId: string) => {
  try {
    await navigator.clipboard.writeText(mpId);
    Message.success('MP ID 已复制到剪贴板');
  } catch (error) {
    // 如果 clipboard API 不可用，使用传统方法
    const textArea = document.createElement('textarea');
    textArea.value = mpId;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      document.execCommand('copy');
      Message.success('MP ID 已复制到剪贴板');
    } catch (err) {
      Message.error('复制失败，请手动复制');
      console.error('复制失败:', err);
    }
    document.body.removeChild(textArea);
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
  width: 100%;
}

.search-bar {
  margin-bottom: 20px;
}

.active-mp {
  background-color: var(--color-primary-light-1);
}

.arco-drawer-body img {
  max-width: 100vw !important;
  padding: 0 !important;
}

a-list-item {
  margin-bottom: 16px;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

a-list-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

a-list-item-meta {
  margin-bottom: 8px;
}

a-list-item-meta-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-1);
}

a-list-item-meta-description {
  font-size: 14px;
  color: var(--color-text-3);
  line-height: 1.5;
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
.arco-typography{
  margin-right: 16px;
}
.total-count {
  color: var(--color-text-3);
  font-size: 14px;
  margin-bottom: 16px;
}
.arco-list-wrapper{
  width: 100% !important;
  min-width: 100% !important;
}

:deep(.arco-list-wrapper) {
  width: 100% !important;
  min-width: 100% !important;
}

:deep(.arco-list) {
  width: 100% !important;
  min-width: 100% !important;
}

:deep(.arco-card) {
  width: 100% !important;
}

:deep(.arco-card-body) {
  width: 100% !important;
}

.mp-list-container .arco-list-wrapper {
  width: 100%;
}

/* 空状态时也要100%宽 */
:deep(.arco-list-item-content) {
  width: 100%;
}

:deep(.arco-empty) {
  width: 100%;
}

/* 空状态容器 */
:deep(.arco-list-container) {
  width: 100% !important;
}

:deep(.arco-spin-nested-loading) {
  width: 100% !important;
}

:deep(.arco-spin-container) {
  width: 100% !important;
}

.article-title-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.read-status-icon {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: var(--color-text-3);
  transition: all 0.2s ease;
}

.read-status-icon:hover {
  transform: scale(1.1);
}

.read-status-icon.read {
  color: var(--color-success);
}

.favorite-icon {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: var(--color-text-3);
  transition: all 0.2s ease;
}

.favorite-icon:hover {
  transform: scale(1.1);
}

.favorite-icon.favorited {
  color: rgb(var(--warning-6));
}

.article-title-read {
  text-decoration: line-through;
  opacity: 0.7;
}

.mp-list-container {
  height: calc(100vh - 200px);
  overflow-y: auto;
  width: 100%;
}

.mp-list-container :deep(.arco-list-item) {
  justify-content: flex-start !important;
}

.mp-list-container :deep(.arco-list-item-content) {
  justify-content: flex-start !important;
  width: 100%;
}

.mp-list-container :deep(.arco-list-wrapper) {
  width: 100% !important;
}

.mp-list-container :deep(.arco-list) {
  width: 100% !important;
}

.mp-loading-more,
.mp-no-more {
  text-align: center;
  padding: 16px;
  color: var(--color-text-3);
  font-size: 14px;
}
</style>
<style>
#article-modal img{
   max-width:100%;
}
</style>