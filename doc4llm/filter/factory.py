"""
内容过滤器工厂
Content Filter Factory

根据URL或自动检测创建合适的内容过滤器
"""

from typing import Optional
from urllib.parse import urlparse
from .base import BaseContentFilter
from .standard import ContentFilter
from .enhanced import EnhancedContentFilter, create_filter


class FilterFactory:
    """
    内容过滤器工厂类

    根据不同的条件自动选择和创建合适的内容过滤器
    """

    # 文档框架的 URL 签名
    FRAMEWORK_SIGNATURES = {
        'mintlify': [
            'mintlify.app',
            'mintlify.com',
            '_mintlify',
        ],
        'docusaurus': [
            'docusaurus.io',
            '/docs/',  # 常见的文档路径
        ],
        'vitepress': [
            'vitepress.dev',
            'vitepress',
        ],
        'gitbook': [
            'gitbook.io',
            'app.gitbook.com',
        ],
    }

    @staticmethod
    def detect_framework_from_url(url: str) -> Optional[str]:
        """
        从 URL 检测文档框架

        Args:
            url: 网页 URL

        Returns:
            检测到的框架名称或 None
        """
        url_lower = url.lower()

        for framework, signatures in FilterFactory.FRAMEWORK_SIGNATURES.items():
            for signature in signatures:
                if signature in url_lower:
                    return framework

        return None

    @staticmethod
    def create(
        url: str = "",
        use_enhanced: bool = False,
        force_preset: Optional[str] = None,
        auto_detect: bool = True,
        **kwargs
    ) -> BaseContentFilter:
        """
        创建合适的内容过滤器

        Args:
            url: 目标 URL（用于自动检测）
            use_enhanced: 是否使用增强版过滤器
            force_preset: 强制使用特定的预设（'mintlify', 'docusaurus' 等）
            auto_detect: 是否自动检测文档框架
            **kwargs: 传递给过滤器的其他参数

        Returns:
            BaseContentFilter 实例

        Examples:
            >>> # 自动检测
            >>> filter = FilterFactory.create(url="https://docs.example.com")

            >>> # 强制使用增强版
            >>> filter = FilterFactory.create(use_enhanced=True)

            >>> # 指定预设
            >>> filter = FilterFactory.create(force_preset='mintlify')

            >>> # 使用原始过滤器
            >>> filter = FilterFactory.create(use_enhanced=False)
        """
        # 如果强制指定了预设，使用增强版过滤器
        if force_preset:
            return create_filter(preset=force_preset, auto_detect_framework=auto_detect, **kwargs)

        # 如果明确要求使用增强版
        if use_enhanced:
            # 检测框架
            detected_framework = None
            if url and auto_detect:
                detected_framework = FilterFactory.detect_framework_from_url(url)

            return create_filter(
                preset=detected_framework,
                auto_detect_framework=auto_detect,
                **kwargs
            )

        # 默认使用原始过滤器
        return ContentFilter(**kwargs)

    @staticmethod
    def create_for_url(url: str, **kwargs) -> BaseContentFilter:
        """
        为特定 URL 创建最合适的过滤器（智能推荐）

        Args:
            url: 目标 URL
            **kwargs: 其他参数

        Returns:
            BaseContentFilter 实例
        """
        # 检测框架
        framework = FilterFactory.detect_framework_from_url(url)

        # 如果检测到已知的文档框架，使用增强版
        if framework:
            print(f"检测到文档框架 '{framework}'，使用增强版过滤器")
            return create_filter(preset=framework, auto_detect_framework=True, **kwargs)

        # 对于其他 URL，使用原始过滤器
        print("使用标准内容过滤器")
        return ContentFilter(**kwargs)


# 便捷函数
def create_filter_auto(url: str = "", use_enhanced: bool = False, **kwargs) -> BaseContentFilter:
    """
    自动创建合适的过滤器的便捷函数

    Args:
        url: 目标 URL
        use_enhanced: 是否优先使用增强版
        **kwargs: 其他参数

    Returns:
        BaseContentFilter 实例
    """
    return FilterFactory.create(url=url, use_enhanced=use_enhanced, **kwargs)


def create_filter_for_url(url: str, **kwargs) -> BaseContentFilter:
    """
    为特定 URL 创建最合适过滤器的便捷函数

    Args:
        url: 目标 URL
        **kwargs: 其他参数

    Returns:
        BaseContentFilter 实例
    """
    return FilterFactory.create_for_url(url, **kwargs)
