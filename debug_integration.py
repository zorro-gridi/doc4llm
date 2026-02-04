#!/usr/bin/env python3
"""
调试API增强器与实际配置的集成问题

模拟用户的实际使用场景，找出为什么API增强器没有生效
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from doc4llm.crawler.DocContentCrawler import DocContentCrawler
from doc4llm.scanner.config import ScannerConfig
import requests
from bs4 import BeautifulSoup


def load_config_from_json(config_path: str) -> dict:
    """从JSON文件加载配置"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_scanner_config_from_json(config_data: dict) -> ScannerConfig:
    """从JSON配置创建ScannerConfig对象"""
    # 提取所有必需的参数
    config = ScannerConfig(
        start_url=config_data['start_url'],
        proxy=config_data.get('proxy'),
        delay=config_data.get('delay', 0.1),
        max_workers=config_data.get('max_workers', 10),
        timeout=config_data.get('timeout', 30),
        max_depth=config_data.get('max_depth', 5),
        blacklist_domains=config_data.get('blacklist_domains', []),
        whitelist_domains=config_data.get('whitelist_domains', []),
        output_file=config_data.get('output_file'),
        color_output=config_data.get('color_output', True),
        verbose=config_data.get('verbose', True),
        extension_blacklist=config_data.get('extension_blacklist', []),
        max_urls=config_data.get('max_urls', 10000),
        smart_concatenation=config_data.get('smart_concatenation', True),
        debug_mode=config_data.get('debug_mode', 0),
        url_scope_mode=config_data.get('url_scope_mode', 0),
        danger_filter_enabled=config_data.get('danger_filter_enabled', 1),
        danger_api_list=config_data.get('danger_api_list', []),
        allowed_api_list=config_data.get('allowed_api_list', []),
        is_duplicate=config_data.get('is_duplicate', 0),
        custom_base_url=config_data.get('custom_base_url', []),
        path_route=config_data.get('path_route', []),
        api_route=config_data.get('api_route', []),
        fuzz=config_data.get('fuzz', 0),
        exclude_fuzzy=config_data.get('exclude_fuzzy', []),
        title_filter_list=config_data.get('title_filter_list', []),
        title_cleanup_patterns=config_data.get('title_cleanup_patterns', []),
        status_code_filter=config_data.get('status_code_filter', []),
        mode=config_data.get('mode', 0),
        force_scan=config_data.get('force_scan', 0),
        doc_dir=config_data.get('doc_dir', './test_docs'),
        doc_name=config_data.get('doc_name', 'test_api'),
        doc_version=config_data.get('doc_version', 'latest'),
        toc_url_filters=config_data.get('toc_url_filters', {}),
        doc_max_depth=config_data.get('doc_max_depth', 10),
        doc_timeout=config_data.get('doc_timeout', 30),
        doc_toc_selector=config_data.get('doc_toc_selector'),
        toc_filter=config_data.get('toc_filter', {}),
        results_dir=config_data.get('results_dir', 'results'),
        output_log_file=config_data.get('output_log_file', 'results/output.out'),
        debug_log_file=config_data.get('debug_log_file', 'results/debug.log'),
        log_max_lines=config_data.get('log_max_lines', 10000),
        content_filter=config_data.get('content_filter', {}),
        enable_inline_extraction=config_data.get('enable_inline_extraction', 1),
        extract_image_list=config_data.get('extract_image_list'),
        playwright_enabled=config_data.get('playwright', {}).get('enabled', True),
        playwright_timeout=config_data.get('playwright', {}).get('timeout', 30),
        playwright_headless=config_data.get('playwright', {}).get('headless', True),
        playwright_force=config_data.get('playwright', {}).get('force', False),
        playwright_stealth=config_data.get('stealth', {}).get('enabled', True),
        playwright_platform=config_data.get('stealth', {}).get('platform', 'darwin'),
        playwright_screen_width=config_data.get('stealth', {}).get('screen_width', 1920),
        playwright_screen_height=config_data.get('stealth', {}).get('screen_height', 1080),
        playwright_device_scale_factor=config_data.get('stealth', {}).get('device_scale_factor', 1),
        playwright_timezone=config_data.get('stealth', {}).get('timezone', 'Asia/Shanghai'),
        playwright_locale=config_data.get('stealth', {}).get('locale', 'zh-CN'),
        playwright_cookies_file=config_data.get('cookies', {}).get('file'),
        playwright_cookies=config_data.get('cookies', {}).get('inline', [])
    )
    
    return config


def test_integration():
    """测试API增强器与实际配置的集成"""
    print("=" * 60)
    print("调试API增强器集成问题")
    print("=" * 60)
    
    # 加载用户的实际配置
    config_path = "Config/dolphinscheduler_fixed.json"
    print(f"加载配置文件: {config_path}")
    
    try:
        config_data = load_config_from_json(config_path)
        print(f"配置加载成功，模式: {config_data.get('mode', 0)}")
        
        # 创建ScannerConfig对象
        config = create_scanner_config_from_json(config_data)
        print(f"ScannerConfig创建成功，debug_mode: {config.debug_mode}")
        
        # 创建DocContentCrawler
        crawler = DocContentCrawler(config)
        print(f"DocContentCrawler创建成功")
        
        # 测试URL
        url = config.start_url
        print(f"测试URL: {url}")
        
        # 获取页面内容
        print("获取页面内容...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html_content = response.text
        print(f"页面大小: {len(html_content)} 字符")
        
        # 测试API增强器
        print("\n测试API增强器...")
        enhanced_html, is_enhanced, api_info = crawler.api_enhancer.enhance_api_content(html_content, url)
        
        print(f"API检测结果:")
        print(f"  是否为API文档: {crawler.api_enhancer.is_api_documentation(url, BeautifulSoup(html_content, 'html.parser'))}")
        print(f"  是否增强: {is_enhanced}")
        print(f"  API项数: {api_info.get('total_items', 0)}")
        
        if is_enhanced:
            print(f"  插入标题数: {api_info.get('inserted_count', 0)}")
            
            # 检查增强后的HTML
            enhanced_soup = BeautifulSoup(enhanced_html, 'html.parser')
            headings = enhanced_soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            print(f"  增强后标题数: {len(headings)}")
            
            if headings:
                print(f"  前5个标题:")
                for i, heading in enumerate(headings[:5]):
                    print(f"    {i+1}. {heading.name}: {heading.get_text(strip=True)[:50]}")
        
        # 测试完整的转换流程
        print("\n测试完整转换流程...")
        markdown_content = crawler._convert_to_markdown(html_content, url, "API Documentation")
        
        # 检查Markdown中的标题
        lines = markdown_content.split('\n')
        heading_lines = [line for line in lines if line.strip().startswith('#')]
        print(f"Markdown标题数: {len(heading_lines)}")
        
        if heading_lines:
            print(f"前5个Markdown标题:")
            for i, line in enumerate(heading_lines[:5]):
                print(f"  {i+1}. {line.strip()[:80]}")
        
        # 检查是否包含_get_attr方法
        get_attr_found = '_get_attr' in markdown_content
        print(f"\n是否找到_get_attr方法: {get_attr_found}")
        
        if get_attr_found:
            # 查找_get_attr周围的内容
            lines = markdown_content.split('\n')
            for i, line in enumerate(lines):
                if '_get_attr' in line:
                    print(f"_get_attr上下文 (行{i}):")
                    start = max(0, i-2)
                    end = min(len(lines), i+3)
                    for j in range(start, end):
                        marker = ">>> " if j == i else "    "
                        print(f"{marker}{lines[j]}")
                    break
        
        return is_enhanced and api_info.get('total_items', 0) > 0
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("API增强器集成调试")
    
    success = test_integration()
    
    print("\n" + "=" * 60)
    print("调试结果")
    print("=" * 60)
    print(f"集成测试: {'✓ 通过' if success else '✗ 失败'}")
    
    if success:
        print("\nAPI增强器集成正常，问题可能在其他地方。")
    else:
        print("\nAPI增强器集成有问题，需要进一步调试。")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)