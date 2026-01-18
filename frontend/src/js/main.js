// Alpine.js 应用状态管理
document.addEventListener('alpine:init', () => {
  Alpine.data('app', () => ({
    // 当前标签页
    currentTab: 'bilibili',

    // 主题管理
    currentTheme: window.ThemeManager?.getCurrentTheme() || 'system',

    // 表单数据
    biliUrl: '',
    selectedFile: null,
    batchUrls: '',
    videoPath: '',
    subtitleText: '',

    // 多P视频相关状态
    multiPartInfo: null,
    selectedParts: [],
    checking: false,
    checkStatus: 'idle',
    checkMessage: '',

    // 状态
    processing: false,
    currentTask: null,
    result: null,
    canCancel: false,
    tasks: [],
    tasksLoading: false,
    tasksPollInterval: null,

    // 轮询定时器
    pollInterval: null,

    init() {
      this.refreshTasks();
      this.startTasksPolling();
      this.$watch('biliUrl', () => {
        this.resetBiliCheckState(false);
      });
    },

    // 主题切换
    toggleTheme() {
      const newTheme = window.ThemeManager.cycleTheme();
      this.currentTheme = newTheme;
    },

    // 获取主题标签
    getThemeLabel() {
      const labels = {
        light: '浅色',
        dark: '深色',
        system: '跟随系统'
      };
      return labels[this.currentTheme] || '跟随系统';
    },

    // 处理 B站视频
    async processBilibili() {
      if (!this.biliUrl) return;

      this.processing = true;
      this.result = null;

      try {
        const response = await fetch('/api/v1/process/bilibili', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({video_url: this.biliUrl})
        });

        const data = await response.json();

        if (response.ok) {
          this.currentTask = data;
          this.canCancel = true;
          this.startPolling(data.task_id);
        } else {
          alert('错误: ' + (data.detail || '处理失败'));
          this.processing = false;
        }
      } catch (error) {
        alert('请求失败: ' + error.message);
        this.processing = false;
      }
    },

    // 检查是否为多P视频
    async checkMultiPart() {
      if (!this.biliUrl) return;

      this.checking = true;
      this.checkStatus = 'checking';
      this.checkMessage = '';
      this.multiPartInfo = null;
      this.selectedParts = [];
      this.result = null;

      try {
        const response = await fetch('/api/v1/bilibili/check-multipart', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({video_url: this.biliUrl})
        });

        const data = await response.json();

        if (response.ok) {
          if (data.is_multipart) {
            this.multiPartInfo = data.info;
            this.selectedParts = [];
            this.checkStatus = 'multi';
            this.checkMessage = '检测到多P视频，请选择分P';
          } else {
            this.checkStatus = 'single';
            this.checkMessage = '单P视频，无需选分P';
          }
          this.checking = false;
        } else {
          alert('错误: ' + (data.detail || '检查失败'));
          this.checkStatus = 'error';
          this.checkMessage = data.detail || '检查失败';
          this.checking = false;
        }
      } catch (error) {
        alert('请求失败: ' + error.message);
        this.checkStatus = 'error';
        this.checkMessage = '请求失败，请稍后重试';
        this.checking = false;
      }
    },


    // 处理多P视频
    async processMultiPart() {
      if (this.selectedParts.length === 0) {
        alert('请至少选择一个分P');
        return;
      }

      this.processing = true;
      this.result = null;

      try {
        const response = await fetch('/api/v1/process/multipart', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            video_url: this.biliUrl,
            // 转换为数字类型，匹配后端 API 期望的 list[int]
            selected_parts: this.selectedParts.map(p => Number(p))
          })
        });

        const data = await response.json();

        if (response.ok) {
          this.currentTask = data;
          this.canCancel = true;
          this.startPolling(data.task_id);
          // 重置多P状态
          this.multiPartInfo = null;
          this.selectedParts = [];
        } else {
          alert('错误: ' + (data.detail || '处理失败'));
          this.processing = false;
        }
      } catch (error) {
        alert('请求失败: ' + error.message);
        this.processing = false;
      }
    },

    resetBiliCheckState(clearUrl = false) {
      this.multiPartInfo = null;
      this.selectedParts = [];
      this.checking = false;
      this.checkStatus = 'idle';
      this.checkMessage = '';
      if (clearUrl) {
        this.biliUrl = '';
      }
    },

    // 重置多P选择
    resetMultiPart() {
      this.resetBiliCheckState(true);
    },

    // 全选分P
    selectAllParts() {
      if (this.multiPartInfo) {
        // 确保使用字符串类型，与 HTML checkbox value 保持一致
        this.selectedParts = this.multiPartInfo.parts.map(p => String(p.part_number));
      }
    },

    // 取消全选
    deselectAllParts() {
      this.selectedParts = [];
    },

    // 反选
    inverseSelectParts() {
      if (this.multiPartInfo) {
        // 确保使用字符串类型，与 HTML checkbox value 保持一致
        const allParts = this.multiPartInfo.parts.map(p => String(p.part_number));
        this.selectedParts = allParts.filter(p => !this.selectedParts.includes(p));
      }
    },

    // 格式化时长
    formatDuration(seconds) {
      if (!seconds) return '';
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return `${mins}:${secs.toString().padStart(2, '0')}`;
    },

    // 处理文件选择
    handleFileSelect(event) {
      this.selectedFile = event.target.files[0];
    },

    // 上传音频文件
    async uploadAudio() {
      if (!this.selectedFile) return;

      this.processing = true;
      this.result = null;

      const formData = new FormData();
      formData.append('file', this.selectedFile);

      try {
        const response = await fetch('/api/v1/process/audio', {
          method: 'POST',
          body: formData
        });

        const data = await response.json();

        if (response.ok) {
          this.currentTask = data;
          this.canCancel = true;
          this.startPolling(data.task_id);
        } else {
          alert('错误: ' + (data.detail || '处理失败'));
          this.processing = false;
        }
      } catch (error) {
        alert('请求失败: ' + error.message);
        this.processing = false;
      }
    },

    // 批量处理
    async processBatch() {
      if (!this.batchUrls) return;

      const urls = this.batchUrls.split('\n')
        .map(url => url.trim())
        .filter(url => url.length > 0);

      if (urls.length === 0) {
        alert('请输入至少一个有效的 URL');
        return;
      }

      this.processing = true;
      this.result = null;

      try {
        const response = await fetch('/api/v1/process/batch', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({urls})
        });

        const data = await response.json();

        if (response.ok) {
          this.currentTask = data;
          this.canCancel = true;
          this.startPolling(data.task_id);
        } else {
          alert('错误: ' + (data.detail || '处理失败'));
          this.processing = false;
        }
      } catch (error) {
        alert('请求失败: ' + error.message);
        this.processing = false;
      }
    },

    // 生成字幕
    async generateSubtitle() {
      if (!this.videoPath) return;

      this.processing = true;
      this.result = null;

      try {
        const response = await fetch('/api/v1/subtitle/generate', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            video_path: this.videoPath,
            subtitle_text_path: this.subtitleText || undefined
          })
        });

        const data = await response.json();

        if (response.ok) {
          this.currentTask = data;
          this.canCancel = true;
          this.startPolling(data.task_id);
        } else {
          alert('错误: ' + (data.detail || '处理失败'));
          this.processing = false;
        }
      } catch (error) {
        alert('请求失败: ' + error.message);
        this.processing = false;
      }
    },

    // 开始轮询任务状态
    startPolling(taskId) {
      if (this.pollInterval) {
        clearInterval(this.pollInterval);
      }

      this.pollInterval = setInterval(async () => {
        await this.checkTaskStatus(taskId);
      }, 2000); // 每2秒查询一次
    },

    // 检查任务状态
    async checkTaskStatus(taskId) {
      try {
        const response = await fetch(`/api/v1/task/${taskId}`);
        const data = await response.json();

        if (response.ok) {
          this.currentTask = data;

          // 任务完成或失败时停止轮询
          if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
            clearInterval(this.pollInterval);
            this.processing = false;
            this.canCancel = false;

            if (data.status === 'completed') {
              this.result = data.result;
            } else if (data.status === 'failed') {
              alert('任务失败: ' + (data.error || '未知错误'));
            }
          }
        } else {
          // 后端返回错误状态码（如 404、500）
          console.error('查询任务状态失败，状态码:', response.status);
          // 如果是 404（任务不存在），停止轮询并重置状态
          if (response.status === 404) {
            clearInterval(this.pollInterval);
            this.processing = false;
            this.canCancel = false;
            alert('任务不存在或已过期');
          }
        }
      } catch (error) {
        // 网络错误或其他异常，停止轮询并重置状态，避免 UI 永久卡住
        console.error('查询任务状态失败:', error);
        clearInterval(this.pollInterval);
        this.processing = false;
        this.canCancel = false;
        alert('网络错误，无法查询任务状态。请刷新页面或检查网络连接。');
      }
    },

    // 取消任务
    async cancelTask() {
      if (!this.currentTask || !this.canCancel) return;

      try {
        const response = await fetch(`/api/v1/task/${this.currentTask.task_id}/cancel`, {
          method: 'POST'
        });

        if (response.ok) {
          alert('已请求取消任务');
          this.canCancel = false;
        } else {
          alert('取消任务失败');
        }
      } catch (error) {
        alert('请求失败: ' + error.message);
      }
    },

    async refreshTasks() {
      if (this.tasksLoading) return;
      this.tasksLoading = true;

      try {
        const response = await fetch('/api/v1/tasks');
        const data = await response.json();

        if (response.ok) {
          this.tasks = Array.isArray(data.tasks) ? data.tasks : [];
        }
      } catch (error) {
        console.error('获取任务列表失败:', error);
      } finally {
        this.tasksLoading = false;
      }
    },

    startTasksPolling() {
      if (this.tasksPollInterval) {
        clearInterval(this.tasksPollInterval);
      }
      this.tasksPollInterval = setInterval(async () => {
        await this.refreshTasks();
      }, 3000);
    },

    getSortedTasks() {
      const tasks = Array.isArray(this.tasks) ? this.tasks : [];
      return tasks.slice().sort((a, b) => {
        const aTime = a?.created_at ? Date.parse(a.created_at) : 0;
        const bTime = b?.created_at ? Date.parse(b.created_at) : 0;
        return bTime - aTime;
      });
    },

    getResultEntries(result) {
      if (!result || typeof result !== 'object') return [];

      const preferredKeys = [
        'title',
        'output_dir',
        'extract_time',
        'polish_time',
        'zip_file',
        'total_time',
        'status_message',
        'subtitle_file',
        'output_video',
        'info',
        'summary',
        'summary_text'
      ];

      const entries = [];
      for (const key of preferredKeys) {
        if (result[key] !== undefined && result[key] !== null && result[key] !== '') {
          entries.push({key, value: result[key]});
        }
      }

      if (entries.length > 0) {
        return entries;
      }

      return Object.entries(result)
        .slice(0, 8)
        .map(([key, value]) => ({key, value}));
    },

    formatResultValue(key, value) {
      if (value === null || value === undefined) return '';

      if (key === 'output_dir' && typeof value === 'object') {
        if (value.output_dir) return value.output_dir;
      }

      const numericValue = typeof value === 'number'
        ? value
        : (typeof value === 'string' ? Number.parseFloat(value) : Number.NaN);

      if (
        (key === 'extract_time' || key === 'polish_time' || key === 'total_time') &&
        Number.isFinite(numericValue)
      ) {
        return `${numericValue.toFixed(1)} s`;
      }

      if (typeof value === 'object') {
        try {
          return JSON.stringify(value);
        } catch (error) {
          return String(value);
        }
      }

      return String(value);
    },

    // 获取状态颜色（支持暗色主题）
    getStatusColor(status) {
      const colors = {
        'pending': 'text-yellow-600 dark:text-yellow-400',
        'processing': 'text-blue-600 dark:text-blue-400',
        'completed': 'text-green-600 dark:text-green-400',
        'failed': 'text-red-600 dark:text-red-400',
        'cancelled': 'text-gray-600 dark:text-gray-400'
      };
      return colors[status] || 'text-gray-600 dark:text-gray-400';
    }
  }));
});
