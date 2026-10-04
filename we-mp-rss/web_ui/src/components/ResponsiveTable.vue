<template>
  <div>
    <a-table :columns="columns" :data="data" :loading="loading" :pagination="pagination" :row-selection="rowSelection" row-key="rowKey" @page-change="onPageChange">
      <template v-for="slot in Object.keys($slots)" #[slot]="props">
        <slot :name="slot" v-bind="props" />
      </template>
    </a-table>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  columns: {
    type: Array,
    required: true,
  },
  data: {
    type: Array,
    required: true,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  pagination: {
    type: Object,
    default: () => ({}),
  },
  rowSelection: {
    type: Object,
    default: null,
  },
  rowKey: {
    type: String,
    default: 'id',
  },
});

const emit = defineEmits(['page-change']);

const width  = window.innerWidth
const isMobile = computed(() => width < 768);

const mobileColumns = computed(() => {
  return props.columns.map(column => ({
    ...column,
    ellipsis: true,
    width: '100%',
  }));
});

const onPageChange = (page, pageSize) => {
  emit('page-change', page, pageSize);
};
</script>