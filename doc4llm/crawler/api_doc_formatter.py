#!/usr/bin/env python3
"""
API文档格式化器 - 专门处理API接口文档的标题结构问题

功能：
1. 检测API文档中的类、方法、属性等结构
2. 为这些结构自动生成对应的Markdown标题
3. 与现有的TOC结构保持一致
4. 支持多种API文档格式（Sphinx、JSDoc、OpenAPI等）

适用场景：
- Python API文档（如DolphinScheduler）
- JavaScript API文档
- REST API文档
- 其他缺少标题结构的技术文档
"""

import re
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, unquote


class APIDocFormatter:
    """API文档格式化器"""
    
    def __init__(self, debug_mode: bool = False):
        """
        初始化API文档格式化器
        
        Args:
            debug_mode: 是否启用调试模式
        """
        self.debug_mode = debug_mode
        
        # API文档结构模式
        self.api_patterns = {
            # Python API 模式
            'python_class': {
                'selector': 'dt[id*="class"], dt[id*="Class"]',
                'title_selector': 'code.descname, .sig-name',
                'level': 2,
                'prefix': 'class'
            },
            'python_method': {
                'selector': 'dt[id*="method"], dt[id*="Method"]',
                'title_selector': 'code.descname, .sig-name',
                'level': 3,
                'prefix': 'method'
            },
            'python_function': {
                'selector': 'dt[id*="function"], dt[id*="Function"]',
                'title_selector': 'code.descname, .sig-name',
                'level': 3,
                'prefix': 'function'
            },
            'python_attribute': {
                'selector': 'dt[id*="attribute"], dt[id*="Attribute"]',
                'title_selector': 'code.descname, .sig-name',
                'level': 4,
                'prefix': 'attribute'
            },
            'python_property': {
                'selector': 'dt[id*="property"], dt[id*="Property"]',
                'title_selector': 'code.descname, .sig-name',
                'level': 4,
                'prefix': 'property'
            },
            # 通用API模式
            'generic_api_section': {
                'selector': '[id]:has(code), .api-item, .method-item, .class-item',
                'title_selector': 'code, .api-name, .method-name, .class-name',
                'level': 3,
                'prefix': 'api'
            }
        }
        
        # 标题层级映射
        self.level_to_markdown = {
            1: '#',
            2: '##',
            3: '###',
            4: '####',
            5: '#####',
            6: '######'
        }
    
    def _debug_print(self, message: str):
        """调试输出"""
        if self.debug_mode:
            print(f"[API_FORMATTER] {message}")
    
    def detect_api_structure(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """
        检测API文档结构
        
        Args:
            soup: BeautifulSoup解析的HTML
            url: 页面URL
            
        Returns:
            List[Dict]: API结构列表，每个元素包含：
                - id: 元素ID
                - title: 标题文本
                - level: 标题层级
                - element: BeautifulSoup元素
                - type: API类型（class/method/function等）
        """
        api_items = []
        
        # 特殊处理DolphinScheduler类型的API文档
        if 'dolphinscheduler' in url or 'apache' in url:
            api_items.extend(self._detect_dolphinscheduler_structure(soup))
        
        # 通用API结构检测
        for pattern_name, pattern in self.api_patterns.items():
            elements = soup.select(pattern['selector'])
            
            for element in elements:
                # 提取标题文本
                title_elem = element.select_one(pattern['title_selector'])
                if not title_elem:
                    title_elem = element
                
                title_text = self._extract_clean_title(title_elem)
                if not title_text:
                    continue
                
                # 获取元素ID
                element_id = element.get('id', '')
                if not element_id:
                    # 尝试从子元素获取ID
                    id_elem = element.find(attrs={'id': True})
                    if id_elem:
                        element_id = id_elem.get('id', '')
                
                api_items.append({
                    'id': element_id,
                    'title': title_text,
                    'level': pattern['level'],
                    'element': element,
                    'type': pattern['prefix'],
                    'pattern': pattern_name
                })
        
        # 按在文档中的出现顺序排序
        api_items.sort(key=lambda x: self._get_element_position(x['element']))
        
        self._debug_print(f"检测到 {len(api_items)} 个API结构项")
        return api_items
    
    def _detect_dolphinscheduler_structure(self, soup: BeautifulSoup) -> List[Dict]:
        """
        专门检测DolphinScheduler API文档结构
        
        Args:
            soup: BeautifulSoup解析的HTML
            
        Returns:
            List[Dict]: API结构列表
        """
        api_items = []
        
        # DolphinScheduler使用特定的HTML结构
        # 查找所有包含class定义的元素
        class_elements = soup.find_all('dl', class_='py class')
        for class_elem in class_elements:
            dt = class_elem.find('dt')
            if dt and dt.get('id'):
                # 提取类名
                sig_name = dt.find('em', class_='sig-name')
                if sig_name:
                    class_name = sig_name.get_text(strip=True)
                    api_items.append({
                        'id': dt.get('id'),
                        'title': class_name,
                        'level': 2,
                        'element': dt,
                        'type': 'class',
                        'pattern': 'dolphinscheduler_class'
                    })
        
        # 查找方法和属性
        method_elements = soup.find_all('dl', class_=['py method', 'py attribute', 'py property'])
        for method_elem in method_elements:
            dt = method_elem.find('dt')
            if dt and dt.get('id'):
                # 提取方法/属性名
                sig_name = dt.find('em', class_='sig-name')
                if sig_name:
                    name = sig_name.get_text(strip=True)
                    
                    # 确定类型和层级
                    if 'py method' in method_elem.get('class', []):
                        api_type = 'method'
                        level = 3
                    elif 'py property' in method_elem.get('class', []):
                        api_type = 'property'
                        level = 4
                    else:
                        api_type = 'attribute'
                        level = 4
                    
                    api_items.append({
                        'id': dt.get('id'),
                        'title': name,
                        'level': level,
                        'element': dt,
                        'type': api_type,
                        'pattern': f'dolphinscheduler_{api_type}'
                    })
        
        # 如果没有找到标准的Sphinx结构，尝试通用检测
        if not api_items:
            self._debug_print("未找到标准Sphinx结构，尝试通用API检测")
            
            # 查找所有带id的dt元素（可能是API项）
            dt_elements = soup.find_all('dt', id=True)
            for dt in dt_elements:
                dt_id = dt.get('id', '')
                if not dt_id:
                    continue
                
                # 检查是否包含API相关的类名或id模式
                if any(pattern in dt_id.lower() for pattern in ['class', 'method', 'function', 'property', 'attribute']):
                    # 提取显示文本
                    title_text = self._extract_clean_title(dt)
                    if title_text:
                        # 根据id模式确定类型和层级
                        if 'class' in dt_id.lower():
                            api_type = 'class'
                            level = 2
                        elif any(pattern in dt_id.lower() for pattern in ['method', 'function']):
                            api_type = 'method'
                            level = 3
                        else:
                            api_type = 'attribute'
                            level = 4
                        
                        api_items.append({
                            'id': dt_id,
                            'title': title_text,
                            'level': level,
                            'element': dt,
                            'type': api_type,
                            'pattern': f'generic_{api_type}'
                        })
            
            # 如果还是没有找到，尝试查找所有带id的元素
            if not api_items:
                self._debug_print("尝试查找所有带id的元素")
                all_id_elements = soup.find_all(id=True)
                for elem in all_id_elements:
                    elem_id = elem.get('id', '')
                    if not elem_id or len(elem_id) < 3:
                        continue
                    
                    # 跳过明显不是API的id
                    if any(skip in elem_id.lower() for skip in ['nav', 'header', 'footer', 'sidebar', 'menu']):
                        continue
                    
                    # 检查是否是Python命名空间格式
                    if '.' in elem_id and any(keyword in elem_id.lower() for keyword in ['core', 'task', 'engine', 'workflow']):
                        title_text = self._extract_clean_title(elem)
                        if title_text:
                            # 根据命名空间层级确定level
                            parts = elem_id.split('.')
                            if len(parts) >= 3:  # pydolphinscheduler.core.Engine
                                level = 2 if parts[-1][0].isupper() else 3  # 大写开头可能是类
                            else:
                                level = 3
                            
                            api_items.append({
                                'id': elem_id,
                                'title': title_text,
                                'level': level,
                                'element': elem,
                                'type': 'api',
                                'pattern': 'namespace_api'
                            })
        
        self._debug_print(f"DolphinScheduler检测到 {len(api_items)} 个API项")
        return api_items
    
    def _extract_clean_title(self, element: Tag) -> str:
        """
        提取干净的标题文本
        
        Args:
            element: BeautifulSoup元素
            
        Returns:
            str: 清理后的标题文本
        """
        if not element:
            return ""
        
        # 获取文本内容
        text = element.get_text(strip=True)
        
        # 清理常见的API文档标记
        text = re.sub(r'^(class|def|function|method|property|attribute)\s+', '', text)
        text = re.sub(r'\([^)]*\)$', '', text)  # 移除参数列表
        text = re.sub(r'\s*:\s*.*$', '', text)  # 移除类型注解
        text = re.sub(r'\s+', ' ', text)  # 标准化空白字符
        
        return text.strip()
    
    def _get_element_position(self, element: Tag) -> int:
        """
        获取元素在文档中的位置（用于排序）
        
        Args:
            element: BeautifulSoup元素
            
        Returns:
            int: 元素位置索引
        """
        try:
            # 获取元素在其父容器中的索引
            parent = element.parent
            if parent:
                return list(parent.children).index(element)
            return 0
        except (ValueError, AttributeError):
            return 0
    
    def insert_api_headings(self, markdown_content: str, api_items: List[Dict], url: str) -> str:
        """
        在Markdown内容中插入API标题
        
        Args:
            markdown_content: 原始Markdown内容
            api_items: API结构列表
            url: 页面URL
            
        Returns:
            str: 插入标题后的Markdown内容
        """
        if not api_items:
            return markdown_content
        
        lines = markdown_content.split('\n')
        new_lines = []
        
        # 为每个API项创建锚点到标题的映射
        anchor_to_title = {}
        for item in api_items:
            if item['id']:
                # 创建标题行
                title_prefix = self.level_to_markdown[item['level']]
                title_line = f"{title_prefix} {item['title']}"
                anchor_to_title[item['id']] = title_line
        
        # 处理每一行
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 检查是否包含API锚点
            inserted_title = False
            for anchor_id, title_line in anchor_to_title.items():
                if anchor_id in line and not line.strip().startswith('#'):
                    # 在当前行之前插入标题
                    new_lines.append(title_line)
                    new_lines.append('')  # 空行分隔
                    inserted_title = True
                    break
            
            new_lines.append(line)
            i += 1
        
        result = '\n'.join(new_lines)
        
        self._debug_print(f"插入了 {len(anchor_to_title)} 个API标题")
        return result
    
    def generate_toc_mapping(self, api_items: List[Dict], base_url: str) -> Dict[str, str]:
        """
        生成TOC映射，用于与docTOC.md保持一致
        
        Args:
            api_items: API结构列表
            base_url: 基础URL
            
        Returns:
            Dict[str, str]: 锚点ID到标题的映射
        """
        toc_mapping = {}
        
        for item in api_items:
            if item['id']:
                # 生成完整URL
                full_url = f"{base_url}#{item['id']}"
                
                # 创建标题
                title = item['title']
                if item['type'] != 'generic':
                    title = f"{item['type'].title()}: {title}"
                
                toc_mapping[item['id']] = {
                    'title': title,
                    'url': full_url,
                    'level': item['level']
                }
        
        return toc_mapping
    
    def format_api_content(self, html_content: str, url: str) -> Tuple[str, Dict]:
        """
        格式化API文档内容
        
        Args:
            html_content: HTML内容
            url: 页面URL
            
        Returns:
            Tuple[str, Dict]: (格式化后的HTML, API结构信息)
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 检测API结构
        api_items = self.detect_api_structure(soup, url)
        
        if not api_items:
            self._debug_print("未检测到API结构，返回原始HTML")
            return html_content, {'api_items': [], 'toc_mapping': {}, 'total_items': 0}
        
        # 在HTML中插入标题标签
        inserted_count = 0
        for item in api_items:
            element = item['element']
            level = item['level']
            title = item['title']
            
            try:
                # 创建标题元素
                heading_tag = soup.new_tag(f'h{level}')
                heading_tag.string = title
                if item['id']:
                    heading_tag['id'] = f"heading-{item['id']}"
                
                # 在原元素之前插入标题
                element.insert_before(heading_tag)
                inserted_count += 1
                
                self._debug_print(f"插入标题: h{level} {title}")
                
            except Exception as e:
                self._debug_print(f"插入标题失败 {title}: {e}")
                continue
        
        # 生成TOC映射
        toc_mapping = self.generate_toc_mapping(api_items, url)
        
        formatted_html = str(soup)
        
        self._debug_print(f"API格式化完成: 插入了 {inserted_count} 个标题")
        
        return formatted_html, {
            'api_items': api_items,
            'toc_mapping': toc_mapping,
            'total_items': len(api_items),
            'inserted_count': inserted_count
        }


class APIDocEnhancer:
    """API文档增强器 - 集成到现有爬虫流程中"""
    
    def __init__(self, config, debug_mode: bool = False):
        """
        初始化API文档增强器
        
        Args:
            config: 爬虫配置对象
            debug_mode: 是否启用调试模式
        """
        self.config = config
        self.debug_mode = debug_mode
        self.formatter = APIDocFormatter(debug_mode)
        
        # API文档检测模式
        self.api_detection_patterns = [
            'dolphinscheduler',
            'api.html',
            '/api/',
            '/docs/api/',
            'reference',
            'sphinx'
        ]
    
    def is_api_documentation(self, url: str, soup: BeautifulSoup) -> bool:
        """
        检测是否为API文档页面
        
        Args:
            url: 页面URL
            soup: BeautifulSoup解析的HTML
            
        Returns:
            bool: 是否为API文档
        """
        # URL模式检测
        for pattern in self.api_detection_patterns:
            if pattern in url.lower():
                return True
        
        # HTML结构检测
        api_indicators = [
            'dl.py.class',  # Sphinx Python文档
            'dl.py.method',
            'dl.py.function',
            '.api-doc',
            '.method-list',
            '.class-list',
            '[class*="api-"]'
        ]
        
        for indicator in api_indicators:
            if soup.select(indicator):
                return True
        
        return False
    
    def enhance_api_content(self, html_content: str, url: str) -> Tuple[str, bool, Dict]:
        """
        增强API文档内容
        
        Args:
            html_content: 原始HTML内容
            url: 页面URL
            
        Returns:
            Tuple[str, bool, Dict]: (增强后的HTML, 是否进行了增强, 增强信息)
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 检测是否为API文档
        if not self.is_api_documentation(url, soup):
            return html_content, False, {}
        
        # 格式化API内容
        enhanced_html, api_info = self.formatter.format_api_content(html_content, url)
        
        return enhanced_html, True, api_info
    
    def enhance_markdown_content(self, markdown_content: str, api_info: Dict, url: str) -> str:
        """
        增强Markdown内容
        
        Args:
            markdown_content: 原始Markdown内容
            api_info: API结构信息
            url: 页面URL
            
        Returns:
            str: 增强后的Markdown内容
        """
        if not api_info or 'api_items' not in api_info:
            return markdown_content
        
        # 插入API标题
        enhanced_markdown = self.formatter.insert_api_headings(
            markdown_content, 
            api_info['api_items'], 
            url
        )
        
        return enhanced_markdown