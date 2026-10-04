import http from './http'

/**
 * 文章实体接口
 * @property id 文章ID
 * @property title 文章标题
 * @property content 文章内容
 * @property mp_name 公众号名称
 * @property publish_time 发布时间
 * @property status 文章状态
 * @property link 文章链接
 * @property created_at 创建时间
 * @property is_read 阅读状态
 */
export interface Article {
  id: number | string
  title: string
  content: string
  mp_name: string
  publish_time: string
  status: number
  link: string
  created_at: string
  is_read?: number
  is_favorite?: number
}

/**
 * 文章列表查询参数接口
 * @property offset 分页偏移量
 * @property limit 每页数量
 * @property search 搜索关键词
 * @property status 文章状态
 * @property mp_id 公众号ID
 */
export interface ArticleListParams {
  page?: number
  pageSize?: number
  offset?: number
  limit?: number
  search?: string
  status?: number
  mp_id?: string
  has_content?: boolean
  only_favorite?: boolean
}

/**
 * 文章列表查询结果接口
 * @property code 状态码
 * @property data 文章列表数据
 */
export interface ArticleListResult {
  code: number
  data: Article[]
}

/**
 * 获取文章列表
 * @param params 查询参数
 * @returns 文章列表结果
 */
export const getArticles = (params: ArticleListParams) => {
  // 转换分页参数
  const apiParams = {
    offset: (params.page || 0) * (params.pageSize || 10),
    limit: params.pageSize || 10,
    search: params.search,
    status: params.status,
    mp_id: params.mp_id,
    has_content: params.has_content,
    only_favorite: params.only_favorite
  }
  return http.get<ArticleListResult>('/wx/articles', {
    params: apiParams
  })
}

/**
 * 获取文章详情
 * @param id 文章ID
 * @parama 类型 0当前,-1上一篇,1下一篇
 * @returns 文章详情结果
 */
export const getArticleDetail = (id: number, action_type: number = 0) => {
  const detailParams = { params: { content: true } }
  switch(action_type){
    case -1:
      return http.get<{code: number, data: Article}>(`/wx/articles/${id}/prev`, detailParams)
    case 1:
      return http.get<{code: number, data: Article}>(`/wx/articles/${id}/next`, detailParams)
    default:
      // 默认获取当前文章详情
      return http.get<{code: number, data: Article}>(`/wx/articles/${id}`, detailParams)
  }
}

/**
 * 获取上一篇文章详情
 * @param id 当前文章ID
 * @returns 上一篇文章详情结果
 */
export const getPrevArticleDetail = (id: number) => {
  return http.get<{code: number, data: Article}>(`/wx/articles/${id}/prev`, {
    params: { content: true }
  })
}

/**
 * 获取下一篇文章详情
 * @param id 当前文章ID
 * @returns 下一篇文章详情结果
 */
export const getNextArticleDetail = (id: number) => {
  return http.get<{code: number, data: Article}>(`/wx/articles/${id}/next`, {
    params: { content: true }
  })
}

/**
 * 删除文章
 * @param id 文章ID
 * @returns 删除结果
 */
export const deleteArticle = (id: number | string) => {
  return http.delete<{code: number, message: string}>(`/wx/articles/${id}`)
}

/**
 * 刷新单篇文章内容
 * @param id 文章ID
 * @returns 任务信息
 */
export const refreshArticle = (id: number | string) => {
  return http.post<{code: number, message: string}>(`/wx/articles/${id}/refresh`)
}

/**
 * 查询单篇文章刷新任务状态
 * @param taskId 任务ID
 * @returns 任务状态
 */
export const getRefreshArticleTaskStatus = (taskId: string) => {
  return http.get<{code: number, data: any}>(`/wx/articles/refresh/tasks/${taskId}`)
}

/**
 * 清空所有文章
 * @param id 无实际作用（保留参数）
 * @returns 清空结果
 */
export const ClearArticle = (id?: number | string) => {
  return http.delete<{code: number, message: string}>(`/wx/articles/clean`)
}

/**
 * 清空重复文章
 * @param id 无实际作用（保留参数）
 * @returns 清空结果
 */
export const ClearDuplicateArticle = (id?: number | string) => {
  return http.delete<{code: number, message: string}>(`/wx/articles/clean_duplicate_articles`)
}

/**
 * 清理旧文章参数接口
 */
export interface CleanOldArticlesParams {
  days?: number  // 清理多少天前的文章，默认3天
  mp_id?: string  // 公众号ID，不指定则清理所有公众号
  dry_run?: boolean  // 是否只预览不实际删除
}

/**
 * 清理旧文章结果接口
 */
export interface CleanOldArticlesResult {
  code: number
  data: {
    message: string
    total_count?: number
    deleted_count?: number
    cutoff_date?: string
    preview_count?: number
    preview?: Array<{
      id: string
      title: string
      mp_id: string
      publish_time: number
      publish_date: string
    }>
    dry_run?: boolean
    days?: number
    mp_id?: string
    physical_delete?: boolean
  }
}

/**
 * 清理指定天数前的旧文章
 * @param params 清理参数
 * @returns 清理结果
 */
export const cleanOldArticles = (params: CleanOldArticlesParams = {}) => {
  return http.delete<CleanOldArticlesResult>(`/wx/articles/clean-old`, {
    params: {
      days: params.days || 3,
      mp_id: params.mp_id,
      dry_run: params.dry_run || false
    }
  })
}

/**
 * 切换文章阅读状态
 * @param id 文章ID
 * @param is_read 阅读状态
 * @returns 操作结果
 */
export const toggleArticleReadStatus = (id: number | string, is_read: boolean) => {
  return http.put<{code: number, message: string, is_read: boolean}>(`/wx/articles/${id}/read`, null, {
    params: { is_read }
  })
}

/**
 * 切换文章收藏状态
 * @param id 文章ID
 * @param is_favorite 收藏状态
 * @returns 操作结果
 */
export const toggleArticleFavoriteStatus = (id: number | string, is_favorite: boolean) => {
  return http.put<{code: number, message: string, is_favorite: boolean}>(`/wx/articles/${id}/favorite`, null, {
    params: { is_favorite }
  })
}

