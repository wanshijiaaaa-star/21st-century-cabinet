import http from './http'
import axios from 'axios'
import { Message } from '@arco-design/web-vue'
export interface LoginParams {
  username: string
  password: string
}

export interface LoginResult {
  access_token: string
  token_type: string
}

export const login = (data: LoginParams) => {
  const formData = new URLSearchParams()
  formData.append('username', data.username)
  formData.append('password', data.password)
  return http.post<LoginResult>('/wx/auth/login', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  })
}

export interface VerifyResult {
  is_valid: boolean
  username: string
  expires_at?: number
}

export const verifyToken = () => {
  return http.get<VerifyResult>('/wx/auth/verify')
}
let qrCodeIntervalId:number = 0;
let qrCodeCounter = 0;

export const QRCode = () => {
  return new Promise((resolve, reject) => {
    if (qrCodeIntervalId) {
      clearInterval(qrCodeIntervalId);
      qrCodeIntervalId = 0;
    }
    qrCodeCounter = 0;
    
    http.get('/wx/auth/qr/code').then(res => {
      const maxAttempts = 500;
      qrCodeIntervalId = setInterval(() => {
        qrCodeCounter++;
        if(qrCodeCounter > maxAttempts) {
          clearInterval(qrCodeIntervalId);
          qrCodeIntervalId = 0;
          reject(new Error('获取二维码超时'));
          return;
        }
        axios.head(res?.code).then(response => {
          if(response.status==200){
            console.log(response)
            clearInterval(qrCodeIntervalId);
            resolve(res)
          }
        }).catch(err => {
          if(qrCodeCounter >= maxAttempts) {
            clearInterval(qrCodeIntervalId);
            reject(err);
          }
        })
      }, 1000)
    }).catch(reject)
  })
}
let interval_status_Id:number=0
export const checkQRCodeStatus = () => {
  return new Promise((resolve, reject) => {
     if (interval_status_Id) {
      clearInterval(interval_status_Id);
      qrCodeIntervalId = 0;
    }
      interval_status_Id = setInterval(() => {
        http.get("wx/auth/qr/status").then(response => {
          if(response?.login_status){
            Message.success("授权成功")
            clearInterval(interval_status_Id)
            resolve(response)
          } else if(response?.qr_code===false){
            Message.error("二维码已失效，请重新获取")
            clearInterval(interval_status_Id)
            reject(new Error('二维码已失效'))
          }
        }).catch(err => {
          // clearInterval(intervalId)
          // reject(err)
        })
      }, 3000)
  })
}
export const refreshToken = () => {
  return http.post<LoginResult>('/wx/auth/refresh')
}

export const logout = () => {
  return http.post('/wx/auth/logout')
}

export const getCurrentUser = () => {
  return http.get('/wx/user')
}

// ===== 密码找回相关 =====

export interface RequestResetCodeParams {
  username: string
}

export interface ResetPasswordParams {
  username: string
  code: string
  new_password: string
}

export const requestResetCode = (data: RequestResetCodeParams) => {
  return http.post('/wx/auth/password/reset-request', data)
}

export const resetPassword = (data: ResetPasswordParams) => {
  return http.post('/wx/auth/password/reset', data)
}