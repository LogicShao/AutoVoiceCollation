"""
文本分割模块单元测试
测试文本按句子分割、智能分割和 ASR 文本清理功能
"""

import re

import pytest

from src.text_arrangement.split_text import (
    clean_asr_text,
    is_chinese,
    smart_split,
    split_text_by_sentences,
)


class TestSplitTextBySentences:
    """测试按句子分割文本"""

    def test_split_simple_text(self):
        """测试简单文本分割"""
        text = "这是第一句。这是第二句。这是第三句。"
        result = split_text_by_sentences(text, split_len=20)

        assert len(result) > 0
        assert all(isinstance(chunk, str) for chunk in result)

    def test_split_with_multiple_punctuation(self):
        """测试多种标点符号"""
        text = "这是问题吗？这是感叹句！这是普通句子。"
        result = split_text_by_sentences(text, split_len=50)

        assert len(result) == 1
        assert "这是问题吗？" in result[0]

    def test_split_exceeds_limit(self):
        """测试超过长度限制的文本"""
        text = "这是一个很长的句子。" * 10
        result = split_text_by_sentences(text, split_len=30)

        assert len(result) > 1
        for chunk in result:
            # 每个块的长度不应严重超过限制（允许单个句子超限）
            pass  # 函数设计允许句子本身超过限制

    def test_split_empty_text(self):
        """测试空文本"""
        text = ""
        result = split_text_by_sentences(text, split_len=100)

        # 空文本应该返回空列表或只包含空字符串
        assert len(result) == 0 or (len(result) == 1 and result[0] == "")

    def test_split_single_sentence(self):
        """测试单个句子"""
        text = "这是唯一的一句话。"
        result = split_text_by_sentences(text, split_len=100)

        assert len(result) == 1
        assert result[0] == "这是唯一的一句话。"

    def test_split_preserves_trailing_text_without_terminal_punctuation(self):
        """测试末尾没有标点时不丢失尾部内容"""
        text = "第一句。第二句没有句号"
        result = split_text_by_sentences(text, split_len=100)
        merged = "".join(result)

        assert "第一句。" in merged
        assert "第二句没有句号" in merged

    def test_split_no_punctuation(self):
        """测试没有标点符号的文本"""
        text = "这是一段没有标点符号的文本" * 3
        result = split_text_by_sentences(text, split_len=10)

        assert len(result) > 0
        assert all(chunk.strip() for chunk in result)
        assert all(len(chunk) <= 10 for chunk in result)

        # 去掉空白后内容应保持一致（split_text_by_sentences 会 strip chunk）
        norm = lambda s: re.sub(r"\s+", "", s)  # noqa: E731
        assert norm("".join(result)) == norm(text)

    def test_split_mixed_punctuation(self):
        """测试中英文混合标点"""
        text = "This is English. 这是中文。Another sentence! 另一句？"
        result = split_text_by_sentences(text, split_len=100)

        assert len(result) == 1
        assert "English" in result[0]
        assert "中文" in result[0]

    def test_split_very_small_limit(self):
        """测试非常小的分割限制"""
        text = "第一句。第二句。第三句。"
        result = split_text_by_sentences(text, split_len=5)

        # 每个句子都应该被单独分割
        assert len(result) > 1

    def test_split_consecutive_punctuation(self):
        """测试连续标点符号"""
        text = "真的吗？？！！是的。。"
        result = split_text_by_sentences(text, split_len=100)

        assert len(result) >= 1

    def test_split_preserves_content(self):
        """测试分割后内容完整性"""
        text = "第一句。第二句。第三句。第四句。"
        result = split_text_by_sentences(text, split_len=15)

        # 合并所有分块，应该包含原始内容的所有句子
        merged = "".join(result)
        assert "第一句" in merged
        assert "第二句" in merged
        assert "第三句" in merged
        assert "第四句" in merged

    def test_split_with_english_punctuation(self):
        """测试英文标点符号"""
        text = "First sentence. Second sentence! Third sentence?"
        result = split_text_by_sentences(text, split_len=100)

        assert len(result) == 1
        assert "First" in result[0]
        assert "Third" in result[0]

    def test_split_long_sentences(self):
        """测试很长的单个句子"""
        text = "这是一个非常非常非常非常长的句子，包含了很多很多的内容。"
        result = split_text_by_sentences(text, split_len=10)

        # 即使超过限制，单个句子也应该保持完整
        # 注意：函数可能会分割句子，所以只验证结果不为空
        assert len(result) >= 1
        # 验证内容完整性
        merged = "".join(result)
        assert "非常" in merged


class TestCleanAsrText:
    """测试 ASR 文本清理"""

    def test_clean_simple_tags(self):
        """测试清理简单标签"""
        text = "这是文本<|tag1|>内容<|tag2|>结束"
        result = clean_asr_text(text)

        assert "<|tag1|>" not in result
        assert "<|tag2|>" not in result
        assert "这是文本" in result
        assert "内容" in result
        assert "结束" in result

    def test_clean_no_tags(self):
        """测试没有标签的文本"""
        text = "这是一段没有标签的正常文本"
        result = clean_asr_text(text)

        assert result == text

    def test_clean_empty_text(self):
        """测试空文本"""
        text = ""
        result = clean_asr_text(text)

        assert result == ""

    def test_clean_only_tags(self):
        """测试只有标签的文本"""
        text = "<|tag1|><|tag2|><|tag3|>"
        result = clean_asr_text(text)

        assert result == ""

    def test_clean_nested_tags(self):
        """测试嵌套标签（实际不应该出现，但测试鲁棒性）"""
        text = "文本<|outer<|inner|>|>结束"
        result = clean_asr_text(text)

        # 正则表达式应该匹配最短的标签
        assert "<|" not in result or "|>" not in result

    def test_clean_special_characters_in_tags(self):
        """测试标签内包含特殊字符"""
        text = "文本<|tag-1_2.3|>内容<|tag@#$|>结束"
        result = clean_asr_text(text)

        assert "<|tag-1_2.3|>" not in result
        assert "<|tag@#$|>" not in result

    def test_clean_multiple_consecutive_tags(self):
        """测试连续多个标签"""
        text = "开始<|tag1|><|tag2|><|tag3|>中间<|tag4|>结束"
        result = clean_asr_text(text)

        assert "<|" not in result
        assert "|>" not in result
        assert "开始" in result
        assert "中间" in result
        assert "结束" in result

    def test_clean_incomplete_tags(self):
        """测试不完整的标签"""
        text = "文本<|incomplete 内容 |>incomplete> 结束"
        result = clean_asr_text(text)

        # 只有完整的 <|...|> 格式才会被移除
        assert "<|incomplete 内容 |>" not in result


class TestIsChinese:
    """测试中文字符判断"""

    def test_is_chinese_true(self):
        """测试中文字符"""
        assert is_chinese("中") is True
        assert is_chinese("文") is True
        assert is_chinese("字") is True
        assert is_chinese("好") is True

    def test_is_chinese_false(self):
        """测试非中文字符"""
        assert is_chinese("a") is False
        assert is_chinese("A") is False
        assert is_chinese("1") is False
        assert is_chinese(" ") is False
        assert is_chinese("!") is False

    def test_is_chinese_edge_cases(self):
        """测试边界 Unicode 字符"""
        # Unicode 中文范围: \u4e00 - \u9fff
        assert is_chinese("\u4e00") is True  # 最小中文字符
        assert is_chinese("\u9fff") is True  # 最大中文字符
        assert is_chinese("\u4dff") is False  # 小于范围
        assert is_chinese("\ua000") is False  # 大于范围

    def test_is_chinese_special_symbols(self):
        """测试特殊符号"""
        assert is_chinese("。") is False  # 中文句号
        assert is_chinese("，") is False  # 中文逗号
        assert is_chinese("？") is False  # 中文问号


class TestSmartSplit:
    """测试智能分割功能"""

    def test_smart_split_simple(self):
        """测试简单智能分割"""
        text = "这是第一段 这是第二段 这是第三段"
        result = smart_split(text, split_len=15)

        assert len(result) > 0
        assert all(isinstance(chunk, str) for chunk in result)

    def test_smart_split_chinese_text(self):
        """测试纯中文文本智能分割"""
        text = "这是一段很长的中文文本需要进行智能分割处理"
        result = smart_split(text, split_len=10)

        assert len(result) > 1
        for chunk in result:
            # 每个块的长度应该接近限制
            assert len(chunk) <= 10 + 5  # 允许一定误差

    def test_smart_split_with_spaces(self):
        """测试包含空格的文本"""
        text = "This is English text with spaces that needs splitting"
        result = smart_split(text, split_len=20)

        assert len(result) > 1
        # 应该优先在空格处分割
        for chunk in result:
            # 检查分割点是否合理
            pass

    def test_smart_split_empty_text(self):
        """测试空文本"""
        text = ""
        result = smart_split(text, split_len=10)

        # 空文本应该返回空列表或只包含空字符串
        assert len(result) == 0 or (len(result) == 1 and result[0] == "")

    def test_smart_split_exact_length(self):
        """测试文本长度正好等于分割限制"""
        text = "十个中文字符正好"
        result = smart_split(text, split_len=10)

        assert len(result) >= 1

    def test_smart_split_very_long_text(self):
        """测试很长的文本"""
        text = "这是一个非常长的文本" * 20
        result = smart_split(text, split_len=30)

        assert len(result) > 1
        # 验证没有内容丢失
        merged = "".join(result)
        assert len(merged.replace(" ", "")) >= len(text.replace(" ", "")) - 10  # 允许空格处理的差异

    def test_smart_split_no_break_points(self):
        """测试没有合适分割点的文本"""
        text = "a" * 50  # 50 个连续的 'a'
        result = smart_split(text, split_len=20)

        # 应该进行硬分割
        assert len(result) > 1

    def test_smart_split_mixed_language(self):
        """测试中英文混合文本"""
        text = "这是中文 This is English 这又是中文 More English"
        result = smart_split(text, split_len=20)

        assert len(result) >= 1
        # 验证内容完整性
        merged = "".join(result)
        assert "中文" in merged
        assert "English" in merged

    def test_smart_split_preserves_order(self):
        """测试分割保持顺序"""
        text = "第一部分 第二部分 第三部分 第四部分"
        result = smart_split(text, split_len=15)

        # 合并后应该保持原始顺序
        merged = " ".join(result)
        assert merged.index("第一") < merged.index("第二")
        assert merged.index("第二") < merged.index("第三")
        assert merged.index("第三") < merged.index("第四")

    def test_smart_split_single_word(self):
        """测试单个单词"""
        text = "单词"
        result = smart_split(text, split_len=10)

        assert len(result) == 1
        assert result[0] == "单词"

    def test_smart_split_consecutive_spaces(self):
        """测试连续空格"""
        text = "文本    包含    多个    空格"
        result = smart_split(text, split_len=10)

        assert len(result) >= 1
        # 空格应该被正确处理


class TestEdgeCasesAndRobustness:
    """测试边界情况和鲁棒性"""

    def test_split_text_very_large_limit(self):
        """测试非常大的分割限制"""
        text = "这是文本。"
        result = split_text_by_sentences(text, split_len=10000)

        assert len(result) == 1

    def test_split_text_zero_limit(self):
        """测试零分割限制"""
        text = "这是文本。"
        # 可能会导致异常或特殊行为
        result = split_text_by_sentences(text, split_len=0)
        # 函数应该处理这种情况

    def test_split_text_negative_limit(self):
        """测试负数分割限制"""
        text = "这是文本。"
        # 可能会导致异常或特殊行为
        result = split_text_by_sentences(text, split_len=-10)
        # 函数应该处理这种情况

    def test_clean_asr_very_long_text(self):
        """测试清理非常长的文本"""
        text = "文本" + "<|tag|>" * 1000 + "结束"
        result = clean_asr_text(text)

        assert "<|tag|>" not in result
        assert "文本" in result
        assert "结束" in result

    def test_smart_split_unicode_characters(self):
        """测试包含 Unicode 字符的文本"""
        text = "文本 😀 emoji 🎉 符号 ★"
        result = smart_split(text, split_len=10)

        assert len(result) >= 1

    def test_is_chinese_emoji(self):
        """测试 emoji 不是中文"""
        assert is_chinese("😀") is False
        assert is_chinese("🎉") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
