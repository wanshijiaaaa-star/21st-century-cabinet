import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

// 导入 ArcoDesign
import ArcoVue from '@arco-design/web-vue'
// 导入 ArcoDesign 图标
import ArcoVueIcon from '@arco-design/web-vue/es/icon'; // 关键步骤
// 导入 ArcoDesign 样式
import '@arco-design/web-vue/dist/arco.css'
// 导入自定义样式
import './style.css'
const app = createApp(App)
// 注册 ArcoDesign
app.use(ArcoVue)
// 注册图标组件
app.use(ArcoVueIcon)
// 注册路由
app.use(router)

app.mount('#app')
