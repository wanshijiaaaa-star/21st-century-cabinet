import http from './http'

export interface FilterRule {
  id: number
  mp_id: string  // JSON字符串，存储多个公众号ID
  mp_ids: string[]  // 解析后的公众号ID数组
  is_global: boolean  // 是否为全局规则
  rule_name: string
  remove_ids: string[]
  remove_classes: string[]
  remove_selectors: string[]
  remove_attributes: Array<{ name: string; value?: string; eq?: boolean }>
  remove_regex: string[]
  remove_normal_tag: number
  status: number
  priority: number
  created_at: string
  updated_at: string
}

export interface FilterRuleCreateParams {
  mp_id: string  // JSON字符串，存储多个公众号ID
  rule_name: string
  remove_ids?: string[]
  remove_classes?: string[]
  remove_selectors?: string[]
  remove_attributes?: Array<{ name: string; value?: string; eq?: boolean }>
  remove_regex?: string[]
  remove_normal_tag?: number
  priority?: number
}

export interface FilterRuleUpdateParams {
  rule_name?: string
  remove_ids?: string[]
  remove_classes?: string[]
  remove_selectors?: string[]
  remove_attributes?: Array<{ name: string; value?: string; eq?: boolean }>
  remove_regex?: string[]
  remove_normal_tag?: number
  status?: number
  priority?: number
}

export interface FilterRuleListResult {
  code: number
  data: {
    list: FilterRule[]
    page: {
      limit: number
      offset: number
      total: number
    }
  }
}

// 获取过滤规则列表
export const getFilterRules = (params?: { mp_id?: string; limit?: number; offset?: number }) => {
  return http.get<FilterRuleListResult>('/wx/filter-rules', { params })
}

// 获取单个过滤规则详情
export const getFilterRule = (ruleId: number) => {
  return http.get<{ code: number; data: FilterRule }>(`/wx/filter-rules/${ruleId}`)
}

// 创建过滤规则
export const createFilterRule = (data: FilterRuleCreateParams) => {
  return http.post<{ code: number; data: { id: number; message: string } }>('/wx/filter-rules', data)
}

// 更新过滤规则
export const updateFilterRule = (ruleId: number, data: FilterRuleUpdateParams) => {
  return http.put<{ code: number; data: { id: number; message: string } }>(`/wx/filter-rules/${ruleId}`, data)
}

// 删除过滤规则
export const deleteFilterRule = (ruleId: number) => {
  return http.delete<{ code: number; data: { id: number; message: string } }>(`/wx/filter-rules/${ruleId}`)
}

// 获取公众号的启用规则
export const getActiveRulesForMp = (mpId: string) => {
  return http.get<{ code: number; data: FilterRule[] }>(`/wx/filter-rules/mp/${mpId}/active`)
}
