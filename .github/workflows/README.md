# GitHub Actions CI/CD 配置说明

本项目使用 GitHub Actions 进行持续集成和测试。

## 最新更新

### v1.2.0 - API 增强功能测试

新增测试覆盖：

- ✅ 时间戳追踪（created_at、completed_at）
- ✅ URL/文件名追踪功能
- ✅ 自动端口查找机制
- ✅ 处理时长计算

### v1.1.0 - 文本总结功能测试

新增测试覆盖：

- ✅ 文本总结端点测试
- ✅ summarize 参数测试
- ✅ 批量处理总结测试

## Workflow 文件

### 1. `test.yml` - 完整测试流程

**触发条件：**

- Push 到 `master`、`main` 或 `develop` 分支
- Pull Request 到这些分支
- 手动触发

**包含的任务：**

#### Job 1: Unit Tests (test)

- **运行环境：** Ubuntu 和 Windows
- **Python 版本：** 3.9, 3.10, 3.11
- **测试内容：** 运行所有单元测试（排除异步测试）
- **覆盖率报告：** 在 Ubuntu + Python 3.11 上生成并上传到 Codecov

#### Job 2: Integration Tests (test-integration)

- **运行环境：** Ubuntu latest
- **触发条件：** 仅在推送到主分支时运行
- **测试内容：** 运行集成测试
- **要求：** 需要配置 API 密钥作为 GitHub Secrets

#### Job 3: Code Quality (lint)

- **运行环境：** Ubuntu latest
- **检查项：**
    - Black（代码格式）
    - isort（导入排序）
    - flake8（代码质量）
    - mypy（类型检查）

### 2. `quick-test.yml` - 快速测试

**触发条件：**

- Pull Request 到主要分支

**特点：**

- 只运行单元测试
- 使用最新的 Python 版本
- 快速反馈（约 2-3 分钟）

## 使用方法

### 基本使用

将代码推送到 GitHub 后，Actions 会自动运行：

```bash
git add .
git commit -m "feat: add new feature"
git push origin your-branch
```

### 查看测试结果

1. 在 GitHub 仓库页面，点击 **Actions** 标签
2. 选择相应的 workflow run
3. 查看测试输出和结果

### 手动触发

在 GitHub Actions 页面：

1. 选择 "Tests" workflow
2. 点击 "Run workflow" 按钮
3. 选择分支并运行

## 配置 GitHub Secrets

集成测试需要 API 密钥，需要在 GitHub 仓库中配置：

1. 进入仓库 **Settings** → **Secrets and variables** → **Actions**
2. 添加以下 secrets：
    - `DEEPSEEK_API_KEY`: DeepSeek API 密钥
    - `GEMINI_API_KEY`: Gemini API 密钥
    - `DASHSCOPE_API_KEY`: DashScope API 密钥（可选）
    - `CEREBRAS_API_KEY`: Cerebras API 密钥（可选）

## Status Badges

在 README.md 中添加状态徽章：

```markdown
![Tests](https://github.com/your-username/AutoVoiceCollation/workflows/Tests/badge.svg)
![Quick Test](https://github.com/your-username/AutoVoiceCollation/workflows/Quick%20Test/badge.svg)
```

## 矩阵测试策略

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest]
    python-version: ['3.9', '3.10', '3.11']
```

这将创建 6 个测试任务（2 个操作系统 × 3 个 Python 版本），确保代码在不同环境下都能正常工作。

## 覆盖率报告

覆盖率报告会在 Ubuntu + Python 3.11 环境中生成：

- **本地查看：** 生成 `coverage.xml` 文件
- **在线查看：** 上传到 Codecov（需要配置 Codecov token）

### 配置 Codecov

1. 在 [Codecov](https://codecov.io/) 注册并关联 GitHub 仓库
2. 获取 Codecov token
3. 在 GitHub Secrets 中添加 `CODECOV_TOKEN`
4. 在 README 中添加覆盖率徽章：

```markdown
[![codecov](https://codecov.io/gh/your-username/AutoVoiceCollation/branch/master/graph/badge.svg)](https://codecov.io/gh/your-username/AutoVoiceCollation)
```

## 测试优化建议

### 1. 缓存依赖

workflow 已配置 pip 缓存，加速安装：

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'
```

### 2. 并行运行

矩阵策略自动实现并行运行，减少总体时间。

### 3. 失败快速反馈

```yaml
strategy:
  fail-fast: false  # 一个任务失败不会取消其他任务
```

### 4. 条件执行

集成测试只在推送到主分支时运行，节省资源：

```yaml
if: github.event_name == 'push' && (github.ref == 'refs/heads/master' || github.ref == 'refs/heads/main')
```

## 本地测试

在提交前本地运行相同的测试：

```bash
# 单元测试
pytest tests/test_api.py -k "not Background" -v

# 覆盖率报告
pytest tests/test_api.py -k "not Background" --cov=api --cov=src --cov-report=html

# 代码格式检查
black --check api.py src/ tests/
isort --check-only api.py src/ tests/
flake8 api.py src/ tests/
```

## 故障排除

### 问题 1: 依赖安装失败

**解决方案：**

- 确保 `requirements.txt` 和 `requirements-test.txt` 文件存在且正确
- 检查依赖版本兼容性

### 问题 2: 测试超时

**解决方案：**

- 在 workflow 中增加 timeout 设置：
  ```yaml
  - name: Run tests
    timeout-minutes: 10
    run: pytest tests/
  ```

### 问题 3: Windows 测试失败

**可能原因：**

- 路径分隔符差异（使用 `os.path.join`）
- 编码问题（指定 `encoding='utf-8'`）

### 问题 4: 集成测试跳过

**原因：** 没有配置必需的 GitHub Secrets

**解决方案：** 按照上面的步骤配置 API 密钥

## 高级配置

### 添加测试报告

使用 `pytest-html` 生成 HTML 报告：

```yaml
- name: Generate HTML report
  if: always()
  run: |
    pytest tests/ --html=report.html --self-contained-html

- name: Upload test report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: test-report
    path: report.html
```

### 定时运行测试

添加 cron 触发器，每天运行一次：

```yaml
on:
  schedule:
    - cron: '0 0 * * *'  # 每天 UTC 00:00
```

### 通知配置

测试失败时发送通知（需要配置 Slack webhook）：

```yaml
- name: Notify on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

## 示例输出

成功运行的输出示例：

```
✓ test_root_endpoint (0.05s)
✓ test_health_endpoint (0.03s)
✓ test_process_bilibili_video_success (0.02s)
✓ test_summarize_success (0.04s)
...
23 passed in 2.34s
```

## 维护建议

1. **定期更新依赖：** 使用 Dependabot 自动更新
2. **监控测试时间：** 如果测试时间过长，考虑拆分或并行化
3. **保持测试覆盖率：** 目标至少 80%
4. **及时修复失败测试：** 不要让破损的测试积累

## 参考资料

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [pytest 文档](https://docs.pytest.org/)
- [Codecov 文档](https://docs.codecov.com/)
