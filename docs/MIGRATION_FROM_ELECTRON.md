# Electron 迁移指南

## 📋 概述

本文档说明了 AutoVoiceCollation 从 Electron 桌面应用架构迁移到 FastAPI Web 应用架构的变更内容。

## ✅ 已完成的变更

### 1. 架构调整

**旧架构（已移除）：**

```
Electron Desktop App
  └─> 启动 Python webui.py
      └─> Gradio UI (端口 7860)
```

**新架构（当前）：**

```
FastAPI Web Server (api.py, 端口 8000)
  ├─> 静态前端 (frontend/)
  │   ├─> HTML/CSS/JS
  │   ├─> Tailwind CSS
  │   └─> Alpine.js
  └─> REST API (/api/v1/*)
      └─> Python 核心 (src/)
```

### 2. 移除的组件

| 组件           | 文件                           | 状态                           |
|--------------|------------------------------|------------------------------|
| Electron 主文件 | `index.js`                   | 已备份至 `archived/index.js.bak` |
| Electron 依赖  | `package.json` 中的 `electron` | 已移除                          |
| 加载动画         | `assets/loading.html`        | 保留（可手动删除）                    |
| node_modules | Electron 相关包                 | 已清理并重装                       |

### 3. 新增的组件

| 组件          | 路径                             | 说明              |
|-------------|--------------------------------|-----------------|
| 前端目录        | `frontend/`                    | 新的 Web 前端架构     |
| HTML 页面     | `frontend/src/index.html`      | 主界面             |
| JavaScript  | `frontend/src/js/main.js`      | 前端逻辑            |
| CSS 源文件     | `frontend/src/css/input.css`   | Tailwind CSS 输入 |
| CSS 构建产物    | `frontend/dist/css/output.css` | 编译后的 CSS        |
| Tailwind 配置 | `tailwind.config.js`           | Tailwind CSS 配置 |
| PostCSS 配置  | `postcss.config.js`            | CSS 处理配置        |
| 前端文档        | `frontend/README.md`           | 前端开发指南          |
| 项目结构说明      | `PROJECT_STRUCTURE.md`         | 完整项目结构          |
| 迁移指南        | `MIGRATION_FROM_ELECTRON.md`   | 本文档             |

### 4. 修改的文件

| 文件             | 主要变更                                  |
|----------------|---------------------------------------|
| `package.json` | 移除 Electron，添加 Tailwind CSS、Alpine.js |
| `api.py`       | 添加静态文件服务、HTML 页面路由                    |
| `.gitignore`   | 已包含必要的忽略规则（无需修改）                      |

## 🚀 使用新架构

### 开发模式

```bash
# 1. 安装前端依赖（首次运行）
npm install

# 2. 启动 Tailwind CSS 监听（终端1）
npm run dev

# 3. 启动后端服务（终端2）
python api.py

# 4. 访问应用
# 浏览器打开: http://127.0.0.1:8000
```

### 生产模式

```bash
# 1. 构建前端资源
npm run build

# 2. 启动服务
python api.py
```

### Docker 部署（推荐）

```bash
# CPU 版本（无需 GPU）
docker compose --profile cpu-only up -d

# GPU 版本
docker compose --profile gpu up -d

# 访问: http://localhost:7861 (CPU) 或 http://localhost:7860 (GPU)
```

## 🔄 功能对比

### 界面访问方式

| 功能   | Electron 方式       | 新方式                         |
|------|-------------------|-----------------------------|
| 启动应用 | `npm start`       | `python api.py`             |
| 访问界面 | 自动打开 Electron 窗口  | 浏览器访问 http://127.0.0.1:8000 |
| 开发调试 | Electron DevTools | 浏览器 DevTools                |

### 功能完整性

所有核心功能都已保留并增强：

- ✅ B站视频处理
- ✅ 本地文件上传
- ✅ 批量处理
- ✅ 字幕生成
- ✅ 任务状态监控
- ✅ 任务取消
- ✅ 结果下载

### 新增功能

- ✅ RESTful API 端点（`/api/v1/*`）
- ✅ 异步任务处理
- ✅ 更好的 UI/UX 设计（Tailwind CSS）
- ✅ 响应式布局
- ✅ 实时任务状态更新

## 📝 迁移检查清单

如果你是从旧版本迁移，请确认以下步骤：

- [ ] 备份旧的 `index.js` 文件（已自动完成）
- [ ] 清理旧的 node_modules（已自动完成）
- [ ] 安装新的前端依赖 `npm install`
- [ ] 构建前端资源 `npm run build`
- [ ] 测试新界面 `python api.py` 并访问 http://127.0.0.1:8000
- [ ] 验证所有功能正常工作
- [ ] 更新启动脚本/快捷方式

## ❓ 常见问题

### Q: 为什么要移除 Electron？

**A:** 主要原因：

1. **简化架构**：减少一层包装，降低复杂度
2. **降低资源消耗**：不需要额外的 Electron 进程
3. **更好的部署**：Web 应用更容易部署和分发
4. **保留 npm 生态**：仍然使用 npm 管理前端工具链
5. **更好的开发体验**：浏览器 DevTools 更强大

### Q: 如何恢复到 Electron 版本？

**A:** 如果需要恢复：

```bash
# 1. 恢复旧的 index.js
cp archived/index.js.bak index.js

# 2. 恢复 Electron 依赖
npm install electron@^38.4.0

# 3. 恢复 package.json 的 start 脚本
# "start": "chcp 65001 && conda activate AutoVoiceCollation && electron ."

# 4. 启动 Electron 应用
npm start
```

### Q: Gradio WebUI 还能用吗？

**A:** 可以！Gradio WebUI (`webui.py`) 仍然保留：

```bash
python webui.py
# 访问: http://127.0.0.1:7860
```

### Q: 前端样式在哪里修改？

**A:**

- **Tailwind 配置**：`tailwind.config.js`
- **自定义 CSS**：`frontend/src/css/input.css`
- **HTML 模板**：`frontend/src/index.html`
- **JavaScript 逻辑**：`frontend/src/js/main.js`

修改后运行 `npm run build` 重新构建。

### Q: API 文档在哪里？

**A:**

- **Swagger UI**：http://127.0.0.1:8000/docs
- **ReDoc**：http://127.0.0.1:8000/redoc
- **API 使用文档**：`docs/API_USAGE.md`

### Q: 如何自定义端口？

**A:** 修改 `.env` 文件：

```env
WEB_SERVER_PORT=8000  # 改为你想要的端口
```

## 🔧 故障排查

### 前端样式没有加载

```bash
# 检查 CSS 是否已构建
ls frontend/dist/css/output.css

# 如果文件不存在，重新构建
npm run build
```

### 静态文件 404 错误

确保 `api.py` 中的静态文件路径正确：

```python
app.mount("/dist", StaticFiles(directory="frontend/dist"), name="dist")
app.mount("/src", StaticFiles(directory="frontend/src"), name="src")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
```

### npm 依赖安装失败

```bash
# 清理缓存并重新安装
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

## 📚 相关文档

- **项目结构**：[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
- **前端开发**：[frontend/README.md](../frontend/README.md)
- **API 文档**：[API_USAGE.md](API_USAGE.md)
- **开发指南**：[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- **Docker 部署**：[DOCKER.md](DOCKER.md)
- **Claude Code 指南**：[CLAUDE.md](../CLAUDE.md)

## 📞 获取帮助

如果遇到问题：

1. 查看相关文档
2. 检查 `logs/AutoVoiceCollation.log`
3. 提交 Issue：https://github.com/LogicShao/AutoVoiceCollation/issues

## 📄 许可证

MIT License - 本迁移不影响原有许可证
