# Docker 中文字体问题完整解决方案

## 问题描述

容器启动时出现错误：

```
FileNotFoundError: 未找到可用的中文字体
```

导致容器无法启动，WebUI
无法访问。

## 根本原因

1.
*
*字体虽然安装但未被找到
**
：Dockerfile
安装了
`fonts-wqy-zenhei`
和
`fonts-noto-cjk`
，但字体搜索逻辑无法找到它们
2.
*
*模块级字体加载
**：
`text_exporter.py`
在模块导入时就尝试加载字体，如果失败会阻止整个应用启动
3.
*
*环境变量未生效
**
：Dockerfile
中的
`ENV`
设置可能不会传递到运行时

## 完整解决方案

### 修复 1：Dockerfile 优化

*
*文件
**:
`Dockerfile`
和
`Dockerfile.cpu`

*
*修改内容
**：

```dockerfile
# 1. 安装 fontconfig 工具
RUN apt-get install -y fontconfig

# 2. 更新字体缓存
&& fc-cache -fv

# 3. 设置环境变量
ENV CHINESE_FONT_PATH=/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc
```

### 修复 2：docker-compose.yml 环境变量

*
*文件
**:
`docker-compose.yml`

*
*添加
**：

```yaml
environment:
  - CHINESE_FONT_PATH=/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc
```

### 修复 3：延迟加载字体

*
*文件
**:
`src/text_arrangement/text_exporter.py`

*
*关键改动
**：

1.
*
*移除模块级字体加载
**
（原来在第
160-168
行）：
```python
# 原来：启动时立即加载
font_ttf_path = get_font_path()
pdfmetrics.registerFont(TTFont('ChineseFont', font_ttf_path))
```

2.
*
*改为延迟加载
**：
```python
# 现在：使用延迟加载函数
_font_initialized = False
_font_error = None

def _ensure_font_loaded():
    """仅在需要时加载字体"""
    global _font_initialized, _font_error
    if _font_initialized:
        return
    # 加载字体逻辑...
```

3.
*
*在需要时调用
**：
```python
def text_to_pdf(...):
    _ensure_font_loaded()  # 仅在生成 PDF 时加载
    # ...

def text_to_one_image(...):
    _ensure_font_loaded()  # 仅在生成图片时加载
    # ...
```

*
*优点
**：

-
✅
应用可以正常启动，即使字体暂时不可用
-
✅
仅在实际需要生成
PDF/图片时才检查字体
-
✅
如果用户只使用文本输出（
`text_only`
），完全不需要字体

## 部署步骤

### 1. 停止现有容器

```bash
docker compose down
```

### 2. 清理并重新构建

```bash
# 清理旧镜像
docker builder prune -f

# 重新构建（无缓存）
docker compose build --no-cache
```

### 3. 启动容器

```bash
docker compose up -d
```

### 4. 验证字体配置

使用验证脚本：

```bash
# Linux/Mac
./verify-font.sh

# Windows (手动执行以下命令)
docker exec avc-webui test -f /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc
docker exec avc-webui printenv | grep CHINESE_FONT_PATH
docker exec avc-webui fc-list :lang=zh | head -3
```

### 5. 查看启动日志

```bash
docker compose logs -f
```

*
*期望看到
**：

```
成功加载字体: /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc
Running on http://0.0.0.0:7860
```

## 验证成功

### 测试 1：WebUI 可访问

打开浏览器访问 http://localhost:7860
，应该能看到
Gradio
界面。

### 测试 2：使用 text_only 模式

在
WebUI
中勾选"
仅返回文本(
JSON)"
选项，处理一个音频文件：

-
✅
应该能正常工作
-
✅
不需要字体也能完成

### 测试 3：生成 PDF

不勾选"
仅返回文本"
，正常处理：

-
✅
应该能生成
PDF
-
✅
PDF
中中文显示正常

## 故障排除

### 问题 1：容器仍然无法启动

*
*检查日志
**：

```bash
docker compose logs --tail=50
```

*
*可能原因
**：

-
构建时缓存了旧代码，使用
`--no-cache`
重新构建
-
环境变量未生效，检查
docker-compose.yml

### 问题 2：字体文件路径错误

*
*手动查找字体
**：

```bash
docker exec avc-webui find /usr/share/fonts -name "*.ttc" -o -name "*.ttf" | grep -i "wqy\|noto"
```

*
*如果路径不同
**
，修改
`docker-compose.yml`
中的路径：

```yaml
environment:
  - CHINESE_FONT_PATH=/实际/字体/路径.ttc
```

### 问题 3：字体显示异常

*
*检查字体缓存
**：

```bash
docker exec avc-webui fc-cache -fv
docker exec avc-webui fc-list :lang=zh
```

### 问题 4：使用其他字体

如果想使用
Noto
CJK
字体：

```yaml
environment:
  - CHINESE_FONT_PATH=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc
```

或挂载本地字体：

```yaml
volumes:
  - ./fonts/your-font.ttf:/app/fonts/chinese.ttf

environment:
  - CHINESE_FONT_PATH=/app/fonts/chinese.ttf
```

## 临时解决方案

如果仍然有问题，可以暂时禁用
PDF
生成功能：

### 方案 A：仅使用 text_only 模式

在
`.env`
文件中设置：

```env
TEXT_ONLY_DEFAULT=true
```

这样默认只输出
JSON，不生成
PDF/图片。

### 方案 B：禁用输出功能

修改
`config.py`：

```python
OUTPUT_STYLE = "text_only"
```

## 预防措施

### 1. 使用多阶段构建优化

未来可以考虑使用多阶段构建，预先验证字体：

```dockerfile
# 验证阶段
FROM base AS font-check
RUN test -f /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc || exit 1

# 运行阶段
FROM base
COPY --from=font-check /usr/share/fonts /usr/share/fonts
```

### 2. 健康检查包含字体验证

修改
`docker-compose.yml`
的健康检查：

```yaml
healthcheck:
  test: >
    curl -f http://localhost:7860 &&
    test -f ${CHINESE_FONT_PATH:-/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc}
```

### 3. 启动脚本验证

在
`CMD`
之前添加验证步骤：

```dockerfile
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["python", "webui.py"]
```

`docker-entrypoint.sh`:

```bash
#!/bin/bash
if [ ! -f "${CHINESE_FONT_PATH}" ]; then
    echo "Warning: Font not found at ${CHINESE_FONT_PATH}"
    echo "Searching for alternative fonts..."
    export CHINESE_FONT_PATH=$(find /usr/share/fonts -name "*.ttc" | head -1)
fi
exec "$@"
```

## 相关文档

- [Docker 容器崩溃故障排除](DOCKER_CRASH_TROUBLESHOOTING.md)
- [Docker 网络问题解决](DOCKER_NETWORK_TROUBLESHOOTING.md)
- [Docker 部署指南](DOCKER.md)

---

*
*更新时间
**:
2025-11-07
*
*问题状态
**:
✅
已解决
