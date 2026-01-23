"""
内容过滤器统一配置模块
Content Filter Unified Configuration

此模块集中管理所有内容过滤器的预定义标签列表和配置参数。
所有过滤器的默认选择器和关键词都在此定义，确保配置统一且易于维护。

Author: Claude Code
Date: 2025-01-16
"""

from typing import List, Dict, Any, Optional


# ============================================================================
# 非正文内容选择器配置
# ============================================================================

#: 高置信度非正文内容选择器（语义化标签和 ARIA 角色）
# 这些标签明确表示非正文内容，移除优先级最高
SEMANTIC_NON_CONTENT_SELECTORS = [
    # HTML5 语义化标签
    'aside',      # 侧边栏
    'nav',        # 导航菜单
    'footer',     # 页脚
    'header',     # 页头
    'navigation', # 导航区域（旧式写法）
    'banner',     # 横幅区域
    'contentinfo', # 内容信息区域
    'complementary', # 补充内容区域

    # ARIA 角色属性
    '[role="navigation"]',    # 导航
    '[role="banner"]',        # 横幅
    '[role="complementary"]', # 补充内容
    '[role="contentinfo"]',   # 内容信息
    '[role="directory"]',     # 目录
]


#: 通用非正文内容选择器（基于常见 ID 和 Class 模式）
# 这些是基于常见命名规范的选择器，适用于大多数网站
GENERAL_NON_CONTENT_SELECTORS = [
    # Sidebar 相关 - 侧边栏
    '#sidebar', '.sidebar', '.side-bar', '.side-panel',
    '[class*="sidebar"]', '[class*="sideBar"]', '[class*="side-bar"]',

    # 导航相关 - 导航菜单和面包屑
    '#toc', '#table-of-contents', '#index', '#directory',
    '#menu', '#navigation', '#ad', '#footer', '#header', '#breadcrumb',
    '.nav', '.navigation', '.navbar', '.nav-bar',
    '[class*="navigation"]', '[class*="navbar"]', '[class*="nav-bar"]',
    '[class*="breadcrumb"]', '[class*="breadcrumbs"]',
    '[class*="menu"]', '[class*="pagination"]',

    # TOC（目录）
    '.toc', '.table-of-contents', '.toc-container',
    '[class*="toc"]', '[class*="TableOfContents"]',

    # 页脚
    '.footer', '.page-footer', '[class*="footer"]',

    # 广告和弹窗
    '.ad', '.advertisement', '.popup', '.modal', '.banner',
    '[class*="popup"]', '[class*="modal"]', '[class*="banner"]',

    # 小部件和工具
    '.widget', '.toolbox', '.toolbar',
    '[class*="widget"]', '[class*="toolbar"]',

    # 按钮和表单
    '.btn', '[class*="btn-"]', '[class*="button"]',

    # 下一页/上一页导航
    '.prev', '.next', '.pagination', '.pager',
    '[class*="prevnext"]', '[class*="prev-next"]',
    '[class*="pagination"]',

    # 搜索相关
    '.search', '[class*="search"]',

    # 反馈相关
    '.feedback', '[class*="feedback"]',
    '.was-this-helpful', '[class*="helpful"]',

    # 社交分享
    '.share', '[class*="share"]', '[class*="social"]',

    # 代码编辑器/控制台（除非在代码块中）
    '.console', '.terminal', '[class*="console"]',

    # Mintlify 特定标识
    '.toclimit-2', '.toclimit-3', '.mw-workspace-container',
    '[class*="mintlify-"]', '.mx-auto.flex', '.sticky',

    # 通用提示
    '.popup', '.tooltip', '[class*="new-right"]',
]


#: 模糊匹配关键词
# 用于匹配 class 或 id 中包含这些关键词的元素
FUZZY_KEYWORDS = [
    # 侧边栏和导航
    'sidebar', 'navigation', 'navbar', 'menu', 'modal',

    # 交互元素
    'cookie', 'notification', 'popup', 'tooltip',

    # 分页和导航
    'pagination', 'breadcrumb', 'footer', 'header',
    'prevnext', 'feedback', 'share',
]


# ============================================================================
# 需要保留的内容选择器
# ============================================================================

#: 正文内容保留选择器
# 这些选择器标记的元素应该被优先保留作为正文内容
CONTENT_PRESERVE_SELECTORS = [
    'article',                      # 文章主体
    'main',                         # 主要内容
    '[role="main"]',                # 主要内容角色
    '.content',                     # 内容区域
    '.post-content',                # 文章内容
    '.article-content',             # 文章正文
    '.markdown-body',               # Markdown 渲染结果
    '.prose',                       # Prose（文学/正文）
    '.mdx',                         # MDX 内容
    '[class*="main-content"]',      # 主内容（模糊匹配）
    '[class*="article-body"]',      # 文章正文（模糊匹配）
    '[class*="post-body"]',         # 帖子正文（模糊匹配）
]


#: 强制删除选择器（优先级最高）
# 这些选择器匹配的元素会被强制删除，即使它们在保护区域内
FORCE_REMOVE_SELECTORS = [
    # 默认为空，由用户根据需要配置
]

#: 级联保护标签黑名单
# 这些标签在级联保护检查时会被忽略，即使位于保护区域内也可以被删除
PROTECTED_TAG_BLACKLIST = [
    'footer',     # 页脚
    'aside',      # 侧边栏
    'nav',        # 导航
]


# ============================================================================
# 日志过滤配置
# ============================================================================

#: Python logging 日志级别标识
# 用于识别和过滤代码块中的日志输出
LOG_LEVELS = [
    r'INFO:', r'info:', r'Info:',
    r'DEBUG:', r'debug:', r'Debug:',
    r'WARNING:', r'warning:', r'Warning:',
    r'ERROR:', r'error:', r'Error:',
    r'CRITICAL:', r'critical:', r'Critical:',
]


#: 代码块容器选择器
# 用于查找包含代码的容器元素
CODE_CONTAINER_SELECTORS = [
    'code', 'pre',
    '[class*="code"]', '[class*="pre"]',
    '[class*="snippet"]', '[class*="terminal"]',
    '[class*="console"]',
]


# ============================================================================
# 内容清理配置
# ============================================================================

#: 无意义内容列表
# 这些文本内容在提取正文时应该被移除
MEANINGLESS_CONTENT = [
    'Skip to main content',
    '__Back to top',
    'Back to top',
    'Table of contents',
    'On this page',
]


#: 正文内容结束标识
# 遇到这些模式后停止提取（通常是文档末尾的导航元素）
CONTENT_END_MARKERS = [
    # 匹配可能包含换行符的标题格式
    r'##?\s*\n*\s*Next steps?',      # 匹配 ## Next steps (可能中间有换行)
    r'##?\s*\n*\s*Further reading',  # 匹配 ## Further reading
    r'##?\s*\n*\s*See also',         # 匹配 ## See also
    r'##?\s*\n*\s*References',       # 匹配 ## References
    r'##?\s*\n*\s*Related',          # 匹配 ## Related
    r'---+\s*\n*\s*Next steps?',     # 分隔线后的 Next steps
    r'Was this (page|article|doc) helpful\?',  # 反馈问题
    r'Did you (find|like) this',     # 另一种反馈问题
]


# ============================================================================
# 文档框架预设配置
# ============================================================================

#: 文档框架预设
# 针对常见文档框架的特定选择器配置
DOCUMENTATION_FRAMEWORK_PRESETS: Dict[str, Dict[str, List[str]]] = {
    'mintlify': {
        'content_selectors': [
            'article',
            '[class*="content"]',
            '[class*="markdown"]',
            '[class*="prose"]',
        ],
        'exclude_selectors': [
            '[class*="sidebar"]',
            '[class*="navigation"]',
            '[class*="navbar"]',
            '[class*="pagination"]',
            '[class*="prevnext"]',
            '[class*="footer"]',
            '[class*="toc"]',
            '[class*="mintlify-"]',
            '.mx-auto.flex',
            '.sticky',
        ]
    },
    'docusaurus': {
        'content_selectors': [
            'article',
            '[class*="docMainContainer"]',
            '[class*="markdown"]',
        ],
        'exclude_selectors': [
            '[class*="sidebar"]',
            '[class*="navbar"]',
            '[class*="footer"]',
            '[class*="toc"]',
            '.menu',
            '.table-of-contents',
        ]
    },
    'vitepress': {
        'content_selectors': [
            '.VPDoc',
            '[class*="content"]',
        ],
        'exclude_selectors': [
            '.VPNav',
            '.VPSidebar',
            '.VPFooter',
            '.VPLocalNav',
        ]
    },
    'gitbook': {
        'content_selectors': [
            '.gitbook-content',
            '[class*="page-content"]',
        ],
        'exclude_selectors': [
            '.gitbook-sidebar',
            '.gitbook-navigation',
            '[class*="navigation"]',
        ]
    }
}


# ============================================================================
# 配置合并工具函数
# ============================================================================

def merge_selectors(
    base_selectors: List[str],
    custom_selectors: Optional[List[str]] = None,
    mode: str = 'extend'
) -> List[str]:
    """
    合并选择器列表

    Args:
        base_selectors: 基础选择器列表
        custom_selectors: 自定义选择器列表
        mode: 合并模式
            - 'extend': 扩展模式，保留基础选择器并添加自定义选择器（默认）
            - 'replace': 替换模式，仅使用自定义选择器

    Returns:
        合并后的选择器列表
    """
    if custom_selectors is None:
        return base_selectors.copy()

    if mode == 'replace':
        return custom_selectors.copy()

    # extend 模式：先添加基础选择器，再添加自定义选择器
    merged = base_selectors.copy()
    merged.extend(custom_selectors)
    return merged


def get_filter_config(
    preset: Optional[str] = None,
    custom_non_content_selectors: Optional[List[str]] = None,
    custom_fuzzy_keywords: Optional[List[str]] = None,
    custom_log_levels: Optional[List[str]] = None,
    custom_meaningless_content: Optional[List[str]] = None,
    custom_force_remove_selectors: Optional[List[str]] = None,
    custom_protected_tag_blacklist: Optional[List[str]] = None,
    merge_mode: str = 'extend'
) -> Dict[str, Any]:
    """
    获取过滤器配置

    Args:
        preset: 文档框架预设名称 ('mintlify', 'docusaurus', 'vitepress', 'gitbook')
        custom_non_content_selectors: 自定义非正文选择器
        custom_fuzzy_keywords: 自定义模糊匹配关键词
        custom_log_levels: 自定义日志级别
        custom_meaningless_content: 自定义无意义内容
        custom_force_remove_selectors: 自定义强制删除选择器（优先级最高）
        custom_protected_tag_blacklist: 自定义级联保护标签黑名单
        merge_mode: 合并模式 ('extend' 或 'replace')

    Returns:
        包含所有配置的字典
    """
    # 合并基础选择器
    non_content_selectors = merge_selectors(
        SEMANTIC_NON_CONTENT_SELECTORS + GENERAL_NON_CONTENT_SELECTORS,
        custom_non_content_selectors,
        merge_mode
    )

    # 应用框架预设
    if preset and preset in DOCUMENTATION_FRAMEWORK_PRESETS:
        preset_config = DOCUMENTATION_FRAMEWORK_PRESETS[preset]
        non_content_selectors.extend(preset_config['exclude_selectors'])

    return {
        'non_content_selectors': non_content_selectors,
        'fuzzy_keywords': merge_selectors(
            FUZZY_KEYWORDS,
            custom_fuzzy_keywords,
            merge_mode
        ),
        'log_levels': merge_selectors(
            LOG_LEVELS,
            custom_log_levels,
            merge_mode
        ),
        'meaningless_content': merge_selectors(
            MEANINGLESS_CONTENT,
            custom_meaningless_content,
            merge_mode
        ),
        'content_end_markers': CONTENT_END_MARKERS,
        'content_preserve_selectors': CONTENT_PRESERVE_SELECTORS,
        'code_container_selectors': CODE_CONTAINER_SELECTORS,
        'force_remove_selectors': merge_selectors(
            FORCE_REMOVE_SELECTORS,
            custom_force_remove_selectors,
            merge_mode
        ),
        'protected_tag_blacklist': merge_selectors(
            PROTECTED_TAG_BLACKLIST,
            custom_protected_tag_blacklist,
            merge_mode
        ),
    }


# ============================================================================
# 从配置文件加载的工具类
# ============================================================================

class FilterConfigLoader:
    """
    从 config.json 加载过滤器配置的工具类

    允许用户通过 config.json 自定义过滤标签列表
    """

    @staticmethod
    def load_from_config(config_dict: Dict[str, Any], preset: Optional[str] = None) -> Dict[str, Any]:
        """
        从配置字典加载过滤器配置

        Args:
            config_dict: 包含 content_filter 配置的字典
            preset: 文档框架预设（如果配置文件中指定了 documentation_preset，则优先使用配置文件的值）

        Returns:
            过滤器配置字典
        """
        # 从配置文件中读取自定义选择器（如果存在）
        filter_config = config_dict.get('content_filter', {})

        # 配置文件中的 preset 优先级高于传入的参数
        actual_preset = filter_config.get('documentation_preset', preset)

        # 获取基础配置
        config = get_filter_config(
            preset=actual_preset,
            custom_non_content_selectors=filter_config.get('non_content_selectors'),
            custom_fuzzy_keywords=filter_config.get('fuzzy_keywords'),
            custom_log_levels=filter_config.get('log_levels'),
            custom_meaningless_content=filter_config.get('meaningless_content'),
            custom_force_remove_selectors=filter_config.get('force_remove_selectors'),
            custom_protected_tag_blacklist=filter_config.get('protected_tag_blacklist'),
            merge_mode=filter_config.get('merge_mode', 'extend')
        )

        # 处理可选的高级配置参数
        # 如果配置文件中指定了这些参数且非空，则覆盖默认值
        if filter_config.get('content_end_markers'):
            config['content_end_markers'] = filter_config.get('content_end_markers')

        if filter_config.get('content_preserve_selectors'):
            config['content_preserve_selectors'] = filter_config.get('content_preserve_selectors')

        if filter_config.get('code_container_selectors'):
            config['code_container_selectors'] = filter_config.get('code_container_selectors')

        return config


# ============================================================================
# TOC URL 过滤配置 (DocUrlCrawler 使用)
# ============================================================================

#: TOC 容器的 CSS 类名/ID 模式（白名单）
#: 用于识别目录（TOC）容器的 class 和 id 属性
TOC_CLASS_PATTERNS = [
    'toc', 'table-of-contents', 'navigation',
    'sidebar', 'menu', 'directory', 'index',
    'content-side-layout',  # TOC 侧边栏布局容器
    'table-of-contents-',  # TOC 相关的 id/class 前缀
]


#: TOC 锚点链接的类名模式（白名单）
#: 用于识别 TOC 内部链接的 class 属性
TOC_LINK_CLASS_PATTERNS = [
    'toc-item', 'toc-link', 'nav-item', 'nav-link',
    'menu-item', 'menu-link', 'directory-item'
]


#: TOC 锚点链接的直接父元素类名（白名单）
#: 如 li.toc-item 这种嵌套结构
TOC_PARENT_CLASS_PATTERNS = [
    'toc-item', 'toc-item relative', 'nav-item', 'menu-item'
]


#: 正文内容区域的类名模式（黑名单）
#: 用于识别非 TOC 的正文内容区域
CONTENT_AREA_PATTERNS = [
    'mdx-content', 'content-area', 'prose', 'content-container'
]


#: 非目录链接的类名模式（黑名单）
#: 用于排除不在 TOC 中的锚点链接
NON_TOC_LINK_PATTERNS = [
    'link',  # 正文相关链接
    'opacity-0',  # 标题旁边的隐藏锚点按钮
    'group-hover:opacity-100',  # 悬停显示的锚点按钮
    'header-link',  # 标题链接
    'anchor'  # 锚点符号
]


#: TOC 结束标识（遇到这些文本后停止提取后续锚点）
#: 用于过滤 TOC 中不必要的后续内容
TOC_END_MARKERS = [
    r'See also',
    r'Related articles?',
    r'Further reading',
    r'External links?',
    r'References',
    r'Related skills',
    r'More skills',
    r'Other skills',
    r'You might also like',
    r'Continue reading',
    r'Next steps',
    r'Next up',
]


# ============================================================================
# 默认配置导出
# ============================================================================

DEFAULT_CONFIG = {
    'semantic_non_content_selectors': SEMANTIC_NON_CONTENT_SELECTORS,
    'general_non_content_selectors': GENERAL_NON_CONTENT_SELECTORS,
    'fuzzy_keywords': FUZZY_KEYWORDS,
    'log_levels': LOG_LEVELS,
    'meaningless_content': MEANINGLESS_CONTENT,
    'content_end_markers': CONTENT_END_MARKERS,
    'content_preserve_selectors': CONTENT_PRESERVE_SELECTORS,
    'code_container_selectors': CODE_CONTAINER_SELECTORS,
    'force_remove_selectors': FORCE_REMOVE_SELECTORS,
    'protected_tag_blacklist': PROTECTED_TAG_BLACKLIST,
    'documentation_framework_presets': DOCUMENTATION_FRAMEWORK_PRESETS,
    # TOC URL 过滤配置
    'toc_class_patterns': TOC_CLASS_PATTERNS,
    'toc_link_class_patterns': TOC_LINK_CLASS_PATTERNS,
    'toc_parent_class_patterns': TOC_PARENT_CLASS_PATTERNS,
    'content_area_patterns': CONTENT_AREA_PATTERNS,
    'non_toc_link_patterns': NON_TOC_LINK_PATTERNS,
    'toc_end_markers': TOC_END_MARKERS,
}


def get_toc_filter_config(
    custom_toc_class_patterns: Optional[List[str]] = None,
    custom_toc_link_class_patterns: Optional[List[str]] = None,
    custom_toc_parent_class_patterns: Optional[List[str]] = None,
    custom_content_area_patterns: Optional[List[str]] = None,
    custom_non_toc_link_patterns: Optional[List[str]] = None,
    custom_toc_end_markers: Optional[List[str]] = None,
    merge_mode: str = 'extend'
) -> Dict[str, Any]:
    """
    获取 TOC URL 过滤器配置

    Args:
        custom_toc_class_patterns: 自定义 TOC 容器类名模式
        custom_toc_link_class_patterns: 自定义 TOC 链接类名模式
        custom_toc_parent_class_patterns: 自定义 TOC 父元素类名模式
        custom_content_area_patterns: 自定义正文内容区域模式
        custom_non_toc_link_patterns: 自定义非 TOC 链接模式
        custom_toc_end_markers: 自定义 TOC 结束标识
        merge_mode: 合并模式 ('extend' 或 'replace')

    Returns:
        包含所有 TOC 过滤配置的字典
    """
    return {
        'toc_class_patterns': merge_selectors(
            TOC_CLASS_PATTERNS,
            custom_toc_class_patterns,
            merge_mode
        ),
        'toc_link_class_patterns': merge_selectors(
            TOC_LINK_CLASS_PATTERNS,
            custom_toc_link_class_patterns,
            merge_mode
        ),
        'toc_parent_class_patterns': merge_selectors(
            TOC_PARENT_CLASS_PATTERNS,
            custom_toc_parent_class_patterns,
            merge_mode
        ),
        'content_area_patterns': merge_selectors(
            CONTENT_AREA_PATTERNS,
            custom_content_area_patterns,
            merge_mode
        ),
        'non_toc_link_patterns': merge_selectors(
            NON_TOC_LINK_PATTERNS,
            custom_non_toc_link_patterns,
            merge_mode
        ),
        'toc_end_markers': merge_selectors(
            TOC_END_MARKERS,
            custom_toc_end_markers,
            merge_mode
        ),
    }


class TocFilterConfigLoader:
    """
    从 config.json 加载 TOC URL 过滤器配置的工具类

    允许用户通过 config.json 自定义 TOC 过滤标签列表
    """

    @staticmethod
    def load_from_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        从配置字典加载 TOC 过滤器配置

        Args:
            config_dict: 包含 toc_filter 配置的字典

        Returns:
            TOC 过滤器配置字典
        """
        # 从配置文件中读取自定义选择器（如果存在）
        toc_filter_config = config_dict.get('toc_filter', {})

        # 获取合并模式
        merge_mode = toc_filter_config.get('merge_mode', 'extend')

        # 获取基础配置
        return get_toc_filter_config(
            custom_toc_class_patterns=toc_filter_config.get('toc_class_patterns'),
            custom_toc_link_class_patterns=toc_filter_config.get('toc_link_class_patterns'),
            custom_toc_parent_class_patterns=toc_filter_config.get('toc_parent_class_patterns'),
            custom_content_area_patterns=toc_filter_config.get('content_area_patterns'),
            custom_non_toc_link_patterns=toc_filter_config.get('non_toc_link_patterns'),
            custom_toc_end_markers=toc_filter_config.get('toc_end_markers'),
            merge_mode=merge_mode
        )
