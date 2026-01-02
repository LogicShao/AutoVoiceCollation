# 处理历史管理系统

## 概述

处理历史管理系统（Process History Manager）是 AutoVoiceCollation 的核心组件之一，用于跟踪已处理的音视频文件，避免重复处理，提供处理历史查询功能。

**模块位置**: `src/core/history/`

**核心文件**:
- `manager.py` - 历史管理器实现
- `__init__.py` - 模块导出

## 核心功能

### 1. 历史记录管理

- ✅ 记录已处理的视频/音频文件
- ✅ 避免重复处理相同内容
- ✅ 提供处理历史查询
- ✅ 支持记录更新和删除
- ✅ 持久化存储（JSON 格式）

### 2. 多源支持

支持以下三种类型的内容跟踪：

- **B站视频** (`bilibili`): 使用 BV 号或 AV 号作为唯一标识符
- **本地音频** (`local_audio`): 使用文件 hash 作为唯一标识符
- **本地视频** (`local_video`): 使用文件 hash 作为唯一标识符

### 3. 智能标识符生成

#### B站视频标识符提取
```python
# 支持多种 B站链接格式
url = "https://www.bilibili.com/video/BV1234567890"
identifier = ProcessHistoryManager.extract_bilibili_id(url)
# 返回: "BV1234567890"
```

支持的 URL 格式：
- `https://www.bilibili.com/video/BV...`
- `https://b23.tv/...`
- `bilibili://video/...`
- 直接提供 BV 号或 AV 号

#### 本地文件标识符生成
```python
# 使用文件名、大小、修改时间生成 MD5
file_path = "/path/to/audio.mp3"
identifier = ProcessHistoryManager.generate_file_identifier(file_path)
# 返回: "a1b2c3d4e5f6g7h8" (16位 MD5 hash)
```

## 数据模型

### ProcessRecord（处理记录）

```python
@dataclass
class ProcessRecord:
    identifier: str           # 唯一标识符（BV号、文件hash等）
    record_type: str          # 类型：bilibili, local_audio, local_video
    url: Optional[str]        # B站链接（如果是B站视频）
    title: str                # 视频/文件标题
    output_dir: str           # 输出目录
    last_processed: str       # 最后处理时间（ISO格式）
    config: Dict[str, Any]    # 处理配置（ASR模型、LLM配置等）
    outputs: Dict[str, str]   # 输出文件路径
    process_count: int = 1    # 处理次数
```

**字段说明**:

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `identifier` | str | 唯一标识符 | `"BV1234567890"` 或 `"a1b2c3d4e5f6g7h8"` |
| `record_type` | str | 记录类型 | `"bilibili"`, `"local_audio"`, `"local_video"` |
| `url` | str\|None | 原始 URL | `"https://www.bilibili.com/video/BV..."` |
| `title` | str | 标题 | `"视频标题"` |
| `output_dir` | str | 输出目录路径 | `"./out/video_name/"` |
| `last_processed` | str | 最后处理时间 | `"2024-01-15T10:30:00"` |
| `config` | dict | 处理配置快照 | `{"asr_model": "paraformer", "llm_server": "..."}` |
| `outputs` | dict | 输出文件映射 | `{"pdf": "output.pdf", "text": "polish_text.txt"}` |
| `process_count` | int | 处理次数 | `3` |

## 架构设计

### 单例模式

`ProcessHistoryManager` 使用单例模式，确保全局唯一实例：

```python
# 获取管理器实例（自动使用配置的输出目录）
manager = ProcessHistoryManager()

# 或指定自定义历史文件路径
manager = ProcessHistoryManager(history_file="/custom/path/.process_history.json")
```

### 存储格式

历史记录以 JSON 格式存储在 `.process_history.json` 文件中：

```json
{
  "version": "1.0",
  "records": {
    "BV1234567890": {
      "identifier": "BV1234567890",
      "record_type": "bilibili",
      "url": "https://www.bilibili.com/video/BV1234567890",
      "title": "示例视频标题",
      "output_dir": "./out/example_video/",
      "last_processed": "2024-01-15T10:30:00",
      "config": {
        "asr_model": "paraformer",
        "llm_server": "deepseek-chat",
        "output_style": "pdf_only"
      },
      "outputs": {
        "pdf": "./out/example_video/output.pdf",
        "text": "./out/example_video/polish_text.txt",
        "summary": "./out/example_video/summary_text.md"
      },
      "process_count": 2
    }
  }
}
```

**存储位置**:
- 默认: `{OUTPUT_DIR}/.process_history.json`
- 配置: 由 `.env` 中的 `OUTPUT_DIR` 决定（默认 `./out`）

### 核心 API

#### 1. 检查处理状态

```python
manager = ProcessHistoryManager()

# 检查是否已处理
if manager.check_processed("BV1234567890"):
    print("该视频已处理过")
```

#### 2. 获取历史记录

```python
# 获取单条记录
record = manager.get_record("BV1234567890")
if record:
    print(f"标题: {record.title}")
    print(f"处理次数: {record.process_count}")

# 获取所有记录（按时间倒序）
all_records = manager.get_all_records()
for record in all_records:
    print(f"{record.title} - {record.last_processed}")
```

#### 3. 添加/更新记录

```python
from datetime import datetime

# 创建 B站视频记录
record = manager.create_record_from_bilibili(
    url="https://www.bilibili.com/video/BV1234567890",
    title="示例视频",
    output_dir="./out/example_video/",
    config={"asr_model": "paraformer", "llm_server": "deepseek-chat"},
    outputs={"pdf": "./out/example_video/output.pdf"}
)

# 添加到历史
manager.add_record(record)
```

#### 4. 删除记录

```python
# 删除指定记录
if manager.delete_record("BV1234567890"):
    print("记录已删除")
```

## 错误处理

### 文件损坏自动恢复

如果历史文件损坏，管理器会：

1. 创建备份文件 `.process_history.json.backup`
2. 重置为空记录集
3. 记录错误日志

```python
# 加载失败时的处理逻辑
try:
    with open(self.history_file, "r") as f:
        data = json.load(f)
except Exception as e:
    logger.error(f"加载历史记录失败: {e}")
    # 创建备份
    backup_path = self.history_file.with_suffix(".json.backup")
    self.history_file.rename(backup_path)
    self.records = {}
```

### 标识符提取失败降级

如果无法从 B站 URL 提取 BV 号：

```python
# 降级方案：使用 URL 的 MD5 hash
identifier = hashlib.md5(url.encode("utf-8")).hexdigest()[:16]
logger.warning(f"无法从URL提取BV号，使用hash作为标识符: {identifier}")
```

## 集成示例

### 在处理器中使用

```python
from src.core.history import ProcessHistoryManager
from src.core.processors import AudioProcessor

# 获取历史管理器
history_manager = ProcessHistoryManager()

# 检查是否已处理
identifier = history_manager.extract_bilibili_id(bili_url)
if history_manager.check_processed(identifier):
    logger.info(f"视频 {identifier} 已处理过，跳过")
    record = history_manager.get_record(identifier)
    return {"status": "skipped", "previous_output": record.output_dir}

# 处理视频
processor = AudioProcessor()
result = processor.process(bili_url)

# 添加历史记录
record = history_manager.create_record_from_bilibili(
    url=bili_url,
    title=result["title"],
    output_dir=result["output_dir"],
    config={"asr_model": config.asr.model, "llm_server": config.llm.server},
    outputs=result["outputs"]
)
history_manager.add_record(record)
```

### 在 Web 前端中展示历史

```python
# 获取历史列表
history_manager = ProcessHistoryManager()
records = history_manager.get_all_records()

# 构建展示数据
history_data = [
    {
        "title": r.title,
        "type": r.record_type,
        "processed_at": r.last_processed,
        "output_dir": r.output_dir,
        "process_count": r.process_count
    }
    for r in records
]
```

## 配置和路径

### 默认历史文件位置

```
项目根目录/
└── out/
    └── .process_history.json
```

### 配置优先级

1. **显式指定**: `ProcessHistoryManager(history_file="/custom/path")`
2. **配置系统**: `{OUTPUT_DIR}/.process_history.json`（推荐）
3. **降级默认**: `./out/.process_history.json`

## 最佳实践

### 1. 使用单例实例

```python
# ✅ 推荐：始终使用同一个实例
manager = ProcessHistoryManager()

# ❌ 避免：重复创建实例
manager1 = ProcessHistoryManager()
manager2 = ProcessHistoryManager()  # 实际上与 manager1 是同一个实例
```

### 2. 记录完整配置快照

```python
# 记录处理时的配置，便于追溯
config_snapshot = {
    "asr_model": config.asr.model,
    "llm_server": config.llm.server,
    "llm_temperature": config.llm.temperature,
    "output_style": config.paths.output_style,
}

record = manager.create_record_from_bilibili(
    url=url,
    title=title,
    output_dir=output_dir,
    config=config_snapshot,  # 完整配置
    outputs=outputs
)
```

### 3. 定期清理过期记录

```python
# 示例：删除30天前的记录
from datetime import datetime, timedelta

def cleanup_old_records(days=30):
    manager = ProcessHistoryManager()
    cutoff_date = datetime.now() - timedelta(days=days)

    for record in manager.get_all_records():
        record_date = datetime.fromisoformat(record.last_processed)
        if record_date < cutoff_date:
            manager.delete_record(record.identifier)
            logger.info(f"删除过期记录: {record.title}")
```

## 性能考虑

### 内存占用

- **内存结构**: 所有记录加载到内存（`Dict[str, ProcessRecord]`）
- **典型大小**: 1000 条记录约 500KB - 1MB
- **建议**: 定期清理过期记录

### 文件 I/O

- **读取**: 仅在初始化时加载一次
- **写入**: 每次 `add_record()` 或 `delete_record()` 后立即保存
- **优化**: 批量操作时可考虑延迟保存

## 未来改进方向

### 计划中的功能

- [ ] **数据库后端**: 支持 SQLite/PostgreSQL 存储
- [ ] **搜索功能**: 按标题、日期范围搜索
- [ ] **统计分析**: 处理量统计、常用配置分析
- [ ] **导出功能**: 导出历史为 CSV/Excel
- [ ] **定时清理**: 自动删除过期记录

### 性能优化

- [ ] **延迟保存**: 批量操作时延迟写入磁盘
- [ ] **增量保存**: 仅保存变更的记录
- [ ] **压缩存储**: 使用 gzip 压缩历史文件
- [ ] **分片存储**: 按日期或类型分片存储

## 相关文档

- [开发者指南](../development/developer-guide.md)
- [项目结构](../development/project-structure.md)
- [异常处理架构](exception-handling.md)

---

**最后更新**: 2026-01-02
**维护者**: AutoVoiceCollation 开发团队
