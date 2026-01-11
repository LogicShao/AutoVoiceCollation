"""
测试文件名处理工具模块
"""

import pytest

from src.utils.helpers.filename import generate_title_from_text, sanitize_filename


class TestSanitizeFilename:
    """测试文件名安全化函数"""

    def test_remove_illegal_characters(self):
        """测试移除非法字符"""
        # Windows 非法字符
        assert sanitize_filename("如何使用 Claude?") == "如何使用 Claude"
        assert sanitize_filename("文件:测试") == "文件_测试"
        assert sanitize_filename('包含"引号"的文件') == "包含_引号_的文件"
        assert sanitize_filename("路径\\测试") == "路径_测试"
        assert sanitize_filename("C:\\Users\\test") == "C_Users_test"
        assert sanitize_filename("文件|管道") == "文件_管道"
        assert sanitize_filename("文件<>测试") == "文件_测试"
        assert sanitize_filename("文件*通配符") == "文件_通配符"

    def test_trim_whitespace(self):
        """测试空格处理"""
        assert sanitize_filename("  测试文件  ") == "测试文件"
        assert sanitize_filename("测试  文件") == "测试 文件"
        assert sanitize_filename("   多个   空格   ") == "多个 空格"

    def test_length_limit(self):
        """测试长度限制"""
        long_name = "a" * 300
        result = sanitize_filename(long_name, max_length=200)
        assert len(result) == 200

        # 测试智能截断（在空格处）
        long_with_space = "测试文件 " * 100
        result = sanitize_filename(long_with_space, max_length=200)
        assert len(result) <= 200
        # 应该在接近200的空格处截断
        assert not result.endswith(" ")

    def test_empty_string(self):
        """测试空字符串处理"""
        assert sanitize_filename("") == "未命名"
        assert sanitize_filename("   ") == "未命名"
        assert sanitize_filename("???") == "未命名"  # 全是非法字符

    def test_chinese_characters(self):
        """测试中文字符"""
        assert sanitize_filename("中文测试文件.txt") == "中文测试文件.txt"
        assert sanitize_filename("深度学习基础讲座") == "深度学习基础讲座"

    def test_mixed_content(self):
        """测试混合内容"""
        assert sanitize_filename("2024年AI发展报告.pdf") == "2024年AI发展报告.pdf"
        assert sanitize_filename("Python3.11新特性") == "Python3.11新特性"


class TestGenerateTitleFromText:
    """测试 LLM 标题生成函数"""

    def test_generate_title_success(self, mocker):
        """测试成功生成标题"""
        # Mock query_llm 函数
        mock_query_llm = mocker.patch("src.utils.helpers.filename.query_llm")
        mock_query_llm.return_value = "深度学习基础讲座"

        text = "今天我们来讲解深度学习的基础知识，包括神经网络、反向传播等内容..."
        title = generate_title_from_text(text, llm_service="gemini-2.0-flash")

        assert title == "深度学习基础讲座"
        mock_query_llm.assert_called_once()

    def test_generate_title_with_quotes(self, mocker):
        """测试生成的标题包含引号时自动清理"""
        mock_query_llm = mocker.patch("src.utils.helpers.filename.query_llm")
        mock_query_llm.return_value = '"机器学习入门"'

        text = "机器学习是人工智能的一个分支..."
        title = generate_title_from_text(text, llm_service="gemini-2.0-flash")

        # 应该自动移除引号
        assert title == "机器学习入门"

    def test_generate_title_empty_text(self):
        """测试空文本返回 None"""
        title = generate_title_from_text("", llm_service="gemini-2.0-flash")
        assert title is None

        title = generate_title_from_text("   ", llm_service="gemini-2.0-flash")
        assert title is None

    def test_generate_title_llm_failure(self, mocker):
        """测试 LLM 调用失败时返回 None"""
        mock_query_llm = mocker.patch("src.utils.helpers.filename.query_llm")
        mock_query_llm.side_effect = Exception("API Error")

        text = "测试文本内容"
        title = generate_title_from_text(text, llm_service="gemini-2.0-flash")

        # 失败时应该返回 None，不抛出异常
        assert title is None

    def test_generate_title_empty_response(self, mocker):
        """测试 LLM 返回空响应"""
        mock_query_llm = mocker.patch("src.utils.helpers.filename.query_llm")
        mock_query_llm.return_value = ""

        text = "测试文本内容"
        title = generate_title_from_text(text, llm_service="gemini-2.0-flash")

        assert title is None

    def test_generate_title_with_illegal_chars(self, mocker):
        """测试生成的标题包含非法字符时自动安全化"""
        mock_query_llm = mocker.patch("src.utils.helpers.filename.query_llm")
        mock_query_llm.return_value = "文件:测试?"

        text = "测试内容"
        title = generate_title_from_text(text, llm_service="gemini-2.0-flash")

        # 应该自动安全化
        assert title == "文件_测试"

    def test_generate_title_length_limit(self, mocker):
        """测试标题长度限制"""
        long_title = "这是一个非常非常长的标题" * 10
        mock_query_llm = mocker.patch("src.utils.helpers.filename.query_llm")
        mock_query_llm.return_value = long_title

        text = "测试内容"
        title = generate_title_from_text(text, llm_service="gemini-2.0-flash", max_length=50)

        # 标题应该被截断到 max_length
        assert len(title) <= 50
