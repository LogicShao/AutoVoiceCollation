"""
处理历史管理模块
用于跟踪已处理的音视频文件，避免重复处理
"""

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.utils.logging.logger import get_logger
from src.utils.config.manager import get_config

logger = get_logger(__name__)


@dataclass
class ProcessRecord:
    """处理记录数据类"""

    identifier: str  # 唯一标识符（BV号、文件hash等）
    record_type: str  # 类型：bilibili, local_audio, local_video
    url: Optional[str]  # B站链接（如果是B站视频）
    title: str  # 视频/文件标题
    output_dir: str  # 输出目录
    last_processed: str  # 最后处理时间（ISO格式）
    config: Dict[str, Any]  # 处理配置
    outputs: Dict[str, str]  # 输出文件路径
    process_count: int = 1  # 处理次数

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessRecord":
        """从字典创建实例"""
        return cls(**data)


class ProcessHistoryManager:
    """处理历史管理器（单例模式）"""

    _instance = None
    _initialized = False

    def __new__(cls, history_file: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, history_file: str = None):
        # 避免重复初始化
        if self._initialized:
            return

        # 默认历史文件路径
        if history_file is None:
            try:
                # 优先使用配置系统的输出目录
                config = get_config()
                history_file = config.paths.output_dir / ".process_history.json"
            except Exception as e:
                logger.warning(f"无法获取配置，使用默认输出目录: {e}")
                # 正确的相对路径：向上4层到项目根目录
                # __file__ -> manager.py
                # parent -> history/
                # parent -> core/
                # parent -> src/
                # parent -> 项目根目录
                project_root = Path(__file__).parent.parent.parent.parent
                history_file = project_root / "out" / ".process_history.json"

        self.history_file = Path(history_file)
        self.version = "1.0"
        self.records: Dict[str, ProcessRecord] = {}

        # 确保历史文件目录存在
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        # 加载历史记录
        self._load()
        self._initialized = True
        logger.info(f"处理历史管理器已初始化，历史文件: {self.history_file}")

    def _load(self):
        """从文件加载历史记录"""
        if not self.history_file.exists():
            logger.info("历史文件不存在，创建新的历史记录")
            self._save()
            return

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.version = data.get("version", "1.0")
            records_data = data.get("records", {})

            # 将字典转换为 ProcessRecord 对象
            self.records = {
                identifier: ProcessRecord.from_dict(record_data)
                for identifier, record_data in records_data.items()
            }

            logger.info(f"成功加载 {len(self.records)} 条历史记录")
        except Exception as e:
            logger.error(f"加载历史记录失败: {e}", exc_info=True)
            # 创建备份
            if self.history_file.exists():
                backup_path = self.history_file.with_suffix(".json.backup")
                self.history_file.rename(backup_path)
                logger.warning(f"已创建备份: {backup_path}")
            self.records = {}

    def _save(self):
        """保存历史记录到文件"""
        try:
            data = {
                "version": self.version,
                "records": {
                    identifier: record.to_dict()
                    for identifier, record in self.records.items()
                },
            }

            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.debug(f"历史记录已保存: {len(self.records)} 条")
        except Exception as e:
            logger.error(f"保存历史记录失败: {e}", exc_info=True)

    @staticmethod
    def extract_bilibili_id(url: str) -> Optional[str]:
        """
        从B站链接中提取视频ID（BV号或AV号）
        支持多种B站链接格式
        """
        if not url:
            return None

        # 提取 BV 号
        bv_match = re.search(r"BV[a-zA-Z0-9]+", url)
        if bv_match:
            return bv_match.group(0)

        # 提取 AV 号
        av_match = re.search(r"av(\d+)", url, re.IGNORECASE)
        if av_match:
            return f"av{av_match.group(1)}"

        return None

    @staticmethod
    def generate_file_identifier(file_path: str) -> str:
        """
        为本地文件生成唯一标识符
        使用文件路径、大小和修改时间的组合生成 MD5
        """
        try:
            path = Path(file_path)
            if not path.exists():
                # 如果文件不存在，仅使用文件名
                return hashlib.md5(path.name.encode("utf-8")).hexdigest()[:16]

            # 使用文件名、大小和修改时间生成标识符
            file_info = f"{path.name}_{path.stat().st_size}_{path.stat().st_mtime}"
            return hashlib.md5(file_info.encode("utf-8")).hexdigest()[:16]
        except Exception as e:
            logger.error(f"生成文件标识符失败: {e}")
            # 降级方案：仅使用文件名
            return hashlib.md5(Path(file_path).name.encode("utf-8")).hexdigest()[:16]

    def check_processed(self, identifier: str) -> bool:
        """检查标识符是否已被处理过"""
        return identifier in self.records

    def get_record(self, identifier: str) -> Optional[ProcessRecord]:
        """获取处理记录"""
        return self.records.get(identifier)

    def add_record(self, record: ProcessRecord):
        """添加或更新处理记录"""
        identifier = record.identifier

        if identifier in self.records:
            # 更新现有记录
            existing = self.records[identifier]
            existing.output_dir = record.output_dir
            existing.last_processed = record.last_processed
            existing.config = record.config
            existing.outputs = record.outputs
            existing.process_count += 1
            logger.info(
                f"更新处理记录: {identifier}，处理次数: {existing.process_count}"
            )
        else:
            # 添加新记录
            self.records[identifier] = record
            logger.info(f"添加新处理记录: {identifier}")

        # 保存到文件
        self._save()

    def delete_record(self, identifier: str) -> bool:
        """删除处理记录"""
        if identifier in self.records:
            del self.records[identifier]
            self._save()
            logger.info(f"删除处理记录: {identifier}")
            return True
        return False

    def get_all_records(self) -> List[ProcessRecord]:
        """获取所有处理记录，按时间倒序排列"""
        records = list(self.records.values())
        records.sort(key=lambda r: r.last_processed, reverse=True)
        return records

    def create_record_from_bilibili(
        self,
        url: str,
        title: str,
        output_dir: str,
        config: Dict[str, Any],
        outputs: Dict[str, str],
    ) -> ProcessRecord:
        """
        从B站视频信息创建处理记录

        Args:
            url: B站视频链接
            title: 视频标题
            output_dir: 输出目录
            config: 处理配置（ASR模型、LLM配置等）
            outputs: 输出文件路径字典

        Returns:
            ProcessRecord: 创建的处理记录
        """
        identifier = self.extract_bilibili_id(url)
        if not identifier:
            # 如果无法提取BV号，使用URL的hash作为标识符
            identifier = hashlib.md5(url.encode("utf-8")).hexdigest()[:16]
            logger.warning(f"无法从URL提取BV号，使用hash作为标识符: {identifier}")

        record = ProcessRecord(
            identifier=identifier,
            record_type="bilibili",
            url=url,
            title=title,
            output_dir=output_dir,
            last_processed=datetime.now().isoformat(),
            config=config,
            outputs=outputs,
            process_count=1,
        )

        self.add_record(record)
        return record

    def create_record_from_local_file(
        self,
        file_path: str,
        file_type: str,
        title: str,
        output_dir: str,
        config: Dict[str, Any],
        outputs: Dict[str, str],
    ) -> ProcessRecord:
        """
        从本地文件信息创建处理记录

        Args:
            file_path: 本地文件路径
            file_type: 文件类型（local_audio 或 local_video）
            title: 文件标题
            output_dir: 输出目录
            config: 处理配置
            outputs: 输出文件路径字典

        Returns:
            ProcessRecord: 创建的处理记录
        """
        identifier = self.generate_file_identifier(file_path)

        record = ProcessRecord(
            identifier=identifier,
            record_type=file_type,
            url=None,
            title=title,
            output_dir=output_dir,
            last_processed=datetime.now().isoformat(),
            config=config,
            outputs=outputs,
            process_count=1,
        )

        self.add_record(record)
        return record

    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        total_count = len(self.records)
        bilibili_count = sum(
            1 for r in self.records.values() if r.record_type == "bilibili"
        )
        local_audio_count = sum(
            1 for r in self.records.values() if r.record_type == "local_audio"
        )
        local_video_count = sum(
            1 for r in self.records.values() if r.record_type == "local_video"
        )
        total_process_count = sum(r.process_count for r in self.records.values())

        return {
            "total_records": total_count,
            "bilibili_videos": bilibili_count,
            "local_audios": local_audio_count,
            "local_videos": local_video_count,
            "total_processes": total_process_count,
        }


def get_history_manager() -> ProcessHistoryManager:
    """获取处理历史管理器单例"""
    return ProcessHistoryManager()
