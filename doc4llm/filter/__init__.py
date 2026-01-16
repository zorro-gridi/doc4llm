"""
内容过滤器包
Content Filter Package

提供网页内容过滤和清理功能，支持传统网站和现代文档站点
"""

from .base import BaseContentFilter, filter_by_end_markers
from .standard import ContentFilter
from .enhanced import EnhancedContentFilter, create_filter
from .factory import FilterFactory, create_filter_auto, create_filter_for_url
from .config import (
    # 配置常量 - 内容过滤器
    SEMANTIC_NON_CONTENT_SELECTORS,
    GENERAL_NON_CONTENT_SELECTORS,
    FUZZY_KEYWORDS,
    LOG_LEVELS,
    MEANINGLESS_CONTENT,
    CODE_CONTAINER_SELECTORS,
    CONTENT_PRESERVE_SELECTORS,
    CONTENT_END_MARKERS,
    DOCUMENTATION_FRAMEWORK_PRESETS,
    DEFAULT_CONFIG,
    # 配置常量 - TOC URL 过滤器
    TOC_CLASS_PATTERNS,
    TOC_LINK_CLASS_PATTERNS,
    TOC_PARENT_CLASS_PATTERNS,
    CONTENT_AREA_PATTERNS,
    NON_TOC_LINK_PATTERNS,
    TOC_END_MARKERS,
    # 工具函数和类
    merge_selectors,
    get_filter_config,
    FilterConfigLoader,
    get_toc_filter_config,
    TocFilterConfigLoader,
)

__all__ = [
    # 基类
    'BaseContentFilter',

    # 统一后处理工具函数
    'filter_by_end_markers',

    # 标准过滤器
    'ContentFilter',

    # 增强版过滤器
    'EnhancedContentFilter',
    'create_filter',

    # 工厂
    'FilterFactory',
    'create_filter_auto',
    'create_filter_for_url',

    # 配置常量 - 内容过滤器
    'SEMANTIC_NON_CONTENT_SELECTORS',
    'GENERAL_NON_CONTENT_SELECTORS',
    'FUZZY_KEYWORDS',
    'LOG_LEVELS',
    'MEANINGLESS_CONTENT',
    'CODE_CONTAINER_SELECTORS',
    'CONTENT_PRESERVE_SELECTORS',
    'CONTENT_END_MARKERS',
    'DOCUMENTATION_FRAMEWORK_PRESETS',
    'DEFAULT_CONFIG',

    # 配置常量 - TOC URL 过滤器
    'TOC_CLASS_PATTERNS',
    'TOC_LINK_CLASS_PATTERNS',
    'TOC_PARENT_CLASS_PATTERNS',
    'CONTENT_AREA_PATTERNS',
    'NON_TOC_LINK_PATTERNS',
    'TOC_END_MARKERS',

    # 工具函数和类
    'merge_selectors',
    'get_filter_config',
    'FilterConfigLoader',
    'get_toc_filter_config',
    'TocFilterConfigLoader',
]

__version__ = '2.1.0'
