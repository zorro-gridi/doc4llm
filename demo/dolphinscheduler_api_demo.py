#!/usr/bin/env python3
"""
DolphinScheduler API文档处理演示

演示如何使用doc4llm的API文档增强功能来处理DolphinScheduler API文档：
1. 爬取API文档页面
2. 自动识别和增强API结构
3. 生成带有标题层级的Markdown文档
4. 使用API文档读取器提取特定内容

使用方法：
    python demo/dolphinscheduler_api_demo.py
"""

import os
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from doc4llm.crawler.DocContentCrawler import DocContentCrawler
from doc4llm.doc_rag.reader.api_doc_reader import APIDocReaderAPI
from doc4llm.scanner.config import ScannerConfig


def load_dolphinscheduler_config():
    """加载DolphinScheduler专用配置"""
    config_path = project_root / "doc4llm/config/dolphinscheduler_config.json"
    
    if not config_path.exists():
        print(f"配置文件不存在: {config_path}")
        return None
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    
    # 创建ScannerConfig实例
    config = ScannerConfig()
    
    # 更新配置
    for key, value in config_data.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return config


def demo_crawl_api_documentation():
    """演示1: 爬取API文档"""
    print("=" * 60)
    print("演示1: 爬取DolphinScheduler API文档")
    print("=" * 60)
    
    # 加载配置
    config = load_dolphinscheduler_config()
    if not config:
        print("无法加载配置文件")
        return
    
    # 创建爬虫实例
    crawler = DocContentCrawler(config)
    
    # 设置目标URL
    target_url = "https://dolphinscheduler.apache.org/python/main/api.html"
    
    print(f"开始爬取: {target_url}")
    print(f"输出目录: {crawler.doc_root_dir}")
    
    # 爬取单个URL
    result = crawler._crawl_single_url(target_url)
    
    if result['success']:
        print(f"✓ 爬取成功!")
        print(f"  文件路径: {result['filepath']}")
        print(f"  页面标题: {result['title']}")
        
        # 检查生成的文件
        if os.path.exists(result['filepath']):
            with open(result['filepath'], 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"  文件大小: {len(content)} 字符")
            
            # 统计标题数量
            import re
            headings = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
            print(f"  检测到标题: {len(headings)} 个")
            
            if headings:
                print("  前5个标题:")
                for i, heading in enumerate(headings[:5]):
                    print(f"    {i+1}. {heading}")
        
    else:
        print(f"✗ 爬取失败: {result.get('error', '未知错误')}")


def demo_api_reader():
    """演示2: 使用API文档读取器"""
    print("\n" + "=" * 60)
    print("演示2: 使用API文档读取器")
    print("=" * 60)
    
    # 设置知识库目录
    kb_dir = project_root / "md_docs"
    
    if not kb_dir.exists():
        print(f"知识库目录不存在: {kb_dir}")
        print("请先运行演示1爬取文档")
        return
    
    try:
        # 创建API文档读取器
        reader = APIDocReaderAPI(
            base_dir=str(kb_dir),
            search_mode="fuzzy",
            fuzzy_threshold=0.6,
            debug_mode=True
        )
        
        print(f"知识库目录: {kb_dir}")
        
        # 列出可用文档
        documents = reader.list_available_documents()
        print(f"可用文档数量: {len(documents)}")
        
        if documents:
            print("前5个文档:")
            for i, doc in enumerate(documents[:5]):
                print(f"  {i+1}. {doc}")
        
        # 分析API结构
        print("\n分析API结构...")
        api_structure = reader.analyze_api_structure()
        
        print(f"API文档数量: {len(api_structure['api_documents'])}")
        print(f"检测到的类: {len(api_structure['classes'])}")
        print(f"检测到的方法: {len(api_structure['methods'])}")
        print(f"检测到的属性: {len(api_structure['properties'])}")
        
        # 尝试提取特定API内容
        print("\n尝试提取特定API内容...")
        
        # 定义要提取的API项
        api_sections = [
            {
                "title": "API — apache-dolphinscheduler 4.1.0-dev documentation",
                "headings": ["Engine", "Task", "Workflow"],
                "doc_set": "DolphinScheduler_API_Docs@latest"
            }
        ]
        
        # 使用API模式提取
        result = reader.extract_api_sections(api_sections, api_mode=True)
        
        print(f"提取结果:")
        print(f"  总行数: {result.total_line_count}")
        print(f"  文档数量: {result.document_count}")
        print(f"  是否需要后处理: {result.requires_processing}")
        
        if result.contents:
            print(f"  提取的内容键:")
            for key in list(result.contents.keys())[:3]:
                content_preview = result.contents[key][:200] + "..." if len(result.contents[key]) > 200 else result.contents[key]
                print(f"    - {key}: {len(result.contents[key])} 字符")
                print(f"      预览: {content_preview}")
        
    except Exception as e:
        print(f"API文档读取器演示失败: {e}")
        import traceback
        traceback.print_exc()


def demo_api_name_extraction():
    """演示3: 按API名称提取内容"""
    print("\n" + "=" * 60)
    print("演示3: 按API名称提取内容")
    print("=" * 60)
    
    kb_dir = project_root / "md_docs"
    
    if not kb_dir.exists():
        print(f"知识库目录不存在: {kb_dir}")
        return
    
    try:
        # 创建API文档读取器
        reader = APIDocReaderAPI(
            base_dir=str(kb_dir),
            search_mode="fuzzy",
            fuzzy_threshold=0.5,
            debug_mode=True
        )
        
        # 定义要提取的API名称
        api_names = [
            "Engine",
            "Task", 
            "Workflow",
            "_get_attr",
            "add_in",
            "add_out"
        ]
        
        print(f"尝试提取以下API项:")
        for name in api_names:
            print(f"  - {name}")
        
        # 按API名称提取内容
        results = reader.extract_api_by_names(
            api_names=api_names,
            doc_set="DolphinScheduler_API_Docs@latest",
            api_type="class"
        )
        
        print(f"\n提取结果:")
        print(f"成功提取: {len(results)} / {len(api_names)} 个API项")
        
        for api_name, content in results.items():
            content_preview = content[:150] + "..." if len(content) > 150 else content
            print(f"\n{api_name}:")
            print(f"  长度: {len(content)} 字符")
            print(f"  预览: {content_preview}")
        
        # 显示未找到的API项
        not_found = set(api_names) - set(results.keys())
        if not_found:
            print(f"\n未找到的API项: {list(not_found)}")
        
    except Exception as e:
        print(f"API名称提取演示失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    print("DolphinScheduler API文档处理演示")
    print("=" * 60)
    
    # 检查项目结构
    print(f"项目根目录: {project_root}")
    print(f"当前工作目录: {os.getcwd()}")
    
    # 运行演示
    try:
        # 演示1: 爬取API文档
        demo_crawl_api_documentation()
        
        # 演示2: 使用API文档读取器
        demo_api_reader()
        
        # 演示3: 按API名称提取内容
        demo_api_name_extraction()
        
    except KeyboardInterrupt:
        print("\n用户中断演示")
    except Exception as e:
        print(f"\n演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n演示完成!")


if __name__ == "__main__":
    main()