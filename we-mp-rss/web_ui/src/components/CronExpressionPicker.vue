<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: '* * * * *'
  }
})

const emit = defineEmits(['update:modelValue'])

const minutes = ref('*')
const hours = ref('*')
const days = ref('*')
const months = ref('*')
const weekdays = ref('*')

// 手动输入模式
const manualInputMode = ref(false)

// 表单模型（用于解决 a-form 的 model 警告）
const formModel = ref({
  manualExpression: ''
})

// 初始化时解析传入的表达式
onMounted(() => {
  if (props.modelValue) {
    parseExpression(props.modelValue)
  }
})

const parseCronDescription = (part: string, type: string) => {
  if (part === '*') return `每${type}`
  if (part.startsWith('*/')) {
    const num = part.substring(2)
    return `每${num}${type}`
  }
  // 支持 9-23/3 这种格式（范围+步长）
  if (part.includes('/') && part.includes('-')) {
    const [range, step] = part.split('/')
    const [start, end] = range.split('-')
    return `${start}到${end}${type}每${step}${type}`
  }
  if (part.includes('-')) {
    const [start, end] = part.split('-')
    return `${start}到${end}${type}`
  }
  if (part.includes(',')) {
    return `在${part.split(',').join('、')}${type}`
  }
  return `在${part}${type}`
}

const cronExpression = computed(() => {
  return `${minutes.value} ${hours.value} ${days.value} ${months.value} ${weekdays.value}`
})

const cornDescription = computed(() => {
  const monthDesc = parseCronDescription(months.value, '月')
  const dayDesc = parseCronDescription(days.value, '日')
  const hourDesc = parseCronDescription(hours.value, '小时')
  const minuteDesc = parseCronDescription(minutes.value, '分钟')
  
  let weekdayDesc = ''
  if (weekdays.value === '*') {
    weekdayDesc = '每天'
  } else if (weekdays.value === '1-5') {
    weekdayDesc = '工作日'
  } else if (weekdays.value === '0,6') {
    weekdayDesc = '周末'
  } else if (weekdays.value.includes(',')) {
    const days = weekdays.value.split(',').map(d => 
      ['周日','周一','周二','周三','周四','周五','周六'][parseInt(d)]
    )
    weekdayDesc = `在${days.join('、')}`
  } else if (weekdays.value.includes('-')) {
    const [start, end] = weekdays.value.split('-').map(d => 
      ['周日','周一','周二','周三','周四','周五','周六'][parseInt(d)]
    )
    weekdayDesc = `${start}到${end}`
  } else {
    weekdayDesc = `在${['周日','周一','周二','周三','周四','周五','周六'][parseInt(weekdays.value)]}`
  }
  
  return `${monthDesc} ${dayDesc} ${weekdayDesc} ${hourDesc} ${minuteDesc}`
})

const updateExpression = () => {
  emit('update:modelValue', cronExpression.value)
  // 同步更新手动输入值
  formModel.value.manualExpression = cronExpression.value
}

const parseExpression = (expr: string) => {
  const parts = expr.split(' ')
  if (parts.length === 5) {
    minutes.value = parts[0]
    hours.value = parts[1]
    days.value = parts[2]
    months.value = parts[3]
    weekdays.value = parts[4]
    // 同步更新手动输入值
    formModel.value.manualExpression = expr
  }
}

// 验证 cron 表达式
const validateCronExpression = (expr: string): boolean => {
  const parts = expr.trim().split(/\s+/)
  if (parts.length !== 5) {
    Message.error('表达式格式错误：需要5个部分（分钟 小时 日 月 星期）')
    return false
  }
  
  const [min, hour, day, month, weekday] = parts
  
  // 简单验证各部分格式
  const validatePart = (value: string, min: number, max: number, name: string): boolean => {
    if (value === '*') return true
    if (value.startsWith('*/')) {
      const num = parseInt(value.substring(2))
      if (isNaN(num) || num < 1 || num > max) {
        Message.error(`${name}部分格式错误`)
        return false
      }
      return true
    }
    if (value.includes(',') || value.includes('-') || value.includes('/')) {
      return true // 复杂格式，不做详细验证
    }
    const num = parseInt(value)
    if (isNaN(num) || num < min || num > max) {
      Message.error(`${name}部分数值超出范围`)
      return false
    }
    return true
  }
  
  return validatePart(min, 0, 59, '分钟') &&
         validatePart(hour, 0, 23, '小时') &&
         validatePart(day, 1, 31, '日') &&
         validatePart(month, 1, 12, '月') &&
         validatePart(weekday, 0, 6, '星期')
}

// 应用手动输入的表达式
const applyManualExpression = () => {
  if (validateCronExpression(formModel.value.manualExpression)) {
    parseExpression(formModel.value.manualExpression)
    emit('update:modelValue', formModel.value.manualExpression)
    Message.success('表达式已应用')
  }
}

// 切换输入模式
const toggleInputMode = () => {
  manualInputMode.value = !manualInputMode.value
  if (manualInputMode.value) {
    // 切换到手动模式时，将当前选择器的值同步到手动输入框
    formModel.value.manualExpression = cronExpression.value
  } else {
    // 切换到选择器模式时，解析手动输入的值并更新选择器
    if (formModel.value.manualExpression) {
      parseExpression(formModel.value.manualExpression)
    }
  }
}

// 监听 modelValue 变化，同步更新手动输入值
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    // 无论在哪个模式，都要同步更新手动输入值
    formModel.value.manualExpression = newVal
    // 如果不在手动模式，也要解析表达式更新选择器
    if (!manualInputMode.value) {
      parseExpression(newVal)
    }
  }
})

// 监听手动输入变化，实时预览
watch(() => formModel.value.manualExpression, (newVal) => {
  if (manualInputMode.value && newVal && validateCronExpression(newVal)) {
    // 在手动模式下，实时解析并更新选择器的值（但不触发emit，避免循环）
    const parts = newVal.split(' ')
    if (parts.length === 5) {
      minutes.value = parts[0]
      hours.value = parts[1]
      days.value = parts[2]
      months.value = parts[3]
      weekdays.value = parts[4]
    }
  }
})

defineExpose({
  parseExpression
})
</script>

<template>
  <a-card class="cron-picker" :bordered="false">

    <!-- 手动输入模式 -->
    <div v-if="manualInputMode" class="manual-input-section">
      <a-form :model="formModel">
        <a-form-item label="Cron表达式">
          <a-input 
            v-model="formModel.manualExpression" 
            placeholder="例如: 0 12 * * * (每天中午12点)"
            @press-enter="applyManualExpression"
          />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="applyManualExpression">
            应用表达式
          </a-button>
        </a-form-item>
      </a-form>
    </div>

    <!-- 选择器模式 -->
    <a-form v-if="!manualInputMode" :model="formModel">
      <a-form-item label="分钟">
        <a-select v-model="minutes" @change="updateExpression" style="width: 180px">
          <a-option v-for="m in 60" :key="m-1" :value="(m-1).toString()">{{ m-1 }}</a-option>
          <a-option value="*">*</a-option>
          <a-option value="*/5">每5分钟</a-option>
          <a-option value="*/1~59">每1-59分钟(随机)</a-option>
          <a-option value="*/15">每15分钟</a-option>
          <a-option value="*/30">每30分钟</a-option>
          <a-option value="0-30">0-30分钟</a-option>
          <a-option value="30-59">30-59分钟</a-option>
        </a-select>
      </a-form-item>
      <a-form-item label="小时">
        <a-select v-model="hours" @change="updateExpression" style="width: 180px">
          <a-option v-for="h in 24" :key="h-1" :value="(h-1).toString()">{{ h-1 }}</a-option>
          <a-option value="*">*</a-option>
          <a-option value="*/1">每1小时</a-option>
          <a-option value="*/2">每2小时</a-option>
          <a-option value="*/3">每3小时</a-option>
          <a-option value="*/4">每4小时</a-option>
          <a-option value="*/5">每5小时</a-option>
          <a-option value="*/8">每8小时</a-option>
          <a-option value="*/6">每6小时</a-option>
          <a-option value="9-21/3">9-21点每3小时</a-option>
          <a-option value="*/12">每12小时</a-option>
          <a-option value="0-12">0-12点</a-option>
          <a-option value="12-23">12-23点</a-option>
        </a-select>
      </a-form-item>
      <a-form-item label="日">
        <a-select v-model="days" @change="updateExpression" style="width: 180px">
          <a-option v-for="d in 31" :key="d" :value="d.toString()">{{ d }}</a-option>
          <a-option value="*">*</a-option>
          <a-option value="*/5">每5天</a-option>
          <a-option value="*/10">每10天</a-option>
          <a-option value="1-15">1-15日</a-option>
          <a-option value="16-31">16-31日</a-option>
        </a-select>
      </a-form-item>
      <a-form-item label="月">
        <a-select v-model="months" @change="updateExpression" style="width: 180px">
          <a-option v-for="m in 12" :key="m" :value="m.toString()">{{ m }}</a-option>
          <a-option value="*">*</a-option>
          <a-option value="*/3">每3个月</a-option>
          <a-option value="*/6">每6个月</a-option>
          <a-option value="1-6">1-6月</a-option>
          <a-option value="7-12">7-12月</a-option>
        </a-select>
      </a-form-item>
      <a-form-item label="星期">
        <a-select v-model="weekdays" @change="updateExpression" style="width: 180px">
          <a-option value="0">周日</a-option>
          <a-option value="1">周一</a-option>
          <a-option value="2">周二</a-option>
          <a-option value="3">周三</a-option>
          <a-option value="4">周四</a-option>
          <a-option value="5">周五</a-option>
          <a-option value="6">周六</a-option>
          <a-option value="*">*</a-option>
          <a-option value="1-5">工作日</a-option>
          <a-option value="0,6">周末</a-option>
          <a-option value="*/2">每隔一天</a-option>
        </a-select>
      </a-form-item>
    </a-form>
  <!-- 模式切换按钮 -->
    <div class="mode-toggle">
      <a-button 
        :type="manualInputMode ? 'outline' : 'primary'" 
        @click="toggleInputMode"
      >
        {{ manualInputMode ? '选择模式' : '手动输入' }}
      </a-button>
    </div>
    <a-space direction="vertical" fill>
      <a-typography-text strong>表达式预览: {{ cronExpression }}</a-typography-text>
      <a-typography-text type="secondary" style="color:green;">解释: {{ cornDescription }}</a-typography-text>

      <div class="examples">
        <a-typography-text strong>常用示例:</a-typography-text>
        <a-list :bordered="false">
          <a-list-item 
            @click="minutes='0';hours='0';days='*';months='*';weekdays='*';updateExpression()"
          >
            每天午夜 (0 0 * * *)
          </a-list-item>
          <a-list-item 
            @click="minutes='0';hours='12';days='*';months='*';weekdays='*';updateExpression()"
          >
            每天中午 (0 12 * * *)
          </a-list-item>
          <a-list-item 
            @click="minutes='0';hours='9';days='*';months='*';weekdays='1-5';updateExpression()"
          >
            工作日早上9点 (0 9 * * 1-5)
          </a-list-item>
          <a-list-item 
            @click="minutes='*/5';hours='*';days='*';months='*';weekdays='*';updateExpression()"
          >
            每5分钟 (*/5 * * * *)
          </a-list-item>
          <a-list-item 
            @click="minutes='0';hours='*/6';days='*';months='*';weekdays='*';updateExpression()"
          >
            每6小时 (0 */6 * * *)
          </a-list-item>
          <a-list-item 
            @click="minutes='0';hours='0';days='*/10';months='*';weekdays='*';updateExpression()"
          >
            每10天 (0 0 */10 * *)
          </a-list-item>
        </a-list>
      </div>
    </a-space>
  </a-card>
</template>

<style scoped>
.cron-picker {
  padding: 10px;
  max-width: 600px;
}

.mode-toggle {
  margin-bottom: 16px;
}

.manual-input-section {
  margin-bottom: 16px;
  padding: 16px;
  background-color: var(--color-fill-2);
  border-radius: 4px;
}

.arco-form-item {
  margin-bottom: 12px;
}

.examples {
  margin-top: 15px;
}

:deep(.arco-list-item) {
  padding: 8px 0;
  cursor: pointer;
  color: rgb(var(--primary-6));
}

:deep(.arco-list-item:hover) {
  background-color: var(--color-fill-2);
}
</style>