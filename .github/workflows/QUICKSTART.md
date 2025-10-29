# GitHub Actions 快速入门

## 立即开始使用 GitHub Actions

### 步骤 1: 确认文件已创建

项目中已包含以下 workflow 文件：

```
.github/
└── workflows/
    ├── test.yml           # 完整测试流程
    ├── quick-test.yml     # 快速测试
    └── README.md          # 详细文档
```

### 步骤 2: 推送到 GitHub

```bash
# 添加 workflow 文件
git add .github/workflows/

# 提交
git commit -m "ci: add GitHub Actions workflows for testing"

# 推送到 GitHub
git push origin master
```

### 步骤 3: 查看测试结果

1. 打开你的 GitHub 仓库
2. 点击顶部的 **Actions** 标签
3. 你会看到 workflows 自动运行

## 快速测试命令对照

| 本地命令                          | GitHub Actions |
|-------------------------------|----------------|
| `pytest tests/test_api.py -v` | ✅ 自动运行         |
| `pytest --cov=api`            | ✅ 自动生成覆盖率      |
| `flake8 api.py`               | ✅ 自动代码检查       |

## 什么时候会运行测试？

### test.yml 会在以下情况运行：

- ✅ 推送代码到 `master`、`main` 或 `develop` 分支
- ✅ 创建或更新 Pull Request
- ✅ 手动触发（在 Actions 页面）

### quick-test.yml 会在以下情况运行：

- ✅ 创建或更新 Pull Request（仅此场景）

## 查看测试状态

### 在 PR 页面

当你创建 Pull Request 时，测试状态会显示在 PR 页面底部：

```
✓ test / Run Unit Tests (ubuntu-latest, 3.11) — Passed
✓ test / Run Unit Tests (windows-latest, 3.11) — Passed
✓ quick-test / Quick Unit Tests — Passed
```

### 在提交历史

每个提交旁边会显示测试状态：

- ✅ 绿色勾号 = 测试通过
- ❌ 红色叉号 = 测试失败
- 🟡 黄色圆点 = 测试进行中

## 配置 API 密钥（集成测试）

如果需要运行集成测试，配置 GitHub Secrets：

1. 进入仓库 **Settings**
2. 点击左侧 **Secrets and variables** → **Actions**
3. 点击 **New repository secret**
4. 添加：
    - Name: `DEEPSEEK_API_KEY`
    - Value: 你的 API 密钥
5. 点击 **Add secret**

重复上述步骤添加其他密钥（GEMINI_API_KEY 等）。

## 添加状态徽章到 README

在你的 `README.md` 中添加：

```markdown
# AutoVoiceCollation

![Tests](https://github.com/YOUR_USERNAME/AutoVoiceCollation/workflows/Tests/badge.svg)
![Quick Test](https://github.com/YOUR_USERNAME/AutoVoiceCollation/workflows/Quick%20Test/badge.svg)

自动语音识别和文本整理工具
```

**记得替换 `YOUR_USERNAME` 为你的 GitHub 用户名！**

## 常见问题

### Q: 测试失败了怎么办？

**A:**

1. 点击失败的测试查看详细日志
2. 在本地运行相同的测试命令
3. 修复问题后重新推送

```bash
# 本地测试
pytest tests/test_api.py -k "not Background" -v

# 修复后推送
git add .
git commit -m "fix: resolve test failures"
git push
```

### Q: 我只想运行快速测试，不想运行完整测试？

**A:** 创建草稿 PR（Draft Pull Request）：

```bash
# 推送到新分支
git checkout -b feature/my-feature
git push origin feature/my-feature

# 在 GitHub 上创建 Draft PR
# Draft PR 只会触发 quick-test.yml
```

### Q: 如何跳过某次提交的 CI？

**A:** 在提交信息中添加 `[skip ci]` 或 `[ci skip]`：

```bash
git commit -m "docs: update README [skip ci]"
```

### Q: 测试花费时间太长？

**A:** 目前的配置已经优化：

- 使用依赖缓存（加速 50%）
- 并行运行多个任务
- 平均运行时间：2-3 分钟（单元测试）

## 成本和配额

### GitHub Actions 免费额度：

- **公开仓库：** 无限制
- **私有仓库：** 每月 2000 分钟（约 33 小时）

### 当前配置消耗（每次运行）：

- Quick Test: ~3 分钟
- Full Tests: ~15 分钟（6 个并行任务 × 2.5 分钟）

## 下一步

1. ✅ **推送代码** - 立即看到 Actions 运行
2. 📊 **配置 Codecov** - 获取覆盖率报告
3. 🎯 **添加更多测试** - 提高代码质量
4. 🚀 **添加部署流程** - 自动化部署

## 需要帮助？

查看详细文档：

- `.github/workflows/README.md` - 完整配置说明
- `tests/README.md` - 测试文档
- [GitHub Actions 官方文档](https://docs.github.com/en/actions)

---

现在就推送代码，看看 GitHub Actions 的神奇之处吧！🎉
