// Alpine.js 应用状态管理
document.addEventListener('alpine:init', () => {
    Alpine.data('app', () => ({
        // 当前标签页
        currentTab: 'bilibili',

        // 表单数据
        biliUrl: '',
        selectedFile: null,
        batchUrls: '',
        videoPath: '',
        subtitleText: '',

        // 状态
        processing: false,
        currentTask: null,
        result: null,
        canCancel: false,

        // 轮询定时器
        pollInterval: null,

        // 处理 B站视频
        async processBilibili() {
            if (!this.biliUrl) return;

            this.processing = true;
            this.result = null;

            try {
                const response = await fetch('/api/v1/process/bilibili', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: this.biliUrl})
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
                }
            } catch (error) {
                console.error('查询任务状态失败:', error);
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

        // 获取状态颜色
        getStatusColor(status) {
            const colors = {
                'pending': 'text-yellow-600',
                'processing': 'text-blue-600',
                'completed': 'text-green-600',
                'failed': 'text-red-600',
                'cancelled': 'text-gray-600'
            };
            return colors[status] || 'text-gray-600';
        }
    }));
});
