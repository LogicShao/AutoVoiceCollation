# AutoVoiceCollation 项目结构说明

> ✅ 项目版本：v2.0 | 架构已更新至现代 Web 前后端分离模式

---

## 📁 根目录结构

```bash
AutoVoiceCollation/
├── 📄 配置文件
│   ├── .env                      # 环境变量配置（包含 API Keys，不提交到 Git）
│   ├── .env.example              # 环境变量模板
│   ├── .dockerignore             # Docker 构建忽略文件
│   ├── .editorconfig             # 编辑器配置（统一代码风格）
│   ├── .gitignore                # Git 忽略规则
│   ├── package.json              # npm 包管理配置（前端工具链）
│   ├── package-lock.json         # npm 依赖锁定文件
│   ├── postcss.config.js         # PostCSS 配置（CSS 处理）
│   ├── tailwind.config.js        # Tailwind CSS 配置
│   ├── pytest.ini                # pytest 测试配置
│   ├── requirements.txt          # Python 依赖（生产环境）
│   └── requirements-test.txt     # Python 测试依赖

├── 📄 文档
│   ├── README.md                 # 项目主文档
│   ├── CLAUDE.md                 # Claude Code 开发指南
│   ├── LICENSE                   # MIT 许可证
│   └── PROJECT_STRUCTURE.md      # 本文件：项目结构说明

├── 🐳 Docker 部署
│   ├── Dockerfile                # GPU 版本 Dockerfile
│   ├── Dockerfile.cpu            # CPU 版本 Dockerfile
│   ├── Dockerfile.proxy          # 代理版本 Dockerfile
│   └── docker-compose.yml        # Docker Compose 配置

├── 🎨 前端（新架构）
│   └── frontend/
│       ├── README.md             # 前端开发文档
│       ├── src/
│       │   ├── index.html        # 主页面入口
│       │   ├── css/
│       │   │   └── input.css     # Tailwind CSS 输入文件
│       │   ├── js/
│       │   │   └── main.js       # 主 JavaScript 逻辑
│       │   └── assets/           # 图片、图标等静态资源
│       └── dist/                 # 构建产物（自动生成，不提交）
│           └── css/
│               └── output.css    # 编译后的 CSS 文件

├── 🐍 Python 后端
│   ├── main.py                   # CLI 入口脚本
│   ├── api.py                    # FastAPI REST API 服务
│   ├── webui.py                  # Gradio WebUI（可选，兼容旧版）
│   └── src/
│       ├── config.py             # 配置管理（Pydantic v2）
│       ├── core_process.py       # 核心处理流程编排
│       ├── extract_audio_text.py # ASR 识别核心
│       ├── bilibili_downloader.py # B站视频下载器
│       ├── subtitle_generator.py # 字幕生成模块
│       ├── task_manager.py       # 任务状态管理
│       ├── device_manager.py     # 设备（GPU/CPU）管理
│       ├── logger.py             # 日志系统（结构化输出）
│       └── text_arrangement/
│           ├── query_llm.py      # LLM 统一接口
│           ├── polish_by_llm.py  # LLM 文本润色
│           ├── split_text.py     # 文本分段处理
│           └── summary_by_llm.py # LLM 文本摘要

├── 🧪 测试
│   └── tests/
│       ├── conftest.py           # pytest fixtures
│       ├── test_config.py        # 配置测试
│       ├── test_device_manager.py # 设备管理测试
│       ├── test_logger.py        # 日志系统测试
│       ├── test_task_manager.py  # 任务管理测试
│       └── test_api.py           # API 端点集成测试

├── 📚 文档目录
│   └── docs/
│       ├── API_USAGE.md          # API 使用文档
│       ├── DEVELOPER_GUIDE.md    # 开发者指南
│       ├── DOCKER.md             # Docker 部署指南
│       ├── DOCKER_NETWORK_TROUBLESHOOTING.md  # Docker 网络问题完整解决方案
│       └── DOCKER_FONT_FIX.md    # Docker 字体问题修复

├── 🔧 脚本工具
│   └── scripts/
│       ├── clear_output.py       # 清理输出目录
│       ├── docker-start.sh       # Docker 启动脚本（Linux/Mac）
│       ├── verify-font.sh        # 字体验证脚本
│       └── test-mirrors.sh       # 镜像源测试脚本

├── 📦 静态资源
│   └── assets/
│       ├── icon.svg              # 应用图标
│       └── loading.html          # 加载动画（旧 Electron 使用）

├── 🗄️ 运行时目录（自动生成，不提交到 Git）
│   ├── out/                      # 输出文件（PDF/ZIP/文本）
│   ├── download/                 # 下载缓存
│   ├── temp/                     # 临时文件
│   ├── logs/                     # 日志文件
│   ├── models/                   # 模型缓存
│   └── node_modules/             # npm 依赖（前端构建使用）

└── 📦 归档（旧文件备份）
    └── archived/
        └── index.js.bak          # 旧的 Electron 主文件（已移除）
```

---

## 🚀 快速启动

### ✅ 前端开发模式（推荐）

```bash
# 安装前端依赖
npm install

# 启动 Tailwind CSS 监听（终端1）
npm run dev

# 启动后端服务（终端2）
python api.py

# 访问 Web 界面
http://127.0.0.1:8000
```

### ✅ 传统 CLI 模式

```bash
python main.py
```

### ✅ Gradio WebUI 模式（可选，兼容旧版）

```bash
python webui.py
```

### ✅ Docker 部署

```bash
# CPU 版本（推荐）
docker compose --profile cpu-only up -d

# GPU 版本（需支持 CUDA）
docker compose --profile gpu up -d
```

---

## 📝 重要说明

### ❌ 已移除的组件

- **Electron 桌面应用**  
  - 已移除，备份至 `archived/` 目录  
  - 原因：简化架构，避免维护桌面打包复杂性  
  - 迁移方案：使用浏览器访问 `http://127.0.0.1:8000` 即可

### ✅ 新增的组件

- **FastAPI + 前端静态页面**  
  - 基于原生 HTML/CSS/JS + Tailwind CSS 构建
- **npm 工具链**  
  - 用于前端构建与开发
- **Alpine.js**  
  - 轻量级前端交互框架（替代 jQuery）

---

## 🔄 架构变更对比

### 旧架构（已废弃）
```
Electron → 启动 python webui.py → Gradio UI
```

### 新架构（当前）
```
浏览器 → FastAPI (api.py) → 静态前端 (frontend/) + REST API
                          ↓
                       Python 核心 (src/)
```

> ✅ 优势：更轻量、更易部署、更符合现代 Web 标准

---

## 📚 相关文档

| 类别 | 文档路径 | 说明 |
|------|----------|------|
| 前端开发 | `frontend/README.md` | 前端构建与开发指南 |
| API 文档 | `docs/API_USAGE.md` | 所有 API 端点说明 |
| 开发指南 | `docs/DEVELOPER_GUIDE.md` | 代码规范、类型检查、CI/CD |
| Docker 部署 | `docs/DOCKER.md` | 详细部署步骤 |
| Claude Code 指南 | `CLAUDE.md` | 项目设计与建议 |

---

## 🤝 贡献指南

欢迎贡献代码！请遵循以下流程：

1. Fork 项目  
2. 创建功能分支（如 `feat/new-feature`）  
3. 提交变更并添加测试  
4. 推送到你的仓库  
5. 发起 Pull Request  

> 📌 请确保通过 `pytest` 和 `mypy` 检查，并更新相关文档。

---

## 📄 许可证

MIT License —— 详见 `LICENSE` 文件

---

- **最后更新**：2025-12-17  
- **文档版本**：2.0  
- **状态**：✅ 已发布，适用于新成员入职与团队协作

✅ 本文档已优化，适合用于：
- 项目初始化
- 团队协作
- CI/CD 配置
- 新成员培训
