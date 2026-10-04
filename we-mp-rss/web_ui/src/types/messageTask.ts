export interface MessageTask {
  id: string
  name: string
  message_type: number
  message_template: string
  web_hook_url: string
  headers?: string
  cookies?: string
  mps_id: any // JSON类型
  status: number
  cron_exp?: string
  created_at?: string
  updated_at?: string
}

export interface MessageTaskCreate {
  name: string
  message_type: number
  message_template: string
  web_hook_url: string
  headers?: string
  cookies?: string
  mps_id: any
  status?: number
  cron_exp?: string
}

export interface MessageTaskUpdate {
  name?: string
  message_type?: number
  message_template?: string
  web_hook_url?: string
  headers?: string
  cookies?: string
  mps_id?: any
  status?: number
  cron_exp?: string
}