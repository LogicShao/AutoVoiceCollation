# AutoVoiceCollation 前端文档

## 概述

AutoVoiceCollation
的新前端基于
FastAPI +
原生
HTML/CSS/JS
构建，使用
Tailwind
CSS
美化样式，Alpine.js
提供轻量级交互。

## 技术栈

-
*
*UI
框架
**:
原生
HTML5
-
*
*CSS
框架
**:
Tailwind
CSS
3.x
-
*
*JS
交互
**:
Alpine.js
3.x
-
*
*构建工具
**:
Tailwind
CLI +
PostCSS
-
*
*后端
**:
FastAPI (
Python)

## 目录结构

```
frontend/
├── src/
│   ├── index.html          # 主页面
│   ├── css/
│   │   └── input.css       # Tailwind CSS 输入文件
│   ├── js/
│   │   └── main.js         # 主 JavaScript 逻辑
│   └── assets/             # 静态资源（图片、图标等）
└── dist/
    └── css/
        └── output.css      # 编译后的 CSS（构建产物）
```

## 开发指南

### 环境配置

1.
*
*安装
Node.js
依赖
**:
```bash
npm install
```

2.
*
*启动
Tailwind
CSS
监听模式
**
（开发时自动编译
CSS）:
```bash
npm run dev
# 或
npm run build:css:watch
```

3.
*
*启动后端服务
**
（另开终端）:
```bash
python api.py
```

4.
*
*访问应用
**:
  -
  前端界面: http://127.0.0.1:8000
  -
  API
  文档: http://127.0.0.1:8000/docs
  -
  健康检查: http://127.0.0.1:8000/health

### 生产构建

```bash
# 构建优化后的 CSS
npm run build

# 启动生产服务
python api.py
```

## 功能模块

### 1. B站视频处理

-
输入
B站视频链接
-
自动下载并转录为文本
-
LLM
润色和导出

### 2. 本地文件上传

-
支持音频/视频文件上传
-
支持格式：MP3,
MP4,
WAV,
M4A
等
-
ASR
识别和文本处理

### 3. 批量处理

-
批量处理多个
B站视频
-
一次性提交多个链接
-
统一导出结果

### 4. 字幕生成

-
为视频自动生成字幕
-
支持
SRT
格式导出
-
支持字幕烧录到视频

## API 端点

所有
API
端点都在
`/api/v1/`
路径下：

-
`POST /api/v1/process/bilibili` -
处理
B站视频
-
`POST /api/v1/process/audio` -
处理音频文件
-
`POST /api/v1/process/batch` -
批量处理
-
`POST /api/v1/process/subtitle` -
生成字幕
-
`GET /api/v1/task/{task_id}` -
查询任务状态
-
`POST /api/v1/task/{task_id}/cancel` -
取消任务
-
`GET /api/v1/download/{task_id}` -
下载结果
-
`POST /api/v1/summarize` -
文本总结

详细
API
文档请访问: http://localhost:8000/docs

## 自定义样式

### 修改 Tailwind 配置

编辑
`tailwind.config.js`:

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          // 自定义主题色
          500: '#3b82f6',
          600: '#2563eb',
        },
      },
    },
  },
}
```

### 添加自定义 CSS

在
`frontend/src/css/input.css`
中添加自定义样式：

```css
@layer components {
  .my-custom-class {
    @apply bg-blue-500 text-white rounded-lg;
  }
}
```

## 状态管理

使用
Alpine.js
的响应式数据系统：

```javascript
Alpine.data('app', () => ({
  // 数据
  currentTab: 'bilibili',
  processing: false,

  // 方法
  async processBilibili() {
    // 处理逻辑
  }
}))
```

## 常见问题

### Q: 样式没有更新？

A:
确保运行了
`npm run dev`
或
`npm run build`
重新编译
CSS。

### Q: 如何添加新功能？

A:

1.
在
`api.py`
添加新的端点
2.
在
`frontend/src/js/main.js`
添加前端逻辑
3.
在
`frontend/src/index.html`
添加
UI
组件

### Q: 如何更改端口？

A:
修改
`.env`
文件中的
`WEB_SERVER_PORT`
配置。

## 部署

### 生产环境部署

1.
构建前端资源:
```bash
npm run build
```

2.
使用
Gunicorn
运行
FastAPI:
```bash
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

3.
配置
Nginx
反向代理（可选）:
```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## 开发工具

### 推荐的 VS Code 扩展

-
Tailwind
CSS
IntelliSense
-
Alpine.js
IntelliSense
-
Prettier -
Code
formatter
-
ESLint

### 调试技巧

1.
*
*查看
API
请求
**:
使用浏览器开发者工具的
Network
选项卡
2.
*
*调试
JavaScript
**:
在
`main.js`
中使用
`console.log()`
或浏览器断点
3.
*
*查看任务状态
**:
访问
`/api/v1/task/{task_id}`
端点

## 贡献指南

欢迎贡献代码！请遵循以下规范：

1.
代码风格：遵循
Prettier
和
ESLint
配置
2.
提交信息：使用语义化提交（Conventional
Commits）
3.
测试：确保修改不影响现有功能

## 许可证

MIT
License
