import axios from 'axios'
import { getToken } from '@/utils/auth'
import { Message } from '@arco-design/web-vue'
import router from '@/router'
// 创建axios实例
const http = axios.create({
  baseURL: (import.meta.env.VITE_API_BASE_URL || '') + 'api/v1/',
  timeout: 100000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
})

// 请求拦截器
http.interceptors.request.use(
  config => {
    const token = getToken()
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
http.interceptors.response.use(
  response => {
    // 处理标准响应格式
    if (response.data?.code === 0) {
      return response.data?.data||response.data?.detail||response.data||response
    }
    if(response.data?.code==401){
      router.push("/login")
      return Promise.reject("未登录或登录已过期，请重新登录。")
    }
    const data=response.data?.detail||response.data
    const errorMsg = data?.message || '请求失败'
    if(response.headers['content-type']==='application/json') {
      Message.error(errorMsg)
    }else{
      return response.data
    }
    return Promise.reject(response.data)
  },
  error => {
     if(error.response?.status==401){
      router.push("/login")
    }
    // console.log(error)
    // 统一错误处理
    const errorMsg =error?.response?.data?.message ||
                    error?.response?.data?.detail?.message ||
                    error?.response?.data?.detail ||
                    error?.message ||
                    '请求错误'
    // Message.error(errorMsg)
    return Promise.reject(errorMsg)
  }
)

export default http
