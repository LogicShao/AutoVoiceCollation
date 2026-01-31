# 遗留模块重构迁移计划

- **创建日期**：2025-12-17
- **最后更新**：2026-01-30
- **状态**：🔄 进行中（部分已完成）
- **优先级**：中等
- **预计工期**：剩余 1–2 周  

---

## 📊 执行摘要

本文档规划了将 `src/` 根目录下的遗留模块迁移到新架构的完整方案。项目已完成配置系统重构（Phase 1），本计划为 **Phase 2**，目标是进一步提升代码组织性、可维护性和模块职责清晰度。

> ✅ 当前版本：v2.0（模块化架构） | 迁移进度：约 70% 完成

---

## 🎯 迁移目标

1. **清理根目录**：移除 `src/` 下的冗余模块，归入合理子目录。
2. **统一架构**：所有模块遵循新命名与层级规范。
3. **保持兼容**：通过向后兼容层确保现有代码持续运行。
4. **改善可维护性**：提高代码可发现性、职责分离与测试覆盖率。

---

## 📋 当前状态分析

### ✅ 已完成的重构（2026-01-30 状态）

- ✅ 配置系统：`src/config.py` → `src/utils/config/`（已完成）
- ✅ 核心处理器：已迁移至 `src/core/processors/`（已完成）
- ✅ 服务层：组织到 `src/services/`（已完成）
- ✅ 日志系统：`src/logger.py` → `src/utils/logging/logger.py`（已完成）
- ✅ 设备管理：`src/device_manager.py` → `src/utils/device/device_manager.py`（已完成）
- ✅ 任务管理：`src/task_manager.py` → `src/utils/helpers/task_manager.py`（已完成）
- ✅ 异常系统：创建统一的异常体系 `src/core/exceptions/`（已完成）
- ✅ API 层：组织到 `src/api/`（已完成）
- ✅ 工具类：组织到 `src/utils/`（已完成）

### 📊 迁移完成状态（2026-01-30）

| 遗留模块                     | 新位置                                     | 状态 | 完成日期 | 备注 |
|--------------------------|---------------------------------------|------|----------|------|
| `src/config.py`          | `src/utils/config/`                   | ✅ 完成 | 2025-12 | Pydantic v2 配置系统 |
| `src/logger.py`          | `src/utils/logging/logger.py`         | ✅ 完成 | 2025-12 | 结构化日志系统 |
| `src/device_manager.py`  | `src/utils/device/device_manager.py`  | ✅ 完成 | 2025-12 | 设备自动检测 |
| `src/task_manager.py`    | `src/utils/helpers/task_manager.py`   | ✅ 完成 | 2025-12 | 任务取消支持 |
| `src/Timer.py`           | `src/utils/helpers/timer.py`          | ✅ 完成 | 2025-12 | 计时器工具 |
| `src/output_file_manager.py` | `src/core/export/file_manager.py`  | ✅ 完成 | 2025-12 | 输出文件管理 |
| `src/process_history.py` | `src/core/history/manager.py`         | ✅ 完成 | 2025-12 | 处理历史管理 |
| `src/bilibili_downloader.py` | `src/services/download/bilibili_downloader.py` | ✅ 完成 | 2025-12 | B站下载服务 |
| `src/extract_audio_text.py` | `src/services/asr/`                  | ✅ 完成 | 2025-12 | ASR 服务抽象层 |
| `src/subtitle_generator.py` | `src/services/subtitle/generator.py` | ✅ 完成 | 2025-12 | 字幕生成服务 |
| `src/core_process.py`    | `src/core/processors/`                | ✅ 完成 | 2025-12 | 处理器架构 |
| `src/core_process_utils.py` | 分散至相关模块                        | ✅ 完成 | 2025-12 | 功能拆分 |
| **遗留模块清理**          | **src/ 根目录已清理**                  | ✅ 完成 | 2026-01 | 仅保留 `__init__.py` |

### 📊 使用情况统计

```text
高频使用 (10+ 引用):
  - logger.py (41 处引用)
  - task_manager.py (15+ 处引用)
  - bilibili_downloader.py (12+ 处引用)
  - extract_audio_text.py (10+ 处引用)

中频使用 (5–10 处引用):
  - subtitle_generator.py (8 处引用)
  - process_history.py (7 处引用)
  - output_file_manager.py (6 处引用)

低频使用 (<5 处引用):
  - device_manager.py (3 处引用)
  - Timer.py (2 处引用)
```

---

## 🗺️ 迁移路线图

### Phase 2.1: 低风险模块迁移（第 1 周）

#### 1.1 `Timer.py`

- **新位置**：`src/utils/helpers/timer.py`
- **迁移策略**：
  - [x] 新模块已存在
  - [ ] 更新所有导入（约 2 处）
  - [ ] 删除旧文件并添加废弃警告
```python
# 旧导入
from src.Timer import Timer

# 新导入
from src.utils.helpers.timer import Timer
```
- **预计工作量**：0.5 天

#### 1.2 `bilibili_downloader.py`

- **新位置**：`src/services/download/bilibili_downloader.py`
- **迁移策略**：
  - [ ] 创建 `src/services/download/` 目录
  - [ ] 移动文件并更新内部导入
  - [ ] 在旧位置创建向后兼容层
  - [ ] 逐步更新 12+ 处引用
```python
# 向后兼容层 (src/bilibili_downloader.py)
"""
⚠️ 已废弃：请使用 src.services.download.bilibili_downloader

此模块将在 v2.0.0 中移除
"""
from src.services.download.bilibili_downloader import *

__all__ = [...]
```
- **预计工作量**：1 天

---

### Phase 2.2: 中风险模块迁移（第 2 周）

#### 2.1 `device_manager.py`

- **新位置**：`src/utils/device/device_manager.py`
- **当前问题**：仍被 `services/asr/factory.py` 等使用
- **迁移策略**：
  - [ ] 确认功能一致性
  - [ ] 更新 3 处引用
  - [ ] 删除旧文件，添加重定向
- **预计工作量**：0.5 天

#### 2.2 `subtitle_generator.py`

- **新位置**：`src/services/subtitle/generator.py`
- **迁移策略**：
  - [ ] 创建 `src/services/subtitle/` 目录
  - [ ] 拆分逻辑：
    - 核心生成 → `generator.py`
    - 配置 → `config.py`
    - 辅助函数 → `utils.py`
  - [ ] 添加向后兼容层
  - [ ] 更新 8 处引用
- **预计工作量**：2 天

#### 2.3 `output_file_manager.py`

- **新位置**：`src/core/export/file_manager.py`
- **迁移策略**：
  - [ ] 创建 `src/core/export/` 目录
  - [ ] 移动并重构代码
  - [ ] 添加向后兼容层
  - [ ] 更新 6 处引用
- **预计工作量**：1.5 天

#### 2.4 `process_history.py`

- **新位置**：`src/core/history/manager.py`
- **迁移策略**：
  - [ ] 创建 `src/core/history/` 目录
  - [ ] 移动文件
  - [ ] 更新相关测试
  - [ ] 添加向后兼容层
  - [ ] 更新 7 处引用
- **预计工作量**：1.5 天

---

### Phase 2.3: 高风险模块迁移（第 3 周）

#### 3.1 `task_manager.py`

- **新位置**：`src/utils/helpers/task_manager.py`
- **当前问题**：广泛使用（15+ 处引用）
- **迁移策略**：
  - [ ] 确认功能完全一致
  - [ ] 编写自动化脚本批量更新导入
  - [ ] 分批更新：
    - Batch 1：测试文件
    - Batch 2：核心处理器
    - Batch 3：入口文件
  - [ ] 每批次后运行完整测试
  - [ ] 最后删除旧文件
- **预计工作量**：2 天

#### 3.2 `logger.py`

- **新位置**：`src/utils/logging/logger.py`
- **当前问题**：最广泛使用（41 处引用）
- **迁移策略**：
  - [ ] 确保兼容性
  - [ ] 编写自动化迁移脚本
  - [ ] 分 5 批次逐步迁移：
    - Batch 1：测试文件
    - Batch 2：`utils/` 和 `services/`
    - Batch 3：`core/`
    - Batch 4：`text_arrangement/`
    - Batch 5：根级别文件
  - [ ] 每批次后运行测试
  - [ ] 最终删除旧文件
- **预计工作量**：3 天

#### 3.3 `extract_audio_text.py`

- **建议方案 A**：`src/services/asr/transcriber.py`
- **建议方案 B**：`src/core/audio/extractor.py`
- **迁移策略**：
  - [ ] 团队讨论确定最佳路径
  - [ ] 重构代码以适应新结构
  - [ ] 添加向后兼容层
  - [ ] 逐步更新 10+ 处引用
- **预计工作量**：2 天

---

### Phase 2.4: 清理与优化（第 3 周末）

#### 4.1 `core_process.py`

- **处理方案**：保留为永久向后兼容层
- **原因**：
  - 作为主要公共 API 入口
  - 避免破坏现有代码
  - 提供清晰的导入路径
- **优化建议**：
  - [ ] 添加详细文档
  - [ ] 明确标注为公共 API
  - [ ] 添加版本警告（未来废弃提示）

#### 4.2 `core_process_utils.py`

- **处理方案**：分散到相关模块
- **迁移策略**：
  - [ ] 分析函数用途
  - [ ] 按逻辑迁移至对应模块
  - [ ] 在原位置创建导入重定向
  - [ ] 更新所有引用
- **预计工作量**：1.5 天

---

## 🛠️ 实施指南

### 通用迁移流程

每个模块遵循以下标准流程：

#### 步骤 1：准备
```bash
# 1. 创建功能分支
git checkout -b refactor/migrate-MODULE_NAME

# 2. 分析使用情况
rg "from src.MODULE_NAME|import src.MODULE_NAME" --type py -l

# 3. 运行基准测试
pytest tests/ -v --tb=short
```

#### 步骤 2：创建新模块
```bash
# 1. 创建目标目录
mkdir -p src/NEW/LOCATION

# 2. 移动或复制文件
cp src/OLD_MODULE.py src/NEW/LOCATION/new_module.py

# 3. 更新内部导入
# 编辑 src/NEW/LOCATION/new_module.py
```

#### 步骤 3：创建向后兼容层
```python
# src/OLD_MODULE.py
"""
⚠️ 已废弃

请使用 src.NEW.LOCATION.new_module

此模块将在 v2.0.0 中移除

迁移指南: docs/migration/MODULE_NAME.md
"""
import warnings
from src.NEW.LOCATION.new_module import *

warnings.warn(
    "src.OLD_MODULE 已废弃，请使用 src.NEW.LOCATION.new_module",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [...]  # 导出所有公共接口
```

#### 步骤 4：更新导入
```python
# scripts/migrate_imports.py
import re
import sys
from pathlib import Path

def update_imports(file_path, old_import, new_import):
    content = file_path.read_text(encoding='utf-8')
    updated = re.sub(
        rf'from {old_import}',
        f'from {new_import}',
        content
    )
    if updated != content:
        file_path.write_text(updated, encoding='utf-8')
        return True
    return False

# 示例调用
for py_file in Path('src').rglob('*.py'):
    update_imports(py_file, 'src.OLD_MODULE', 'src.NEW.LOCATION.new_module')
```

#### 步骤 5：测试验证
```bash
# 1. 单元测试
pytest tests/ -v

# 2. 集成测试
pytest tests/ -m integration -v

# 3. 手动烟雾测试
python -c "from src.NEW.LOCATION.new_module import *; print('Import OK')"
```

#### 步骤 6：文档更新
- [ ] 更新 `CHANGELOG.md`
- [ ] 更新 `docs/DEVELOPER_GUIDE.md`
- [ ] 创建迁移指南：`docs/migration/MODULE_NAME.md`
- [ ] 更新 `CLAUDE.md` 中的路径引用

#### 步骤 7：提交与审查
```bash
git add .
git commit -m "
refactor: migrate OLD_MODULE to src/NEW/LOCATION

- Move OLD_MODULE.py to src/NEW/LOCATION/new_module.py
- Add backward compatibility layer
- Update N imports across codebase
- Add deprecation warnings

BREAKING CHANGE: OLD_MODULE will be removed in v2.0.0

Refs: #ISSUE_NUMBER
"

git push origin refactor/migrate-MODULE_NAME
```

---

## 📝 向后兼容策略

### 兼容层保留期限

| 版本范围       | 兼容层状态         |
|----------------|--------------------|
| v1.x           | 保留，仅显示警告   |
| v2.0.0+        | 移除，强制更新     |

### 废弃警告级别
```python
# Level 1: 信息性（v1.5.0 - v1.7.0）
warnings.warn("Module moved, please update imports", FutureWarning)

# Level 2: 推荐更新（v1.8.0 - v1.9.0）
warnings.warn("Will be removed in v2.0.0", DeprecationWarning)

# Level 3: 即将移除（v1.10.0+）
warnings.warn("URGENT: Will be removed in next major version", DeprecationWarning)
```

---

## 🧪 测试策略

每个迁移模块需通过以下测试：

- [ ] 单元测试（100% 通过）
- [ ] 集成测试（通过）
- [ ] 导入测试（新旧路径均能导入）
- [ ] 功能测试（无回归）
- [ ] 性能测试（<5% 下降）
- [ ] 文档测试（示例可运行）

### 自动化测试脚本
```python
# tests/test_migration.py
"""测试模块迁移的向后兼容性"""
import pytest
import warnings

def test_old_import_with_warning():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from src.OLD_MODULE import SomeClass

        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "已废弃" in str(w[0].message)

        obj = SomeClass()
        assert obj is not None

def test_new_import_no_warning():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from src.NEW.LOCATION.new_module import SomeClass

        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 0

def test_functionality_identical():
    from src.OLD_MODULE import function_a as old_func
    from src.NEW.LOCATION.new_module import function_a as new_func
    assert old_func is new_func
```

---

## 📊 进度跟踪

| Milestone | 任务 | 状态 |
|---------|------|------|
| ✅ Milestone 1: 低风险模块（Week 1） | `Timer.py`、`bilibili_downloader.py` 迁移完成 | □ |
| ✅ Milestone 2: 中风险模块（Week 2） | `device_manager.py`、`subtitle_generator.py`、`output_file_manager.py`、`process_history.py` 完成 | □ |
| ✅ Milestone 3: 高风险模块（Week 3） | `task_manager.py`、`logger.py`、`extract_audio_text.py` 完成 | □ |
| ✅ Milestone 4: 清理收尾（Week 3 末） | 所有模块迁移完成，文档更新，发布 v1.5.0-rc1 | □ |

---

## 🚨 风险管理

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 大量导入导致合并冲突 | 高 | 中 | 分小批次迁移，及时合并 |
| 遗漏隐式依赖 | 中 | 中 | 代码审查 + 全面测试 |
| 性能回归 | 中 | 低 | 基准测试 |
| 破坏第三方集成 | 高 | 低 | 保留兼容层至 v2.0 |
| 文档不同步 | 低 | 中 | 每次迁移包含文档更新 |

### 回滚计划
```bash
# 快速回滚
git revert <commit-hash>

# 或回滚整个分支
git reset --hard origin/master
```

---

## 📚 相关文档

### 创建的新文档

- [ ] `docs/migration/timer-migration.md`
- [ ] `docs/migration/bilibili-downloader-migration.md`
- [ ] `docs/migration/logger-migration.md`
- [ ] `docs/architecture/new-structure.md`

### 更新的文档

- [ ] `docs/DEVELOPER_GUIDE.md` —— 新结构说明
- [ ] `CLAUDE.md` —— 路径引用更新
- [ ] `README.md` —— 导入示例更新
- [ ] `CHANGELOG.md` —— 记录变更

---

## 🎯 成功标准

迁移成功当且仅当：

1. ✅ 所有单元测试通过（100%）
2. ✅ 所有集成测试通过
3. ✅ 旧导入路径正常工作（带警告）
4. ✅ 新导入路径正常工作（无警告）
5. ✅ 性能无明显下降（<5%）
6. ✅ 文档全面更新
7. ✅ CI/CD 流水线绿色
8. ✅ 代码审查通过

---

## 🔄 后续优化

迁移完成后推进以下改进：

1. **代码质量提升**
   - 添加类型提示
   - 改善 docstring
   - 统一错误处理
2. **性能优化**
   - 分析热点路径
   - 优化导入时间
   - 减少循环依赖
3. **架构改进**
   - 引入依赖注入
   - 提升测试覆盖率
   - 增加集成测试

---

## 📞 联系与支持

- **项目负责人**：[待指定]
- **技术顾问**：[待指定]
- **问题反馈**：[GitHub Issues](https://github.com/your-repo/issues)
- **讨论交流**：[GitHub Discussions](https://github.com/your-repo/discussions)

---

## 🎉 迁移总结（2026-01-30）

### ✅ 迁移成果
1. **架构清晰化**：从扁平结构重构为模块化架构，遵循 SOLID 原则
2. **职责分离**：每个模块有明确的职责边界
3. **可维护性提升**：代码组织更合理，便于扩展和维护
4. **向后兼容**：通过兼容层确保现有功能不受影响

### 🏗️ 新架构优势
1. **单一职责**：每个模块/类有明确的职责
2. **依赖倒置**：高层模块不依赖低层模块，都依赖抽象
3. **开闭原则**：易于扩展新功能（如添加新的 LLM 服务）
4. **接口隔离**：细粒度的接口设计
5. **依赖注入**：通过配置和工厂模式管理依赖

### 📈 下一步计划
1. **文档完善**：确保所有文档反映新架构
2. **测试覆盖**：增加对新模块的测试覆盖率
3. **性能优化**：基于新架构进行性能调优
4. **监控集成**：添加监控和可观测性支持

---

- **最后更新**：2026-01-30
- **文档版本**：2.0（迁移完成版）
- **审核状态**：✅ 已审核
- **迁移状态**：✅ 已完成（95%）  

✅ **说明**：
- 所有链接已修正，去除多余空格。
- 代码块使用标准 Markdown 语法包裹。
- 表格对齐清晰，避免换行混乱。
- 使用 `✅` / `❌` / `🟡` / `🔴` 等图标增强可读性。
- 适合用于团队协作、CI/CD 文档同步、发布前评审。

> 💡 如需导出为 PDF / HTML / Word，也可继续协助。
