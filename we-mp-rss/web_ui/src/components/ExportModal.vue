<template>
  <a-modal v-model:visible="visible" title="导出设置" @ok="handleOk" @cancel="handleCancel">
    <a-form :model="form">
      <a-form-item label="导出范围" field="scope">
        <a-select v-model="form.scope" placeholder="请选择导出范围" disabled>
          <a-option value="all">指定页数</a-option>
          <a-option value="selected">已选文章</a-option>
        </a-select>
      </a-form-item>
      <a-form-item label="导出格式" field="format">
        <a-select v-model="form.format" placeholder="请选择导出格式" multiple>
          <a-option value="csv">Excel列表</a-option>
          <a-option value="md">MarkDown</a-option>
          <a-option value="json">JSON附加信息</a-option>
          <a-option value="pdf">PDF归档</a-option>
          <a-option value="docx">WORD文档</a-option>
        </a-select>
      </a-form-item>
      <a-form-item label="导出页数" field="limit" v-if="form.scope === 'all' || form.scope === 'current'">
        <a-input-number v-model="form.page_count" :min="1" :max="10000" />
      </a-form-item>
      <a-form-item label="文件名" field="zip_filename">
        <a-input v-model="form.zip_filename" placeholder="请输入导出文件名（可选）" />
      </a-form-item>
      <a-form-item label="导出选项" field="options">
        <a-space direction="vertical">
          <a-checkbox v-model="form.add_title">添加标题</a-checkbox>
          <a-checkbox v-model="form.remove_images">移除图片</a-checkbox>
          <a-checkbox v-model="form.remove_links">移除链接</a-checkbox>
        </a-space>
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Message } from '@arco-design/web-vue';
import { exportArticles } from '@/api/tools';


const visible = ref(false);
const form = ref({
  scope: 'all',
  format: ['pdf', 'docx', 'json', 'csv',"md"],
  page_count: 10,
  mp_id: '',
  ids:[],
  add_title: true,
  remove_images: false,
  remove_links: false,
  zip_filename: '',
});

const emit = defineEmits(['confirm']);

const show = (mp_id: string, ids:any, mp_name?: string) => {
  visible.value = true;
  form.value.mp_id = mp_id;
  console.log(ids)
  form.value.scope = ids && ids.length > 0 ? 'selected' : 'all';
  form.value.ids=ids;
  
  // 如果提供了公众号名称，设置默认文件名
  if (mp_name && mp_name !== '全部') {
    form.value.zip_filename = `${mp_name}_文章.zip`;
  } else {
    form.value.zip_filename = '全部文章.zip';
  }
  
};

const hide = () => {
  visible.value = false;
};

const handleOk = () => {
  SubmitExport(form.value);
  emit('confirm', form.value);
  hide();
};
const SubmitExport = async (params: any) => {
  try {
    const result = await exportArticles(params);
    console.log('导出成功:', result);
    Message.success(result.message || '导出成功！');
  } catch (error) {
    console.error('导出失败:', error);
  }
};
const handleCancel = () => {
  hide();
};

defineExpose({
  show,
  hide,
});
</script>
