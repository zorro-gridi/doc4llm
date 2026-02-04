#!/usr/bin/env python3
"""
API文档读取器 - 专门处理API接口文档的内容提取

功能：
1. 智能识别API文档结构（类、方法、属性等）
2. 支持按API项目名称提取内容
3. 处理缺少标准标题的API文档
4. 与现有的doc_reader_api.py兼容

适用场景：
- Python API文档（如DolphinScheduler）
- JavaScript API文档  
- REST API文档
- 其他技术文档
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass

from doc4llm.doc_rag.reader.doc_reader_api import DocReaderAPI
from doc4llm.tool.md_doc_retrieval.doc_extractor import ExtractionResult


@dataclass
class APIDocReaderAPI(DocReaderAPI):
    """
    API文档读取器 - 继承自DocReaderAPI，增加API文档特殊处理
    
    新增功能：
    1. 智能识别API结构（类、方法、属性）
    2. 支持按API项目名称提取
    3. 处理缺少标题的API文档
    4. 自动生成标题结构
    """
    
    def __post_init__(self):
        """初始化，调用父类初始化"""
        super().__post_init__()
        
        # API文档特有的配置
        self.api_patterns = {
            # Python API 模式
            'python_class': r'^(class\s+)?([A-Z][a-zA-Z0-9_]*)\s*(\(.*\))?:?\s*$',
            'python_method': r'^(def\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*:?\s*$',
            'python_property': r'^(property\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*:?\s*$',
            
            # 通用API模式
            'api_section': r'^([A-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*$',
            'method_signature': r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*$',
        }
    
    def extract_api_sections(
        self,
        sections: List[Dict[str, Any]],
        threshold: int = 2100,
        api_mode: bool = True
    ) -> ExtractionResult:
        """
        提取API文档章节，支持API特殊处理
        
        Args:
            sections: 章节配置列表
            threshold: 行数阈值
            api_mode: 是否启用API模式（智能识别API结构）
            
        Returns:
            ExtractionResult: 提取结果
        """
        if not api_mode:
            # 使用标准模式
            return self.extract_multi_by_headings(sections, threshold)
        
        # API模式：预处理sections，智能匹配API结构
        enhanced_sections = []
        
        for section in sections:
            title = section.get('title', '')
            headings = section.get('headings', [])
            doc_set = section.get('doc_set', '')
            
            # 检查是否为API文档
            if self._is_api_document(title):
                # 增强API文档的headings
                enhanced_headings = self._enhance_api_headings(headings, title, doc_set)
                enhanced_sections.append({
                    'title': title,
                    'headings': enhanced_headings,
                    'doc_set': doc_set,
                    'api_enhanced': True
                })
            else:
                # 非API文档，保持原样
                enhanced_sections.append(section)
        
        # 使用增强后的sections调用父类方法
        return self.extract_multi_by_headings(enhanced_sections, threshold)
    
    def _is_api_document(self, title: str) -> bool:
        """
        判断是否为API文档
        
        Args:
            title: 文档标题
            
        Returns:
            bool: 是否为API文档
        """
        api_indicators = [
            'api',
            'reference',
            'class',
            'method',
            'function',
            'module',
            'package',
            'library',
            'sdk'
        ]
        
        title_lower = title.lower()
        return any(indicator in title_lower for indicator in api_indicators)
    
    def _enhance_api_headings(
        self, 
        headings: List[str], 
        title: str, 
        doc_set: str
    ) -> List[str]:
        """
        增强API文档的headings列表
        
        Args:
            headings: 原始headings列表
            title: 文档标题
            doc_set: 文档集
            
        Returns:
            List[str]: 增强后的headings列表
        """
        if not headings:
            return headings
        
        enhanced_headings = []
        
        for heading in headings:
            # 检查是否匹配API模式
            api_type = self._detect_api_type(heading)
            
            if api_type:
                # 生成可能的标题变体
                variants = self._generate_heading_variants(heading, api_type)
                enhanced_headings.extend(variants)
            else:
                # 非API项，保持原样
                enhanced_headings.append(heading)
        
        return enhanced_headings
    
    def _detect_api_type(self, heading: str) -> Optional[str]:
        """
        检测API项的类型
        
        Args:
            heading: 标题文本
            
        Returns:
            Optional[str]: API类型（class/method/property等），或None
        """
        for pattern_name, pattern in self.api_patterns.items():
            if re.match(pattern, heading.strip()):
                return pattern_name.split('_')[1]  # 提取类型（class/method/property）
        
        # 检查是否包含API关键词
        api_keywords = ['class', 'method', 'function', 'property', 'attribute']
        heading_lower = heading.lower()
        
        for keyword in api_keywords:
            if keyword in heading_lower:
                return keyword
        
        return None
    
    def _generate_heading_variants(self, heading: str, api_type: str) -> List[str]:
        """
        为API项生成可能的标题变体
        
        Args:
            heading: 原始标题
            api_type: API类型
            
        Returns:
            List[str]: 标题变体列表
        """
        variants = [heading]  # 包含原始标题
        
        # 清理标题
        clean_heading = self._clean_api_heading(heading)
        if clean_heading != heading:
            variants.append(clean_heading)
        
        # 根据API类型生成变体
        if api_type == 'class':
            variants.extend([
                f"class {clean_heading}",
                f"Class: {clean_heading}",
                f"{clean_heading} class",
            ])
        elif api_type == 'method':
            variants.extend([
                f"method {clean_heading}",
                f"Method: {clean_heading}",
                f"{clean_heading}()",
                f"def {clean_heading}",
            ])
        elif api_type == 'property':
            variants.extend([
                f"property {clean_heading}",
                f"Property: {clean_heading}",
                f"{clean_heading} property",
            ])
        
        # 移除重复项
        return list(dict.fromkeys(variants))
    
    def _clean_api_heading(self, heading: str) -> str:
        """
        清理API标题，移除多余的格式
        
        Args:
            heading: 原始标题
            
        Returns:
            str: 清理后的标题
        """
        # 移除常见的API文档标记
        cleaned = re.sub(r'^(class|def|function|method|property|attribute)\s+', '', heading)
        cleaned = re.sub(r'\([^)]*\)$', '', cleaned)  # 移除参数列表
        cleaned = re.sub(r'\s*:\s*.*$', '', cleaned)  # 移除类型注解
        cleaned = re.sub(r'\s+', ' ', cleaned)  # 标准化空白字符
        
        return cleaned.strip()
    
    def extract_api_by_names(
        self,
        api_names: List[str],
        doc_set: Optional[str] = None,
        api_type: Optional[str] = None
    ) -> Dict[str, str]:
        """
        按API名称提取内容
        
        Args:
            api_names: API名称列表（类名、方法名等）
            doc_set: 文档集标识符
            api_type: API类型过滤（class/method/property等）
            
        Returns:
            Dict[str, str]: API名称到内容的映射
        """
        results = {}
        
        for api_name in api_names:
            # 生成可能的标题变体
            variants = self._generate_heading_variants(api_name, api_type or 'api')
            
            # 尝试每个变体
            content = None
            for variant in variants:
                content = self.extract_by_title(variant, doc_set=doc_set)
                if content:
                    break
            
            if content:
                results[api_name] = content
            else:
                # 尝试模糊搜索
                search_results = self.search_documents(api_name, search_mode='fuzzy')
                if search_results:
                    # 取第一个结果
                    first_result = search_results[0]
                    if 'title' in first_result:
                        content = self.extract_by_title(first_result['title'], doc_set=doc_set)
                        if content:
                            results[api_name] = content
        
        return results
    
    def analyze_api_structure(self, doc_set: Optional[str] = None) -> Dict[str, Any]:
        """
        分析API文档结构
        
        Args:
            doc_set: 文档集标识符
            
        Returns:
            Dict[str, Any]: API结构分析结果
        """
        # 获取所有可用文档
        documents = self.list_available_documents()
        
        if doc_set:
            # 过滤指定文档集
            documents = [doc for doc in documents if doc_set in doc]
        
        api_structure = {
            'total_documents': len(documents),
            'api_documents': [],
            'classes': [],
            'methods': [],
            'properties': [],
            'other_apis': []
        }
        
        for doc_title in documents:
            if self._is_api_document(doc_title):
                api_structure['api_documents'].append(doc_title)
                
                # 尝试提取文档内容进行结构分析
                content = self.extract_by_title(doc_title, doc_set=doc_set)
                if content:
                    structure = self._analyze_document_structure(content, doc_title)
                    api_structure['classes'].extend(structure.get('classes', []))
                    api_structure['methods'].extend(structure.get('methods', []))
                    api_structure['properties'].extend(structure.get('properties', []))
                    api_structure['other_apis'].extend(structure.get('other_apis', []))
        
        return api_structure
    
    def _analyze_document_structure(self, content: str, title: str) -> Dict[str, List[str]]:
        """
        分析单个文档的API结构
        
        Args:
            content: 文档内容
            title: 文档标题
            
        Returns:
            Dict[str, List[str]]: 结构分析结果
        """
        structure = {
            'classes': [],
            'methods': [],
            'properties': [],
            'other_apis': []
        }
        
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 检测API项
            api_type = self._detect_api_type(line)
            if api_type:
                clean_name = self._clean_api_heading(line)
                if clean_name:
                    if api_type == 'class':
                        structure['classes'].append(clean_name)
                    elif api_type in ['method', 'function']:
                        structure['methods'].append(clean_name)
                    elif api_type == 'property':
                        structure['properties'].append(clean_name)
                    else:
                        structure['other_apis'].append(clean_name)
        
        return structure


# =============================================================================
# 便捷函数
# =============================================================================

def create_api_reader(
    base_dir: str,
    config: Optional[Union[str, Path, Dict[str, Any]]] = None,
    **kwargs
) -> APIDocReaderAPI:
    """
    创建API文档读取器实例
    
    Args:
        base_dir: 知识库根目录
        config: 配置文件路径、JSON字符串或字典
        **kwargs: 其他配置参数
        
    Returns:
        APIDocReaderAPI: API文档读取器实例
    """
    return APIDocReaderAPI(base_dir=base_dir, config=config, **kwargs)


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "APIDocReaderAPI",
    "create_api_reader",
]