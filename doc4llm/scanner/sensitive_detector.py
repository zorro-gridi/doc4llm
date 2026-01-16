"""
敏感信息检测模块
使用正则表达式检测敏感信息
"""
import re
from .utils import DebugMixin


class SensitiveDetector(DebugMixin):
    """敏感信息检测类"""

    def __init__(self, sensitive_patterns, debug_mode=False):
        self.sensitive_patterns = sensitive_patterns
        self.debug_mode = debug_mode

    def detect(self, content):
        """检测响应中的敏感信息 - 返回结构化格式"""
        try:
            if not content:
                self._debug_print("内容为空，跳过敏感信息检测")
                return []

            self._debug_print("开始敏感信息检测")

            text_content = self._process_content(content)
            if text_content is None:
                return []

            detected = []

            for name, pattern in self.sensitive_patterns.items():
                detected_item = self._detect_pattern(name, pattern, text_content)
                if detected_item:
                    detected.append(detected_item)

            self._debug_print(f"敏感信息检测完成，共发现 {len(detected)} 种敏感信息")

            return detected
        except Exception as e:
            self._debug_print(f"敏感信息检测过程中出错: {type(e).__name__}: {e}")
            return []

    def _process_content(self, content):
        """处理内容，确保是字符串格式"""
        try:
            return content.decode('utf-8', 'ignore') if isinstance(content, bytes) else content
        except Exception as e:
            self._debug_print(f"内容解码失败: {type(e).__name__}: {e}")
            return str(content) if content else ""

    def _detect_pattern(self, name, pattern, text_content):
        """检测单个敏感信息模式"""
        try:
            matches = re.findall(pattern, text_content)
            if matches:
                return self._create_detected_item(name, matches)
            else:
                pass
        except re.error as e:
            self._debug_print(f"正则表达式错误 ({name}): {str(e)}")
            return None
        except Exception as e:
            self._debug_print(f"处理敏感信息模式时出错 ({name}): {type(e).__name__}: {e}")
            return None
        return None

    def _create_detected_item(self, name, matches):
        """创建检测结果项"""
        # 去重并获取样本
        unique_matches = set(matches)
        count = len(unique_matches)

        # 获取样本
        samples = list(unique_matches)

        # 构建结构化结果
        detected_item = {
            'type': name,
            'count': count,
            'samples': samples,
            'total': len(unique_matches)
        }

        self._debug_print(f"发现敏感信息: {name} x{count} 个样本")
        return detected_item
