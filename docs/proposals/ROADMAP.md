# AutoVoiceCollation 项目路线图

本文档记录项目的功能规划与版本迭代计划。

---

## 版本历史

### 🚀 v1.0.0（当前版本）

- **发布日期**：2024-10-30
- **核心功能**：
  - ✅ B站视频音频下载与转录
  - ✅ 本地音频文件处理
  - ✅ FunASR 多模型支持（Paraformer, SenseVoice）
  - ✅ 多 LLM 提供商集成（DeepSeek, Gemini, Cerebras, Qwen）
  - ✅ 文本润色与总结
  - ✅ PDF/图片/字幕导出
  - ✅ FastAPI RESTful API
  - ✅ Gradio Web UI
  - ✅ Docker 部署支持
  - ✅ 任务历史管理

---

## 开发中（v1.1.0 — 预计 2024-12 月底）

### 🎯 高优先级

- [ ] **异步推理队列**  
  解决 HTTP 请求阻塞问题  
  - 单进程异步任务队列  
  - HTTP 立即响应，推理后台执行  
  - 任务状态实时查询  
  - 参考：[异步推理队列方案](proposals/async-inference-queue.md)

- [ ] **项目结构重构 Phase 2**  
  完成模块化架构  
  - `core/processors/` — 处理器模块  
  - `services/asr/` — ASR 服务封装  
  - `services/llm/` — LLM 服务封装  
  - `api/endpoints/v1/` — API 端点拆分  
  - 参考：[开发建议 - 项目结构改进](proposals/dev-suggestions.md#1-项目结构改进)

- [ ] **配置系统增强**  
  完善 Pydantic v2 配置  
  - 多环境配置支持（dev/test/prod）  
  - 配置热重载  
  - 配置验证增强  
  - 参考：[开发建议 - 配置管理现代化](proposals/dev-suggestions.md#2-配置管理现代化)

### 🔧 中优先级

- [ ] **类型安全增强**  
  全面使用 Pydantic Models  
  - 创建 `Task`, `VideoInfo`, `ProcessResult` 等数据模型  
  - 配置 mypy 类型检查  
  - 参考：[开发建议 - 类型安全增强](proposals/dev-suggestions.md#4-类型安全增强)

- [ ] **测试覆盖率提升**  
  达到 80%+ 覆盖率  
  - 补充单元测试  
  - 搭建集成测试框架  
  - 构建 CI/CD 流水线  
  - 参考：[开发建议 - 测试策略改进](proposals/dev-suggestions.md#5-测试策略改进)

### 📊 低优先级

- [ ] **监控和可观测性**  
  - Prometheus + Grafana  
  - 业务指标监控（任务数、处理时间）  
  - 结构化日志输出  
  - 健康检查增强  
  - 参考：[开发建议 - 监控和可观测性](proposals/dev-suggestions.md#6-监控和可观测性)

---

## 计划中（v1.2.0 — 预计 2025-Q1）

### 性能优化

- [ ] **ONNX Runtime 集成**  
  - 推理加速  
  - 导出 Paraformer ONNX 模型  
  - ONNX Runtime 多线程推理  
  - 性能基准测试

- [ ] **批处理推理**  
  - 提升 GPU 利用率  
  - 累积多个请求批量推理  
  - 动态 batch size 调整

### 功能增强

- [ ] **字幕生成增强**  
  - 多语言字幕支持  
  - 字幕样式自定义  
  - 双语字幕生成

- [ ] **实时语音识别**  
  - WebSocket 流式推理  
  - 实时文本展示

- [ ] **多语言支持**  
  - 英语、日语、韩语识别  
  - 多语言混合识别

### 部署优化

- [ ] **生产部署优化**  
  - Docker 镜像体积优化（多阶段构建）  
  - Kubernetes 配置与 Helm Chart  
  - 资源限制与自动扩缩容  
  - 参考：[开发建议 - 生产部署优化](proposals/dev-suggestions.md#8-生产部署优化)

---

## 未来展望（v2.0.0 — 预计 2025-Q2）

### 架构升级

- [ ] **微服务化**  
  - ASR 服务独立部署  
  - LLM 服务独立部署  
  - 文件处理服务独立部署

- [ ] **分布式任务队列**  
  - Celery + Redis  
  - 支持横向扩展  
  - 任务持久化与重试  
  - 任务优先级与定时任务

### 前端重构

- [ ] **前端现代化**  
  - Vue.js 3 + TypeScript  
  - 响应式设计  
  - 状态管理（Pinia）  
  - 构建优化（Vite）  
  - 参考：[开发建议 - 前端现代化](proposals/dev-suggestions.md#7-前端现代化)

### 高级功能

- [ ] **模型版本管理**  
  - 支持多模型版本切换  
  - A/B 测试支持

- [ ] **用户系统**  
  - 用户认证与授权  
  - 配额管理  
  - 使用统计

- [ ] **API 增强**  
  - GraphQL API  
  - Webhook 通知  
  - 批量操作 API

---

## 长期规划（v3.0.0+）

### 生态扩展

- [ ] **模型训练支持**  
  - 自定义模型微调  
  - 数据标注工具

- [ ] **插件系统**  
  - 自定义处理器插件  
  - LLM 提供商插件  
  - 导出格式插件

- [ ] **云服务集成**  
  - 阿里云 OSS 存储  
  - AWS S3 存储  
  - 云端模型服务

---

## 贡献您的想法

我们欢迎社区提出功能建议与改进意见！

- **提交方式**：
  1. 在 [GitHub Issues](https://github.com/your-repo/issues) 创建 Feature Request
  2. 参与 [GitHub Discussions](https://github.com/your-repo/discussions)
  3. 提交 Pull Request

- **优先级评估标准**：
  - 用户需求强度
  - 技术可行性
  - 实施成本
  - 对现有功能的影响

---

## 版本发布规范

遵循 [语义化版本控制 (SemVer)](https://semver.org/lang/zh-CN/)：

- **主版本号（Major）**：不兼容的 API 变更
- **次版本号（Minor）**：向下兼容的功能新增
- **修订号（Patch）**：向下兼容的问题修复

---

- **最后更新**：2024-12-17  
- **返回**：[提案目录](README.md) | [文档中心](../README.md)

---

✅ **说明**：
- 所有链接均已修正为标准格式，去除多余空格。
- 任务列表统一使用 `- [ ]` 格式，提高一致性。
- 标题层级清晰，避免嵌套混乱。
- 使用 `✅` 和 `🚀` 等图标增强视觉引导，但未过度使用。

> 💡 如需导出为 PDF 或 HTML，也可继续协助。
