# 处理历史管理系统 - 使用文档

## 📋 概述

处理历史管理系统是为 AutoVoiceCollation 项目新增的功能，用于跟踪已处理的音视频文件，避免重复处理并提供历史查询功能。

## ✨ 核心特性

- ✅ **自动记录处理历史**：每次处理完成后自动记录到JSON文件
- ✅ **智能去重**：自动检测已处理的视频/文件，避免重复处理
- ✅ **多源支持**：支持B站视频、本地音频、本地视频
- ✅ **统计分析**：提供处理统计信息和历史查询
- ✅ **轻量级存储**：使用JSON文件存储，无需数据库
- ✅ **单例模式**：全局唯一的历史管理器实例

## 📁 文件结构

```
src/
├── process_history.py          # 核心历史管理类
└── core_process_utils.py       # 辅助工具函数

docs/
└── WEBUI_HISTORY_INTEGRATION.py  # WebUI集成示例

tests/
├── test_process_history.py     # 完整测试脚本
└── test_process_history_simple.py  # 简化测试脚本

out/
└── .process_history.json       # 历史记录存储文件
```

## 🚀 快速开始

### 1. 基本使用

```python
from src.process_history import get_history_manager
from src.core_process_utils import (
    check_bilibili_processed,
    record_bilibili_process,
    build_output_files_dict
)

# 获取历史管理器实例
history_manager = get_history_manager()

# 检查B站视频是否已处理
video_url = "https://www.bilibili.com/video/BV1xx411c7mD"
record = check_bilibili_processed(video_url)

if record:
    print(f"该视频已于 {record.last_processed} 处理过")
    print(f"输出目录: {record.output_dir}")
    print(f"处理次数: {record.process_count}")
else:
    print("该视频尚未处理")
```

### 2. 记录处理历史

```python
# 处理完成后记录历史
config = {
    "asr_model": "paraformer",
    "llm_api": "deepseek-chat",
    "temperature": 0.1,
    "max_tokens": 6000
}

outputs = build_output_files_dict("out/video_name", text_only=False)

record_bilibili_process(
    video_url="https://www.bilibili.com/video/BV1xx411c7mD",
    title="视频标题",
    output_dir="out/video_name",
    config=config,
    outputs=outputs
)
```

### 3. 查询统计信息

```python
# 获取统计信息
stats = history_manager.get_statistics()
print(f"总记录数: {stats['total_records']}")
print(f"B站视频: {stats['bilibili_videos']}")
print(f"总处理次数: {stats['total_processes']}")

# 获取所有记录（按时间倒序）
records = history_manager.get_all_records()
for record in records:
    print(f"{record.title} - {record.last_processed}")
```

## 🔌 WebUI 集成

### 方式一：简单检查（推荐）

在处理函数开头添加历史检查，如果已处理过则显示提示信息：

```python
def bilibili_process_wrapper(url, llm_api, temp, tokens, text_only, task_id):
    # 检查历史
    record = check_bilibili_processed(url)
    if record:
        info = f"⚠️ 该视频已于 {record.last_processed} 处理过\n"
        info += f"输出目录: {record.output_dir}\n"
        info += f"继续处理将创建新的输出...\n\n"
        yield info, "", "", "", None
    else:
        yield "处理中...", "", "", "", None

    # 执行原有处理逻辑
    result = bilibili_video_download_process(...)

    # 处理完成后记录历史
    if isinstance(result_data, dict):
        record_bilibili_process(
            video_url=url,
            title=result_data.get("title"),
            output_dir=result_data.get("output_dir"),
            config={...},
            outputs=build_output_files_dict(result_data.get("output_dir"))
        )

    yield ...
```

### 方式二：添加检查按钮

在 Gradio UI 中添加"检查历史"按钮：

```python
with gr.Row():
    bilibili_input = gr.Textbox(label="请输入B站视频链接")
    check_history_btn = gr.Button("🔍 检查历史", size="sm")

history_info = gr.Textbox(label="历史信息", visible=False)

def show_history(url):
    record = check_bilibili_processed(url)
    if record:
        info = f"已处理 {record.process_count} 次\n"
        info += f"上次处理: {record.last_processed}\n"
        info += f"输出目录: {record.output_dir}"
        return gr.update(value=info, visible=True)
    return gr.update(value="尚未处理", visible=True)

check_history_btn.click(
    fn=show_history,
    inputs=[bilibili_input],
    outputs=[history_info]
)
```

完整的WebUI集成示例请参考 `docs/WEBUI_HISTORY_INTEGRATION.py`。

## 📊 数据结构

### ProcessRecord

```python
@dataclass
class ProcessRecord:
    identifier: str         # 唯一标识符（BV号、文件hash等）
    record_type: str        # 类型：bilibili, local_audio, local_video
    url: Optional[str]      # B站链接（如果是B站视频）
    title: str              # 视频/文件标题
    output_dir: str         # 输出目录
    last_processed: str     # 最后处理时间（ISO格式）
    config: Dict[str, Any]  # 处理配置
    outputs: Dict[str, str] # 输出文件路径
    process_count: int = 1  # 处理次数
```

### JSON 存储格式

```json
{
  "version": "1.0",
  "records": {
    "BV1xx411c7mD": {
      "identifier": "BV1xx411c7mD",
      "record_type": "bilibili",
      "url": "https://www.bilibili.com/video/BV1xx411c7mD",
      "title": "视频标题",
      "output_dir": "out/video_name",
      "last_processed": "2025-11-25T13:08:18.599572",
      "config": {
        "asr_model": "paraformer",
        "llm_api": "deepseek-chat",
        "temperature": 0.1,
        "max_tokens": 6000
      },
      "outputs": {
        "audio_transcription": "out/video_name/audio_transcription.txt",
        "polish_text": "out/video_name/polish_text.txt"
      },
      "process_count": 1
    }
  }
}
```

## 🔧 API 参考

### ProcessHistoryManager

#### 核心方法

```python
# 检查是否已处理
history_manager.check_processed(identifier: str) -> bool

# 获取处理记录
history_manager.get_record(identifier: str) -> Optional[ProcessRecord]

# 添加/更新记录
history_manager.add_record(record: ProcessRecord)

# 删除记录
history_manager.delete_record(identifier: str) -> bool

# 获取所有记录
history_manager.get_all_records() -> List[ProcessRecord]

# 获取统计信息
history_manager.get_statistics() -> Dict[str, Any]
```

#### 辅助方法

```python
# 提取B站视频ID
history_manager.extract_bilibili_id(url: str) -> Optional[str]

# 生成文件标识符
history_manager.generate_file_identifier(file_path: str) -> str

# 从B站视频信息创建记录
history_manager.create_record_from_bilibili(
    url, title, output_dir, config, outputs
) -> ProcessRecord

# 从本地文件信息创建记录
history_manager.create_record_from_local_file(
    file_path, file_type, title, output_dir, config, outputs
) -> ProcessRecord
```

### 辅助工具函数（core_process_utils.py）

```python
# 检查B站视频是否已处理
check_bilibili_processed(video_url: str) -> Optional[ProcessRecord]

# 记录B站视频处理历史
record_bilibili_process(
    video_url, title, output_dir, config, outputs
) -> ProcessRecord

# 记录本地文件处理历史
record_local_file_process(
    file_path, file_type, title, output_dir, config, outputs
) -> ProcessRecord

# 构建输出文件路径字典
build_output_files_dict(output_dir: str, text_only: bool) -> Dict[str, str]
```

## 🧪 测试

运行测试脚本验证功能：

```bash
# 完整测试（包含emoji，可能在Windows上显示乱码）
python tests/test_process_history.py

# 简化测试（纯ASCII字符）
python tests/test_process_history_simple.py
```

测试覆盖：

- ✅ URL解析和标识符生成
- ✅ 创建处理记录
- ✅ 历史检查
- ✅ 统计信息
- ✅ 记录列表
- ✅ 重复处理（处理次数自动增加）
- ✅ 本地文件记录

## 📝 使用场景

### 场景1：避免重复下载B站视频

```python
video_url = "https://www.bilibili.com/video/BV1xx411c7mD"

# 检查是否已下载
record = check_bilibili_processed(video_url)
if record:
    print(f"该视频已处理过，输出目录: {record.output_dir}")
    print("是否继续处理？")
    # 在WebUI中询问用户
else:
    # 继续下载和处理
    pass
```

### 场景2：批量处理时跳过已处理视频

```python
urls = ["https://...", "https://...", ...]

for url in urls:
    record = check_bilibili_processed(url)
    if record:
        print(f"跳过已处理视频: {record.title}")
        continue

    # 处理新视频
    result = bilibili_video_download_process(url, ...)
```

### 场景3：查看处理历史和统计

```python
# 查看最近处理的视频
records = history_manager.get_all_records()
print("最近处理的视频:")
for i, record in enumerate(records[:10], 1):
    print(f"{i}. {record.title} ({record.last_processed})")

# 查看统计信息
stats = history_manager.get_statistics()
print(f"\n已处理 {stats['bilibili_videos']} 个B站视频")
print(f"总处理次数: {stats['total_processes']}")
```

## ⚠️ 注意事项

1. **历史文件位置**：默认存储在 `out/.process_history.json`，该文件应添加到 `.gitignore`
2. **重复处理**：重新处理已处理过的视频会增加 `process_count`，但会创建新的输出目录
3. **标识符生成**：
    - B站视频：使用 BV号 或 AV号
    - 本地文件：使用文件名、大小和修改时间的MD5哈希
4. **单例模式**：`get_history_manager()` 返回全局唯一实例
5. **线程安全**：当前实现不是线程安全的，在多线程环境中需要额外的同步机制
6. **文件备份**：加载历史文件失败时会自动创建备份（`.json.backup`）

## 🔄 未来改进

- [ ] 添加导出功能（导出为Excel/CSV）
- [ ] 支持搜索和过滤功能
- [ ] 添加历史记录可视化（图表）
- [ ] 支持数据库存储（SQLite）
- [ ] 实现线程安全
- [ ] 添加历史记录清理策略（如自动删除30天前的记录）
- [ ] 支持导入/导出历史记录

## 💡 常见问题

### Q: 历史文件在哪里？

A: 默认在 `out/.process_history.json`。可以通过 `history_manager.history_file` 查看完整路径。

### Q: 如何清空历史记录？

A:

```python
history_manager.records.clear()
history_manager._save()
```

或直接删除 `out/.process_history.json` 文件。

### Q: 如何判断两个本地文件是否相同？

A: 使用 `generate_file_identifier()` 生成的标识符，基于文件名、大小和修改时间。

### Q: 重复处理会怎样？

A: 会更新记录中的配置和输出目录，处理次数 +1，但不会覆盖之前的输出文件。

### Q: 支持哪些视频平台？

A: 目前仅支持B站（bilibili），其他平台可扩展实现类似的标识符提取逻辑。

## 📄 许可证

本功能遵循项目的整体许可证。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**更新日期**: 2025-11-25
**版本**: 1.0.0
