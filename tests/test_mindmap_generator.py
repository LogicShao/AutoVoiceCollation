import asyncio
from unittest.mock import patch

import pytest

from src.services.mindmap import MindMapDepth, generate_mindmap


def _tree_depth(node) -> int:
    if not node.children:
        return 1
    return 1 + max(_tree_depth(child) for child in node.children)


def test_generate_mindmap_applies_all_depth_profiles():
    text = "这是一段用于生成思维导图的测试文本。" * 700
    captured_instructions = []

    async def fake_query_llm(params):
        captured_instructions.append(params.system_instruction)
        if "请求值：low" in params.system_instruction:
            return """
            {"title": "课程", "children": [
              {"title": "主题", "children": [{"title": "要点"}]}
            ]}
            """
        if "请求值：medium" in params.system_instruction:
            return """
            {"title": "课程", "children": [
              {"title": "主题", "children": [
                {"title": "子主题", "children": [{"title": "细节"}]}
              ]}
            ]}
            """
        if "请求值：high" in params.system_instruction:
            return """
            {"title": "课程", "children": [
              {"title": "主题", "children": [
                {"title": "子主题", "children": [
                  {"title": "细节", "children": [{"title": "证据"}]}
                ]}
              ]}
            ]}
            """
        return """
        {"title": "课程", "children": [
          {"title": "自动", "children": [
            {"title": "主题", "children": [{"title": "细节"}, {"title": "例子"}]}
          ]}
        ]}
        """

    with patch("src.services.mindmap.generator.query_llm_async", new=fake_query_llm):
        outputs = {
            depth: asyncio.run(generate_mindmap(text=text, title="测试", depth=depth))
            for depth in ("low", "medium", "high", "auto")
        }

    assert outputs["low"].depth == MindMapDepth.LOW
    assert outputs["medium"].depth == MindMapDepth.MEDIUM
    assert outputs["high"].depth == MindMapDepth.HIGH
    assert outputs["auto"].depth == MindMapDepth.AUTO

    node_counts = {depth: output.node_count for depth, output in outputs.items()}
    tree_depths = {depth: _tree_depth(output.root) for depth, output in outputs.items()}

    assert node_counts["low"] < node_counts["medium"] < node_counts["high"]
    assert tree_depths["low"] < tree_depths["medium"] < tree_depths["high"]
    assert node_counts["auto"] != node_counts["low"]
    assert tree_depths["auto"] != tree_depths["low"]

    assert "请求值：low" in captured_instructions[0]
    assert "最多 2 层" in captured_instructions[0]
    assert "请求值：medium" in captured_instructions[1]
    assert "最多 3 层" in captured_instructions[1]
    assert "请求值：high" in captured_instructions[2]
    assert "最多 4 层" in captured_instructions[2]
    assert "请求值：auto" in captured_instructions[3]
    assert "实际档位：high" in captured_instructions[3]


def test_generate_mindmap_rejects_unknown_depth():
    with pytest.raises(ValueError, match="Unsupported mindmap depth"):
        asyncio.run(generate_mindmap(text="测试文本", title="测试", depth="unknown"))
