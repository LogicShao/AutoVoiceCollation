# Ruff 代码质量检查使用指南

本项目使用 [Ruff](https://docs.astral.sh/ruff/) 进行代码质量检查和格式化。

## 🚀 快速开始

### 手动运行检查

```bash
# Windows
scripts\lint.bat check

# Linux/Mac
./scripts/lint.sh check
```

### 自动修复问题

```bash
# Windows
scripts\lint.bat all

# Linux/Mac
./scripts/lint.sh all
```

---

## 📋 常用命令

| 命令 | Windows | Linux/Mac | 说明 |
|------|---------|-----------|------|
| **仅检查** | `scripts\lint.bat check` | `./scripts/lint.sh check` | 检查代码问题但不修复 |
| **自动修复** | `scripts\lint.bat fix` | `./scripts/lint.sh fix` | 自动修复可修复的问题 |
| **格式化** | `scripts\lint.bat format` | `./scripts/lint.sh format` | 格式化代码 |
| **完整检查** | `scripts\lint.bat all` | `./scripts/lint.sh all` | 检查+修复+格式化 |

### 原生 Ruff 命令

```bash
# 检查代码问题
ruff check .

# 自动修复问题
ruff check --fix .

# 格式化代码
ruff format .

# 检查格式（不修改）
ruff format --check .

# 显示统计信息
ruff check . --statistics

# 检查特定文件/目录
ruff check src/core/
ruff check src/api/middleware.py
```

---

## ⚙️ 自动化检查

### 1. Git Pre-commit Hook（提交前检查）

已配置 Git hook，每次 `git commit` 时自动运行 Ruff 检查。

**特性：**
- ✅ 自动检查暂存的 Python 文件
- ✅ 检查失败会阻止提交
- ✅ 提供修复建议

**跳过检查：**
```bash
git commit --no-verify -m "commit message"
```

### 2. GitHub Actions（CI/CD）

每次推送代码或创建 PR 时，GitHub Actions 会自动运行：
- Ruff lint 检查
- Ruff 格式检查
- Mypy 类型检查（可选）

**查看结果：** GitHub → Actions 标签

### 3. PyCharm 集成（IDE）

#### 方法1：配置外部工具

1. File → Settings → Tools → External Tools
2. 点击 "+" 添加新工具
3. 配置：
   - **Name:** Ruff Check
   - **Program:** `ruff`
   - **Arguments:** `check --fix $FilePath$`
   - **Working directory:** `$ProjectFileDir$`

4. 重复以上步骤添加 "Ruff Format"：
   - **Arguments:** `format $FilePath$`

#### 方法2：保存时自动运行

1. File → Settings → Tools → File Watchers
2. 点击 "+" → Custom
3. 配置：
   - **Name:** Ruff Auto-fix
   - **File type:** Python
   - **Program:** `ruff`
   - **Arguments:** `check --fix $FilePath$`
   - **Working directory:** `$ProjectFileDir$`

---

## 📝 配置文件

### ruff.toml

位置：项目根目录 `ruff.toml`

**主要配置：**
```toml
line-length = 100           # 每行最大字符数
target-version = "py311"    # 目标 Python 版本

[lint]
select = ["E", "W", "F", "I", "N", "UP", "B"]  # 启用的规则
ignore = ["E501", "E402"]                       # 忽略的规则
```

**自定义规则：**
编辑 `ruff.toml` 文件，参考 [Ruff 规则文档](https://docs.astral.sh/ruff/rules/)

---

## 🔍 常见问题

### Q: 如何忽略某一行的检查？

```python
# 忽略整行
result = some_long_function()  # noqa

# 忽略特定规则
result = some_long_function()  # noqa: E501

# 忽略多个规则
result = some_long_function()  # noqa: E501, W503
```

### Q: 如何忽略整个文件？

在文件顶部添加：
```python
# ruff: noqa
```

### Q: Pre-commit hook 不工作？

**Windows 用户：** Git 可能无法执行 bash 脚本，请手动运行：
```bash
scripts\lint.bat check
```

或在提交前手动检查：
```bash
ruff check . && ruff format --check .
```

### Q: 如何查看所有可用规则？

```bash
ruff rule --all
```

### Q: 格式化冲突怎么办？

Ruff 格式化优先级高于 lint 检查。如果冲突：
1. 先运行 `ruff format .`
2. 再运行 `ruff check --fix .`

---

## 📊 代码质量标准

项目要求：
- ✅ 所有 PR 必须通过 Ruff lint 检查
- ✅ 所有 PR 必须通过 Ruff 格式检查
- ⚠️  Mypy 类型检查为建议性（不强制）

**建议工作流：**
```bash
# 1. 编写代码
# 2. 运行完整检查和修复
scripts\lint.bat all  # Windows
./scripts/lint.sh all # Linux/Mac

# 3. 提交代码
git add .
git commit -m "feat: add new feature"  # 自动触发 pre-commit hook
```

---

## 🎯 最佳实践

1. **编码时：** 配置 IDE 实时检查
2. **提交前：** 运行 `scripts/lint.bat all` 确保通过
3. **PR 前：** 检查 GitHub Actions 结果
4. **代码审查：** 关注 Ruff 报告的问题

---

## 📚 参考资料

- [Ruff 官方文档](https://docs.astral.sh/ruff/)
- [Ruff 规则列表](https://docs.astral.sh/ruff/rules/)
- [Ruff vs Black/Flake8/isort](https://docs.astral.sh/ruff/faq/#how-does-ruff-compare-to-flake8)
