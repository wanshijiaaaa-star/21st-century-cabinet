import http from './http';

export interface TaskRecord {
  task_name: string;
  start_time: string;
  end_time: string | null;
  duration: number | null;
  status: 'running' | 'completed' | 'failed';
  error: string | null;
}

export interface PendingTask {
  task_name: string;
  args: string;
  kwargs: string;
  add_time: string;
}

export interface CurrentTask {
  task_name: string;
  start_time: string;
  status: string;
}

export interface QueueStatus {
  tag: string;
  is_running: boolean;
  pending_count: number;
  pending_tasks: PendingTask[];
  current_task: CurrentTask | null;
  history_count: number;
  recent_history: TaskRecord[];
}

export interface AllQueuesStatus {
  main_queue: QueueStatus | null;
  content_queue: QueueStatus | null;
}

export interface SchedulerJob {
  id: string;
  name: string;
  trigger: string;
  next_run_time: string | null;
  last_run_time: string | null;
}

export interface SchedulerStatus {
  running: boolean;
  job_count: number;
  next_run_times: [string, string | null][];
}

// 获取所有队列状态
export const getQueueStatus = async (): Promise<AllQueuesStatus> => {
  try {
    const response = await http.get('/wx/task-queue/status');
    const data = response as any;
    return {
      main_queue: data?.main_queue || null,
      content_queue: data?.content_queue || null,
    };
  } catch (error) {
    console.error('Get queue status error:', error);
    throw error;
  }
};

// 获取单个队列状态
export const getMainQueueStatus = async (): Promise<QueueStatus> => {
  try {
    const response = await http.get('/wx/task-queue/main/status');
    const data = response as any;
    return normalizeQueueStatus(data);
  } catch (error) {
    console.error('Get main queue status error:', error);
    throw error;
  }
};

export const getContentQueueStatus = async (): Promise<QueueStatus> => {
  try {
    const response = await http.get('/wx/task-queue/content/status');
    const data = response as any;
    return normalizeQueueStatus(data);
  } catch (error) {
    console.error('Get content queue status error:', error);
    throw error;
  }
};

const normalizeQueueStatus = (data: any): QueueStatus => {
  if (data && typeof data === 'object') {
    return {
      tag: data.tag || '',
      is_running: data.is_running || false,
      pending_count: data.pending_count || 0,
      pending_tasks: data.pending_tasks || [],
      current_task: data.current_task || null,
      history_count: data.history_count || 0,
      recent_history: data.recent_history || [],
    };
  }
  return {
    tag: '',
    is_running: false,
    pending_count: 0,
    pending_tasks: [],
    current_task: null,
    history_count: 0,
    recent_history: [],
  };
};

export const getQueueHistory = async (
  page: number = 1,
  pageSize: number = 10,
  queueType: 'main' | 'content' = 'main'
): Promise<{ history: TaskRecord[]; total: number; page: number; page_size: number; total_pages: number }> => {
  try {
    const response = await http.get('/wx/task-queue/history', { params: { page, page_size: pageSize, queue_type: queueType } });
    const data = response as any;
    return {
      history: data?.history || [],
      total: data?.total || 0,
      page: data?.page || 1,
      page_size: data?.page_size || 10,
      total_pages: data?.total_pages || 0,
    };
  } catch (error) {
    console.error('Get queue history error:', error);
    throw error;
  }
};

export const clearQueue = async (queueType: 'main' | 'content' = 'main'): Promise<void> => {
  await http.post('/wx/task-queue/clear', null, { params: { queue_type: queueType } });
};

export const clearHistory = async (queueType: 'main' | 'content' = 'main'): Promise<void> => {
  await http.post('/wx/task-queue/history/clear', null, { params: { queue_type: queueType } });
};

export const getSchedulerStatus = async (): Promise<SchedulerStatus> => {
  try {
    const response = await http.get('/wx/task-queue/scheduler/status');
    const data = response as any;
    return {
      running: data?.running || false,
      job_count: data?.job_count || 0,
      next_run_times: data?.next_run_times || [],
    };
  } catch (error) {
    console.error('Get scheduler status error:', error);
    throw error;
  }
};

export const getSchedulerJobs = async (): Promise<{ jobs: SchedulerJob[]; total: number }> => {
  try {
    const response = await http.get('/wx/task-queue/scheduler/jobs');
    const data = response as any;
    return {
      jobs: data?.jobs || [],
      total: data?.total || 0,
    };
  } catch (error) {
    console.error('Get scheduler jobs error:', error);
    throw error;
  }
};
