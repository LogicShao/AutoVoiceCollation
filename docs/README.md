# AutoVoiceCollation 文档中心

*
*项目
**:
音视频转文本系统（ASR +
LLM）  
*
*主文档
**: [CLAUDE.md](../CLAUDE.md) |
*
*快速开始
**: [README.md](../README.md)

---

## 📚 文档导航

### 🎯 用户指南

- [API 使用指南](user-guide/api-usage.md) -
  RESTful
  API
  端点和使用示例

### 🚀 部署文档

- [Docker 部署指南](deployment/docker.md) -
  完整的
  Docker
  部署说明
-
*
*Docker
故障排查
**:
  - [网络问题](deployment/docker/troubleshooting-network.md)
  - [字体问题](deployment/docker/troubleshooting-font.md)
  - [容器崩溃](deployment/docker/troubleshooting-crash.md)

### 💻 开发文档

- [开发者指南](development/developer-guide.md) -
  环境配置、编码规范、贡献流程
- [项目结构](development/project-structure.md) -
  代码库组织和模块说明
- [日志系统](development/logging.md) -
  日志配置和使用规范

### 🏗️ 架构设计

- [异常处理架构](architecture/exception-handling.md) -
  统一异常处理系统
- [处理历史管理](architecture/process-history.md) -
  任务历史记录系统
- [Web UI 历史集成](architecture/web-ui-history-integration.py) -
  界面实现代码

### 📝 实施记录
按时间倒序排列：
- [2024-12-17 文档重组](implementation/2024-12-17-docs-restructure.md)
- [2024-12-17 项目重构 Phase 1](implementation/2024-12-17-project-restructure-phase1.md)
- [2024-12-16 配置修复](implementation/2024-12-16-config-fix.md)
- [历史实施总结](implementation/implementation-summary.md)

### 💡 提案和路线图

- [项目路线图](proposals/ROADMAP.md) -
  版本规划（v1.0 →
  v3.0+）
- [开发改进建议](proposals/dev-suggestions.md) -
  完整的架构优化建议
- [异步推理队列方案](proposals/async-inference-queue.md) -
  解决
  HTTP
  阻塞问题

---

## 🔍 快速查找

| 我是...   | 我想...        | 文档链接                                    |
|---------|--------------|-----------------------------------------|
| **用户**  | 调用 API       | [API 使用指南](user-guide/api-usage.md)     |
| **管理员** | 部署系统         | [Docker 部署指南](deployment/docker.md)     |
| **管理员** | 解决 Docker 问题 | [故障排查目录](deployment/docker/)            |
| **开发者** | 贡献代码         | [开发者指南](development/developer-guide.md) |
| **架构师** | 了解系统设计       | [开发改进建议](proposals/dev-suggestions.md)  |

---

*
*最后更新
**:
2024-12-17  
*
*问题反馈
**: [GitHub Issues](https://github.com/your-repo/issues)
