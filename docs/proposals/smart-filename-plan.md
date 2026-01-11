# 智能输出文件命名功能实现计划

## 📋 需求概述

**目标**：改进输出 PDF 文件的命名，使其具有具体含义并与视频内容相关。

**当前问题**：
- PDF 文件统一命名为 `output.pdf`，缺乏区分度
- 输出目录名基于音频文件名，对本地上传文件不够友好
- 本地视频文件无法自动生成有意义的标题

**期望效果**：
- B站视频：使用视频标题作为 PDF 文件名（如：`如何使用Claude Code进行开发.pdf`）
- 本地视频：通过 LLM 基于转录内容生成合适的文件名（如：`音乐节演出实况录音.pdf`）

---

## 🔍 当前代码分析

### 1. 文件命名流程

**代码路径**：`src/text_arrangement/text_exporter.py:210`
```python
pdf_path = os.path.join(output_dir, "output.pdf")  # ❌ 硬编码
```

**调用链**：
```
AudioProcessor.process()
  └─> _export_output(polished_text, output_dir, audio_file.title, ...)
      └─> text_to_img_or_pdf(polished_text, title=title, output_path=output_dir, ...)
          └─> text_to_pdf(txt, ..., title, output_dir, ...)
              └─> pdf_path = "output.pdf"  # 硬编码在这里
```

### 2. 输出目录命名

**代码路径**：`src/core/processors/audio.py:66-81`
```python
def _create_output_directory(self, audio_file: BiliVideoFile) -> str:
    audio_file_name = os.path.basename(audio_file.path).split(".")[0]
    output_dir = self.config.paths.output_dir / audio_file_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir)
```

### 3. 标题来源

**B站视频**：
- 来源：`BiliVideoFile.title`（从 B站 API 获取）
- 示例：`"Claude Code 开发实战教程"`

**本地文件**：
- 来源：`new_local_bili_file(audio_path, title=None)`
- 当前值：`None`（无标题）

---

## 🎯 实现方案

### 方案设计原则

1. **向后兼容**：保持现有 API 接口不变
2. **安全文件名**：处理非法字符（如 `/`, `\`, `:` 等）
3. **长度限制**：文件名不超过 200 字符（预留扩展名和时间戳）
4. **失败降级**：LLM 生成失败时回退到原文件名

---

## 📝 详细实现步骤

### 阶段 1：工具函数（utils/helpers/filename.py）

**新建文件**：`src/utils/helpers/filename.py`

**功能 1：文件名安全化**
```python
def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    将字符串转换为安全的文件名

    - 移除/替换非法字符（Windows: <>:"/\|?* 等）
    - 移除前后空格
    - 限制长度（默认 200 字符）
    - 处理空字符串情况

    示例：
        "如何使用 Claude Code?" -> "如何使用 Claude Code"
        "C:\\Users\\..." -> "C_Users_..."
        超长字符串 -> 截断到 max_length
    """
```

**功能 2：LLM 生成标题**
```python
async def generate_title_from_text(
    text: str,
    llm_service: str = "gemini-2.0-flash",
    max_length: int = 50
) -> str | None:
    """
    通过 LLM 根据文本内容生成合适的标题

    参数：
        text: 转录文本（取前 2000 字符避免 token 超限）
        llm_service: LLM 服务名称（默认使用快速模型）
        max_length: 生成标题的最大长度

    返回：
        str: 生成的标题（已安全化）
        None: 生成失败（网络错误、API 限流等）

    Prompt 设计：
        "请根据以下文本内容生成一个简洁、准确的标题（不超过{max_length}字符）。
        只返回标题，不要有任何解释或标点符号：\n\n{text[:2000]}"
    """
```

---

### 阶段 2：修改核心导出函数（text_exporter.py）

**修改函数签名**：
```python
def text_to_pdf(
    txt: str,
    with_img: bool,
    title: str,
    output_dir: str,
    ASR_model: str,
    LLM_info: str = "",
    pdf_filename: str | None = None,  # ✅ 新增参数
) -> str:
```

**核心改动**（line 210）：
```python
# 修改前：
pdf_path = os.path.join(output_dir, "output.pdf")

# 修改后：
if pdf_filename:
    # 安全化文件名并添加扩展名
    safe_filename = sanitize_filename(pdf_filename)
    if not safe_filename.lower().endswith('.pdf'):
        safe_filename += '.pdf'
    pdf_path = os.path.join(output_dir, safe_filename)
else:
    # 向后兼容：保留原行为
    pdf_path = os.path.join(output_dir, "output.pdf")
```

**同步修改 `text_to_img_or_pdf` 函数**（line 392）：
```python
def text_to_img_or_pdf(
    text: str,
    title: str,
    output_style: str,
    output_path: str,
    LLM_info: str,
    pdf_filename: str | None = None,  # ✅ 新增参数
):
    # ... 省略代码 ...
    if output_style in ("pdf_only", "pdf_with_img"):
        text_to_pdf(
            text,
            with_img=(output_style == "pdf_with_img"),
            title=title,
            output_dir=output_path,
            ASR_model=config.asr.asr_model,
            LLM_info=LLM_info,
            pdf_filename=pdf_filename,  # ✅ 传递参数
        )
```

---

### 阶段 3：修改处理器（audio.py）

**步骤 1：扩展 `_export_output` 方法**

在 `AudioProcessor` 类中：
```python
def _export_output(
    self,
    polished_text: str,
    output_dir: str,
    title: str,
    llm_api: str,
    temperature: float,
    pdf_filename: str | None = None,  # ✅ 新增参数
):
    """导出输出文件"""
    text_to_img_or_pdf(
        polished_text,
        title=title,
        output_style=self.config.output_style,
        output_path=output_dir,
        LLM_info=f"({llm_api},温度:{temperature})",
        pdf_filename=pdf_filename,  # ✅ 传递参数
    )
```

**步骤 2：修改 `process` 方法**

在 `process` 方法中（line 342 附近）：
```python
# 生成 PDF 文件名
pdf_filename = None
if audio_file.title:
    # B站视频：使用标题
    pdf_filename = audio_file.title
else:
    # 本地文件：尝试从音频文本生成标题
    self.logger.info("本地文件无标题，尝试通过 LLM 生成...")
    try:
        from src.utils.helpers.filename import generate_title_from_text
        pdf_filename = await generate_title_from_text(
            text=audio_text,  # 使用原始转录文本
            llm_service=llm_api,
        )
        if pdf_filename:
            self.logger.info(f"生成标题: {pdf_filename}")
            # 更新 audio_file.title 以便其他地方使用
            audio_file.title = pdf_filename
        else:
            self.logger.warning("LLM 标题生成失败，使用文件名")
    except Exception as e:
        self.logger.error(f"标题生成异常: {e}", exc_info=True)

# 正常模式：生成PDF/图片
self._export_output(
    polished_text,
    output_dir,
    audio_file.title or "未命名",
    llm_api,
    temperature,
    pdf_filename=pdf_filename,  # ✅ 传递文件名
)
```

**步骤 3：处理同步/异步问题**

⚠️ **注意**：`generate_title_from_text` 是异步函数，但 `process` 是同步函数。

**解决方案**：使用 `asyncio.run()` 或 `asyncio.get_event_loop().run_until_complete()`
```python
import asyncio

# 在同步函数中调用异步函数
if not audio_file.title:
    try:
        from src.utils.helpers.filename import generate_title_from_text
        # 同步调用异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            pdf_filename = loop.run_until_complete(
                generate_title_from_text(text=audio_text, llm_service=llm_api)
            )
        finally:
            loop.close()
    except Exception as e:
        self.logger.error(f"标题生成异常: {e}", exc_info=True)
```

---

### 阶段 4：配置选项（可选）

**新增配置**：`src/utils/config/base.py` 或独立配置类

```python
@dataclass
class OutputConfig:
    """输出文件配置"""

    # 是否启用智能文件名（默认启用）
    smart_filename_enabled: bool = True

    # 文件名最大长度
    filename_max_length: int = 200

    # 用于生成标题的 LLM 服务（使用快速模型节省成本）
    title_generation_llm: str = "gemini-2.0-flash"

    # 标题生成超时时间（秒）
    title_generation_timeout: int = 10
```

**环境变量支持**：`.env`
```bash
# 智能文件名开关
SMART_FILENAME_ENABLED=true

# 标题生成 LLM（建议使用快速模型）
TITLE_GENERATION_LLM=gemini-2.0-flash
```

---

## 🧪 测试计划

### 单元测试（tests/test_filename.py）

```python
def test_sanitize_filename():
    """测试文件名安全化"""
    assert sanitize_filename("如何使用 Claude?") == "如何使用 Claude"
    assert sanitize_filename("C:\\Users\\test") == "C_Users_test"
    assert len(sanitize_filename("a" * 300, max_length=200)) == 200

async def test_generate_title_from_text():
    """测试 LLM 标题生成"""
    text = "这是一段关于机器学习的讲座内容..."
    title = await generate_title_from_text(text)
    assert title is not None
    assert len(title) <= 50

def test_pdf_filename_generation():
    """测试 PDF 文件名生成"""
    # B站视频：使用标题
    bili_file = BiliVideoFile(url="...", title="测试视频", ...)
    # ... 验证 PDF 文件名为 "测试视频.pdf"

    # 本地文件：生成标题
    local_file = BiliVideoFile(url="file://...", title=None, ...)
    # ... 验证调用 LLM 生成标题
```

### 集成测试

1. **B站视频测试**：
   - 下载一个正常 B站视频
   - 验证 PDF 文件名使用视频标题

2. **本地文件测试**：
   - 上传一个本地音频文件
   - 验证 LLM 生成合理标题
   - 验证 PDF 文件名使用生成的标题

3. **失败降级测试**：
   - 模拟 LLM API 失败
   - 验证回退到原文件名
   - 验证不影响正常流程

---

## 🚨 风险与注意事项

### 1. 文件名冲突

**问题**：同一目录下可能有同名 PDF（如多次处理同一视频）

**解决方案**：
- 方案 A（推荐）：在文件名后添加时间戳（`标题_20260110_203045.pdf`）
- 方案 B：检测冲突，自动添加序号（`标题(1).pdf`、`标题(2).pdf`）

### 2. LLM 调用成本

**问题**：每次处理本地文件都调用 LLM 会增加成本

**解决方案**：
- 使用快速、低成本模型（Gemini Flash、Cerebras 等）
- 只传递前 2000 字符（约 500-1000 tokens）
- 添加配置开关，可禁用该功能
- 缓存生成的标题（基于文本 hash）

### 3. 异步调用复杂度

**问题**：在同步函数中调用异步 LLM API

**解决方案**：
- 使用 `asyncio.run()` 包装
- 或将整个处理流程改为异步（更大改动）

### 4. 文件名长度

**问题**：Windows 路径限制 260 字符

**解决方案**：
- 限制文件名长度为 200 字符
- 超长时智能截断（避免截断中文字符）

---

## 📦 向后兼容性

**保证**：
- ✅ 原有 API 接口保持不变
- ✅ 配置为空时回退到 `output.pdf`
- ✅ LLM 失败时不影响主流程
- ✅ 输出目录结构不变

---

## 🔄 实施顺序

1. **第一阶段**（核心功能）：
   - [ ] 创建 `filename.py` 工具文件
   - [ ] 实现 `sanitize_filename` 函数
   - [ ] 实现 `generate_title_from_text` 函数
   - [ ] 编写单元测试

2. **第二阶段**（集成）：
   - [ ] 修改 `text_exporter.py` 添加参数
   - [ ] 修改 `audio.py` 处理器
   - [ ] 处理同步/异步调用
   - [ ] 编写集成测试

3. **第三阶段**（优化）：
   - [ ] 添加配置选项
   - [ ] 实现文件名冲突处理
   - [ ] 性能优化和错误处理
   - [ ] 更新文档

4. **第四阶段**（扩展，可选）：
   - [ ] 支持其他处理器（视频、字幕）
   - [ ] 添加标题缓存机制
   - [ ] 支持自定义 Prompt

---

## 📊 预期效果

**改进前**：
```
out/
└── my_local_audio/
    └── output.pdf  ❌ 无意义的文件名
```

**改进后**：
```
out/
└── my_local_audio/
    └── 深度学习基础讲座.pdf  ✅ 有意义的文件名
```

---

## 📝 后续优化建议

1. **多语言支持**：根据音频语言选择不同的 Prompt
2. **标题模板**：允许用户自定义标题格式（如：`[分类] 标题 - 作者`）
3. **批量处理优化**：缓存 LLM 生成的标题，避免重复调用
4. **UI 展示**：在前端显示生成的标题，允许用户编辑

---

## ❓ 问题与决策点

请在审阅时考虑以下问题：

1. **文件名冲突处理**：使用时间戳还是序号？
2. **LLM 模型选择**：默认使用哪个模型？是否允许用户配置？
3. **失败降级策略**：LLM 失败时使用什么文件名？
4. **异步实现**：是否需要将整个处理流程改为异步？
5. **配置粒度**：是否需要单独的 `OutputConfig` 类？

---

## ✅ 待审阅清单

- [ ] 需求理解是否准确？
- [ ] 技术方案是否可行？
- [ ] 实施步骤是否合理？
- [ ] 是否有遗漏的边界情况？
- [ ] 测试覆盖是否充分？
- [ ] 配置选项是否必要？

---

**文档版本**：v1.0
**创建时间**：2026-01-10
**当前分支**：`feature/smart-output-filename`
**预计工作量**：8-12 小时（包含测试和文档）
