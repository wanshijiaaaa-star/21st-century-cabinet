import { createRouter, createWebHistory } from 'vue-router'
import BasicLayout from '../components/Layout/BasicLayout.vue'
import ExportRecords from '../views/ExportRecords.vue'
import Login from '../views/Login.vue'
import ArticleList from '../views/ArticleList.vue'
import ChangePassword from '../views/ChangePassword.vue'
import EditUser from '../views/EditUser.vue'
import AddSubscription from '../views/AddSubscription.vue'
import WeChatMpManagement from '../views/WeChatMpManagement.vue'
import ConfigList from '../views/ConfigList.vue'
import ConfigDetail from '../views/ConfigDetail.vue'
import MessageTaskList from '../views/MessageTaskList.vue'
import MessageTaskForm from '../views/MessageTaskForm.vue'
import NovelReader from '../views/NovelReader.vue'
import FilterRuleList from '../views/FilterRuleList.vue'
import FilterRuleForm from '../views/FilterRuleForm.vue'
import TaskQueueView from '../views/TaskQueueView.vue'
import ForgotPassword from '../views/ForgotPassword.vue'

const routes = [
  {
    path: '/',
    component: BasicLayout,
    children: [
      {
        path: '',
        name: 'Home',
        component: ArticleList,
        meta: { requiresAuth: true }
      },
      {
        path: 'change-password',
        name: 'ChangePassword',
        component: ChangePassword,
        meta: { requiresAuth: true }
      },
      {
        path: 'edit-user',
        name: 'EditUser',
        component: EditUser,
        meta: { requiresAuth: true }
      },
      {
        path: 'add-subscription',
        name: 'AddSubscription',
        component: AddSubscription,
        meta: { requiresAuth: true }
      },
      {
        path: 'wechat/mp',
        name: 'WeChatMpManagement',
        component: WeChatMpManagement,
        meta: { 
          requiresAuth: true,
          permissions: ['wechat:manage'] 
        }
      },
      
      {
        path: 'configs',
        name: 'ConfigList',
        component: ConfigList,
        meta: { 
          requiresAuth: true,
          permissions: ['config:view'] 
        }
      },
      {
        path: 'export/records',
        name: 'ExportList',
        component: ExportRecords,
        meta: { 
          requiresAuth: true,
          permissions: ['config:view'] 
        }
      },
      {
        path: 'configs/:key',
        name: 'ConfigDetail',
        component: ConfigDetail,
        props: true,
        meta: { 
          requiresAuth: true,
          permissions: ['config:view'] 
        }
      },
      {
        path: 'message-tasks',
        name: 'MessageTaskList',
        component: MessageTaskList,
        meta: { 
          requiresAuth: true,
          permissions: ['message_task:view'] 
        }
      },
      {
        path: 'message-tasks/add',
        name: 'MessageTaskAdd',
        component: MessageTaskForm,
        meta: { 
          requiresAuth: true,
          permissions: ['message_task:edit'] 
        }
      },
      {
        path: 'message-tasks/edit/:id',
        name: 'MessageTaskEdit',
        component: MessageTaskForm,
        props: true,
        meta: { 
          requiresAuth: true,
          permissions: ['message_task:edit'] 
        }
      },
      {
        path: 'sys-info',
        name: 'SysInfo',
        component: () => import('@/views/SysInfo.vue'),
        meta: { 
          requiresAuth: true,
          permissions: ['admin'] 
        }
      },
      {
        path: 'tags',
        name: 'TagList',
        component: () => import('@/views/TagList.vue'),
        meta: { 
          requiresAuth: true,
          permissions: ['tag:view'] 
        }
      },
      {
        path: 'tags/add',
        name: 'TagAdd',
        component: () => import('@/views/TagForm.vue'),
        meta: { 
          requiresAuth: true,
          permissions: ['tag:edit'] 
        }
      },
      {
        path: 'tags/edit/:id',
        name: 'TagEdit',
        component: () => import('@/views/TagForm.vue'),
        props: true,
        meta: { 
          requiresAuth: true,
          permissions: ['tag:edit'] 
        }
      },
      {
        path: 'access-keys',
        name: 'AccessKeyManagement',
        component: () => import('@/views/AccessKeyManagement.vue'),
        meta: { 
          requiresAuth: true,
          permissions: ['admin'] 
        }
      },
      {
        path: 'cascade',
        name: 'CascadeManagement',
        component: () => import('@/views/CascadeManagement.vue'),
        meta: { 
          requiresAuth: true,
          permissions: ['admin'] 
        }
      },
      {
        path: 'cascade/feed-status',
        name: 'CascadeFeedStatus',
        component: () => import('@/views/CascadeFeedStatus.vue'),
        meta: { 
          requiresAuth: true,
          permissions: ['admin'] 
        }
      },
      {
        path: 'env-exception',
        name: 'EnvExceptionStats',
        component: () => import('@/views/EnvExceptionStats.vue'),
        meta: { 
          requiresAuth: true,
          permissions: ['admin'] 
        }
      },
      {
        path: 'filter-rules',
        name: 'FilterRuleList',
        component: FilterRuleList,
        meta: { 
          requiresAuth: true,
          permissions: ['wechat:manage'] 
        }
      },
      {
        path: 'filter-rules/add',
        name: 'FilterRuleAdd',
        component: FilterRuleForm,
        meta: { 
          requiresAuth: true,
          permissions: ['wechat:manage'] 
        }
      },
      {
        path: 'filter-rules/edit/:id',
        name: 'FilterRuleEdit',
        component: FilterRuleForm,
        props: true,
        meta: { 
          requiresAuth: true,
          permissions: ['wechat:manage'] 
        }
      },
      {
        path: 'task-queue',
        name: 'TaskQueue',
        component: TaskQueueView,
        meta: { 
          requiresAuth: true,
          permissions: ['admin'] 
        }
      },
      {
        path: 'wechat-status',
        name: 'WechatStatus',
        component: () => import('@/views/WechatStatus.vue'),
        meta: { 
          requiresAuth: true,
          permissions: ['wechat:manage'] 
        }
      },
      {
        path: 'users',
        name: 'UserManagement',
        component: () => import('@/views/UserManagement.vue'),
        meta: { 
          requiresAuth: true,
          permissions: ['admin'] 
        }
      },
      {
        path: 'weread',
        name: 'WereadManagement',
        component: () => import('@/views/WereadManagement.vue'),
        meta: { 
          requiresAuth: true,
          permissions: ['wechat:manage'] 
        }
      },
    ]
  },
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: ForgotPassword
  },
  {
        path: '/reader',
        name: 'NovelReader',
        component: NovelReader,
        meta: { requiresAuth: true }
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach(async (to, from, next) => {
  // 不需要认证的路由直接放行
  if (!to.meta.requiresAuth) {
    return next()
  }

  const token = localStorage.getItem('token')
  
  // 未登录则跳转登录页
  if (!token) {
    return next({
      path: '/login',
      query: { redirect: to.fullPath } // 保存目标路由用于登录后跳转
    })
  }

  // 已登录状态，验证token有效性
  try {
    // 确保从正确路径导入verifyToken
    const { verifyToken } = await import('@/api/auth')
    await verifyToken()
    next()
  } catch (error) {
    console.error('Token验证失败:', error)
    // token无效时清除并跳转登录
    localStorage.removeItem('token')
    next({
      path: '/login',
      query: { 
        redirect: to.fullPath,
        error: 'session_expired'
      }
    })
  }
})

export default router