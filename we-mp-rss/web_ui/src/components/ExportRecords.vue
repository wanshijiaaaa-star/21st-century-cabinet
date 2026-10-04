<template>
  <div class="export-records">
    <a-page-header title="导出记录" subtitle="查看和管理导出的文件">
      <template #extra>
        <a-button type="primary" @click="fetchExportRecords">
          刷新
        </a-button>
      </template>
    </a-page-header>

    <a-card>
      <a-table
        :loading="loading"
        :columns="columns"
        :data="exportRecords"
        :pagination="pagination"
      />
    </a-card>
  </div>
</template>
<script setup lang="ts">
import { Message, Modal } from '@arco-design/web-vue';
import { h, ref, onMounted, onBeforeUnmount } from 'vue';
import { IconDownload, IconDelete } from '@arco-design/web-vue/es/icon';
import { getExportRecords ,DeleteExportRecords} from '@/api/tools';
const isMobile = ref(window.innerWidth < 768);
const handleResize = () => {
  isMobile.value = window.innerWidth < 768;
};

onMounted(() => {
  window.addEventListener('resize', handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
});

const visable = ref(true);
const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0
});

const columns = [
  {
    title: '文件名',
    dataIndex: 'filename',
  },
  {
    title: '文件大小',
    dataIndex: 'size',
    render: ({ record }) => formatFileSize(record.size),
  },
  {
    title: '创建时间',
    dataIndex: 'created_time',
    render: ({ record }) => formatDateTime(record.created_time),
  },
  {
    title: '操作',
    dataIndex: 'download_url',
    render: ({ record }) => {
      return h('div', { class: 'action-buttons', style: { display: 'flex', gap: '8px' } }, [
        h('a-button', {
          type: 'outline',
          size: 'small',
          shape: 'round',
          style: { cursor: 'pointer' },
          onClick: () => handleDownload(record)
        }, [h(IconDownload), '下载']),
        h('a-button', {
          type: 'outline',
          status: 'danger',
          size: 'small',
          shape: 'round',
          style: { cursor: 'pointer' },
          onClick: () => handleDelete(record)
        }, [h(IconDelete), '删除'])
      ]);
    }
  },
];

const props = defineProps({
  mp_id: {
    type: String,
    default: '',
    required: false,
  },
});

const exportRecords = ref();
const loading = ref(false);

// 格式化文件大小为MB显示
const formatFileSize = (size: number | string): string => {
  try {
    const sizeInBytes = typeof size === 'string' ? parseInt(size) : size;
    if (isNaN(sizeInBytes) || sizeInBytes <= 0) {
      return '0 MB';
    }
    const sizeInMB = sizeInBytes / (1024 * 1024);
    return `${sizeInMB.toFixed(2)} MB`;
  } catch (error) {
    return '0 MB';
  }
};

// 格式化日期时间
const formatDateTime = (dateTime: string | number): string => {
  if (!dateTime) return '-';

  try {
    const date = new Date(dateTime);
    if (isNaN(date.getTime())) return '-';

    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  } catch (error) {
    return '-';
  }
};

// 下载文件
const handleDownload = (record: any) => {
  if (record.download_url && record.download_url !== '#') {
    window.open(record.download_url, '_blank');
  } else {
    Message.warning('下载链接不可用');
  }
};

// 删除导出记录
const handleDelete = async (record: any) => {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除文件 "${record.filename}" 吗？`,
    okText: '确定',
    cancelText: '取消',
    onOk: async () => {
      try {
        // 调用删除API
        const response = await DeleteExportRecords({
          mp_id: props.mp_id,
          filename: record.path
        });
        console.log('删除API返回数据:', response);
        if (response?.message.indexOf('成功') !== -1) {
          // API调用成功后，从本地数组中移除
          const index = exportRecords.value.findIndex((item: any) => item.filename === record.filename);
          if (index > -1) {
            exportRecords.value.splice(index, 1);
            Message.success('删除成功');
          }
        } else {
          Message.error('删除失败：' + (response.data?.message || '未知错误'));
        }
      } catch (error) {
        console.error('删除导出记录失败:', error);
      }
    }
  });
};

const fetchExportRecords = (): Promise<void> => {
  loading.value = true;
  visable.value = false;
  return getExportRecords({ mp_id: props.mp_id })
    .then((response) => {
      console.log('API 返回数据:', response);
      // 确保 response 是数组或包含 data 字段的响应
      const records = Array.isArray(response) ? response : (response?.data || []);
      exportRecords.value = records.map(record => ({
        ...record,
        filename: record.filename || '-',
        size: record.size || 0,
        created_time: record.created_time || '-',
        modified_time: record.modified_time || '-',
        download_url: record.download_url || '#'
      }));
      console.log('表格数据:', exportRecords.value); // 调试用
    })
    .catch((error) => {
      console.error('获取导出记录失败:', error);
      exportRecords.value = [];
    })
    .finally(() => {
      loading.value = false;
      visable.value = true;
    });
};

// 初始化时加载记录
fetchExportRecords();

// 暴露方法给组件外部
defineExpose({
  fetchExportRecords
});

</script>

<style scoped>
.export-records {
  padding: 16px;
}

.action-buttons {
  display: flex;
  gap: 8px;
  align-items: center;
}

.action-buttons .arco-btn {
  transition: all 0.2s ease;
}

.action-buttons .arco-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
</style>