#!/usr/bin/env python3
"""
测试API文档格式化器

验证DolphinScheduler API文档的检测和格式化功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from doc4llm.crawler.api_doc_formatter import APIDocFormatter, APIDocEnhancer
from doc4llm.scanner.config import ScannerConfig
import requests
from bs4 import BeautifulSoup


def test_api_formatter():
    """测试API文档格式化器"""
    print("=" * 60)
    print("测试API文档格式化器")
    print("=" * 60)
    
    # 获取DolphinScheduler API页面
    url = "https://dolphinscheduler.apache.org/python/main/api.html"
    print(f"获取页面: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html_content = response.text
        print(f"页面大小: {len(html_content)} 字符")
        
        # 创建API文档格式化器
        formatter = APIDocFormatter(debug_mode=True)
        
        # 检测API结构
        soup = BeautifulSoup(html_content, 'html.parser')
        api_items = formatter.detect_api_structure(soup, url)
        
        print(f"\n检测结果:")
        print(f"  检测到API项: {len(api_items)}")
        
        if api_items:
            print(f"  前10个API项:")
            for i, item in enumerate(api_items[:10]):
                print(f"    {i+1}. {item['type']}: {item['title']} (level {item['level']}, id: {item['id']})")
        
        # 测试格式化
        print(f"\n开始格式化...")
        formatted_html, api_info = formatter.format_api_content(html_content, url)
        
        print(f"格式化结果:")
        print(f"  插入标题数: {api_info.get('inserted_count', 0)}")
        print(f"  总API项数: {api_info.get('total_items', 0)}")
        
        # 检查格式化后的HTML中是否包含标题
        formatted_soup = BeautifulSoup(formatted_html, 'html.parser')
        headings = formatted_soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        print(f"  格式化后标题数: {len(headings)}")
        
        if headings:
            print(f"  前5个标题:")
            for i, heading in enumerate(headings[:5]):
                print(f"    {i+1}. {heading.name}: {heading.get_text(strip=True)}")
        
        return len(api_items) > 0
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_enhancer():
    """测试API文档增强器"""
    print("\n" + "=" * 60)
    print("测试API文档增强器")
    print("=" * 60)
    
    # 创建配置
    url = "https://dolphinscheduler.apache.org/python/main/api.html"
    config = ScannerConfig(
        start_url=url, 
        debug_mode=True,
        doc_dir="./test_docs",  # 添加必需的参数
        doc_name="test_api",
        doc_version="latest"
    )
    
    # 创建API文档增强器
    enhancer = APIDocEnhancer(config, debug_mode=True)
    
    # 测试URL
    url = "https://dolphinscheduler.apache.org/python/main/api.html"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html_content = response.text
        
        # 测试API文档检测
        soup = BeautifulSoup(html_content, 'html.parser')
        is_api_doc = enhancer.is_api_documentation(url, soup)
        print(f"是否为API文档: {is_api_doc}")
        
        if is_api_doc:
            # 测试内容增强
            enhanced_html, is_enhanced, api_info = enhancer.enhance_api_content(html_content, url)
            
            print(f"增强结果:")
            print(f"  是否增强: {is_enhanced}")
            print(f"  API项数: {api_info.get('total_items', 0)}")
            
            if is_enhanced:
                # 检查增强后的HTML
                enhanced_soup = BeautifulSoup(enhanced_html, 'html.parser')
                headings = enhanced_soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                print(f"  增强后标题数: {len(headings)}")
                
                return True
        
        return False
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("API文档格式化器测试")
    
    # 测试API格式化器
    formatter_ok = test_api_formatter()
    
    # 测试API增强器
    enhancer_ok = test_api_enhancer()
    
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    print(f"API格式化器: {'✓ 通过' if formatter_ok else '✗ 失败'}")
    print(f"API增强器: {'✓ 通过' if enhancer_ok else '✗ 失败'}")
    
    if formatter_ok and enhancer_ok:
        print("\n所有测试通过！API文档格式化功能正常。")
        return True
    else:
        print("\n部分测试失败，请检查配置和代码。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)