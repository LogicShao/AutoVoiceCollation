# 文档中心（MVP）

本文档系统按 MVP 原则维护：只保留“当前版本运行和开发必需”的文档。

## 文档清单

1. `docs/deployment/docker.md`：Docker 部署与常见问题
2. `docs/user-guide/api-usage.md`：API 端点与调用示例
3. `docs/development/developer-guide.md`：本地开发、测试和代码结构

## 建议阅读路径

- 普通使用者：先读根目录 `README.md`
- API 调用方：直接读 `docs/user-guide/api-usage.md`
- 维护者：读 `docs/development/developer-guide.md`

## 维护规则

- 文档内容以当前代码行为为准，不保留历史提案型内容。
- 每次接口或命令变化，优先更新对应文档，再合并代码。
- 一个主题只保留一份主文档，避免平行重复。
