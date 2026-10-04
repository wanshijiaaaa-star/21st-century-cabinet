import http from './http'

export interface EnvExceptionStats {
  date: string
  total: number
  urls: Record<string, string>
  mp_stats: Record<string, string>
  recent_logs: string[]
}

/**
 * 获取指定日期的环境异常统计
 */
export const getEnvExceptionStats = async (date?: string): Promise<EnvExceptionStats> => {
  try {
    const params = date ? { date } : {}
    const response = await http.get('wx/env-exception/stats', { params })

    // http拦截器已处理，response直接是data对象
    const data = response || {}

    return {
      date: data.date || new Date().toISOString().split('T')[0],
      total: data.total || 0,
      urls: data.urls || {},
      mp_stats: data.mp_stats || {},
      recent_logs: data.recent_logs || []
    }
  } catch (error) {
    console.error('获取环境异常统计失败:', error)
    // 返回默认值
    return {
      date: date || new Date().toISOString().split('T')[0],
      total: 0,
      urls: {},
      mp_stats: {},
      recent_logs: []
    }
  }
}

/**
 * 获取今日环境异常统计
 */
export const getTodayStats = async (): Promise<EnvExceptionStats> => {
  try {
    const response = await http.get('wx/env-exception/today')

    // http拦截器已处理，response直接是data对象
    const data = response || {}

    return {
      date: data.date || new Date().toISOString().split('T')[0],
      total: data.total || 0,
      urls: data.urls || {},
      mp_stats: data.mp_stats || {},
      recent_logs: data.recent_logs || []
    }
  } catch (error) {
    console.error('获取今日统计失败:', error)
    // 返回默认值
    return {
      date: new Date().toISOString().split('T')[0],
      total: 0,
      urls: {},
      mp_stats: {},
      recent_logs: []
    }
  }
}
