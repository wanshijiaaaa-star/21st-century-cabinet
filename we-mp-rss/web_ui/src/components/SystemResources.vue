<template>
    <div class="resource-charts">
      <!-- CPU 使用率 -->
        <div class="chart-container">
          <a-tooltip :content="`CPU 核心数: ${resources.cpu?.cores || 0} 核 / ${resources.cpu?.threads || 0} 线程`">
          <custom-pie-chart :percent="resources.cpu?.percent || 0"  :title="`CPU`" :info="` ${resources.cpu?.cores || 0} 核 / ${resources.cpu?.threads || 0} 线程`"/>
          </a-tooltip>
        </div>

      <!-- 内存使用率 -->
         
        <div class="chart-container">
          <a-tooltip placement="top" :content="`内存总量: ${resources.memory?.total || 0} GB (已用: ${resources.memory?.used || 0} GB, 空闲: ${resources.memory?.free || 0} GB)`">
          <custom-pie-chart :percent="resources.memory?.percent || 0"  :title="`内存`" :info="` ${resources.memory?.used || 0}GB/${resources.memory?.total || 0}GB`"/>
          </a-tooltip>
        </div>
      <!-- 磁盘使用率 -->
        <div class="chart-container">
          <a-tooltip placement="top" :content="`磁盘总量: ${resources.disk?.total || 0} GB (已用: ${resources.disk?.used || 0} GB, 空闲: ${resources.disk?.free || 0} GB)`">
          <custom-pie-chart :percent="resources.disk?.percent || 0" :title="`磁盘`" :info="` ${resources.disk?.used || 0}GB/${resources.disk?.total || 0} GB `"/>
          </a-tooltip>
        </div>
    </div>
</template>

<script>
import { DashboardOutlined } from '@ant-design/icons-vue';
import CustomPieChart from './CustomPieChart.vue';
import { getSysResources } from '@/api/sysInfo';

export default {
  components: { DashboardOutlined, CustomPieChart },
  data() {
    return {
      resources: {
        cpu: { percent: 0, cores: 0, threads: 0 },
        memory: { percent: 0, total: 0, used: 0, free: 0 },
        disk: { percent: 0, total: 0, used: 0, free: 0 }
      },
      intervalId: null
    };
  },
  methods: {
    async fetchResources() {
      this.resources = await getSysResources();
    }
  },
  mounted() {
    this.fetchResources();
    this.intervalId = setInterval(() => {
      this.fetchResources();
    }, 2000);
    
    // 监听路由变化
    this.unwatchRoute = this.$router.afterEach(() => {
      if (this.intervalId) {
        clearInterval(this.intervalId);
        this.intervalId = null;
      }
    });
  },
  activated() {
    // 组件可见时重新开始获取数据
    this.fetchResources();
    this.intervalId = setInterval(() => {
      this.fetchResources();
    }, 1000);
  },
  deactivated() {
    // 组件不可见时停止获取数据
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  },
  beforeDestroy() {
    // 移除路由监听器
    if (this.unwatchRoute) {
      this.unwatchRoute();
    }
  }
};
</script>

<style scoped>
.sys-info-card {
  margin-bottom: 16px;
}
.resource-charts {
  display: flex;
  justify-content: space-around;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
}
.chart-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
}

:deep(.resource-tooltip) {
  .ant-tooltip-inner {
    background: rgba(0, 0, 0, 0.85);
    color: white;
    padding: 8px 12px;
    border-radius: 4px;
  }
}
</style>