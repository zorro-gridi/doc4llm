"""
通用工具模块
提供调试输出、异常处理等通用功能
"""
import hashlib
import logging
import sys
from threading import Lock

# 尝试导入colorama
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLOR_SUPPORT = True
except ImportError:
    COLOR_SUPPORT = False
    Fore = Style = type('', (), {'__getattr__': lambda *args: ''})()

# 全局输出锁
output_lock = Lock()


def handle_exceptions(func):
    """异常处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 尝试调用对象的_debug_print方法输出异常信息
            if args and hasattr(args[0], '_debug_print'):
                args[0]._debug_print(f"异常: {str(e)}")
            elif args and hasattr(args[0], 'debug_mode') and args[0].debug_mode:
                # 如果对象有debug_mode属性但没有_debug_print方法
                print(f"{Fore.MAGENTA}[DEBUG] 异常: {str(e)}{Style.RESET_ALL}")
            return None
    return wrapper


class DebugMixin:
    """调试输出 Mixin 类"""

    def __init__(self, debug_mode=False):
        self.debug_mode = debug_mode

    def _debug_print(self, message):
        """调试信息输出"""
        if hasattr(self, 'debug_mode') and self.debug_mode:
            debug_prefix = f"{Fore.MAGENTA}[DEBUG]{Style.RESET_ALL}"
            print(f"{debug_prefix} {message}")
            try:
                logging.debug(message)
            except Exception as e:
                print(f"Debug输出异常: {e}")
                pass


class BloomFilter:
    """布隆过滤器 - 用于URL去重"""

    def __init__(self, expected_elements=1000000, false_positive_rate=0.001):
        """
        初始化布隆过滤器

        Args:
            expected_elements: 预期元素数量
            false_positive_rate: 误判率
        """
        # 计算需要的位数和哈希函数数量
        import math
        self.size = self._calculate_size(expected_elements, false_positive_rate)
        self.hash_count = self._calculate_hash_count(self.size, expected_elements)

        # 使用位图存储（使用整数作为位数组）
        self.bit_array = 0
        self.size_bits = self.size

        # 元素计数
        self.element_count = 0

    def _calculate_size(self, n, p):
        """计算需要的位数"""
        import math
        return int(-(n * math.log(p)) / (math.log(2) ** 2)) + 1

    def _calculate_hash_count(self, m, n):
        """计算哈希函数数量"""
        import math
        return int((m / n) * math.log(2)) + 1

    def _get_hashes(self, item):
        """生成多个哈希值"""
        item_str = str(item).encode('utf-8')
        hashes = []

        # 使用不同的哈希算法生成多个哈希值
        hash_algos = ['md5', 'sha1', 'sha256']

        for i in range(self.hash_count):
            # 组合哈希算法和索引生成不同的哈希值
            algo = hash_algos[i % len(hash_algos)]
            hash_obj = hashlib.new(algo)
            hash_obj.update(item_str + str(i).encode('utf-8'))
            hash_value = int(hash_obj.hexdigest(), 16)
            hashes.append(hash_value % self.size_bits)

        return hashes

    def add(self, item):
        """添加元素到布隆过滤器"""
        for hash_value in self._get_hashes(item):
            # 设置对应的位
            self.bit_array |= (1 << hash_value)
        self.element_count += 1

    def __contains__(self, item):
        """检查元素是否可能在布隆过滤器中"""
        for hash_value in self._get_hashes(item):
            # 检查对应的位是否为1
            if not (self.bit_array & (1 << hash_value)):
                return False
        return True

    def contains(self, item):
        """检查元素是否可能在布隆过滤器中（方法版本）"""
        return item in self

    def __len__(self):
        """返回元素计数"""
        return self.element_count

    def clear(self):
        """清空布隆过滤器"""
        self.bit_array = 0
        self.element_count = 0
