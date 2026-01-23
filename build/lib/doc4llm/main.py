"""
doc4llm - Web URL扫描和信息安全收集工具
主入口文件
"""
import argparse
import json
import os
import sys
from datetime import datetime

from colorama import Fore, Style

from doc4llm.scanner import UltimateURLScanner, ScannerConfig
from doc4llm.scanner import OutputLogger

# 禁用SSL警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 初始化输出日志记录器（使用默认路径，稍后会根据配置重新初始化）
output_logger = None
original_stdout = sys.stdout
original_stderr = sys.stderr


def _init_output_logger(output_log_file='results/output.out', max_lines=None):
    """初始化输出日志记录器"""
    global output_logger, original_stdout
    # 关闭旧的日志记录器（如果存在）
    if output_logger:
        output_logger.close()
    # 创建新的日志记录器
    output_logger = OutputLogger(output_log_file, max_lines=max_lines)
    # 重定向stdout和stderr到日志记录器
    sys.stdout = output_logger
    sys.stderr = output_logger


def main():
    try:
        # 先初始化一个临时的输出日志记录器
        _init_output_logger()

        # 打印程序信息
        _print_program_info()

        # 解析命令行参数
        args = _parse_arguments()

        # 加载配置
        config_data = _load_config(args.config_file)

        # 验证参数（在配置加载后，以便检查 CSV 文件状态）
        _validate_arguments(args, config_data)

        # 根据配置重新初始化输出日志记录器
        output_log_file = config_data.get('output_log_file', 'results/output.out')
        log_max_lines = config_data.get('log_max_lines', 10000)
        _init_output_logger(output_log_file, max_lines=log_max_lines)

        # 获取配置值的辅助函数
        def get_config_value(key, default=None):
            return getattr(args, key, None) if getattr(args, key, None) is not None else config_data.get(key, default)

        # 创建配置对象
        config = _create_config(args, config_data, get_config_value)

        # 打印配置信息
        _print_config_info(config)

        # 检查是否为文档爬取模式
        # mode: 0=仅爬取.csv url文件, 1=继续抓取文档内容, 2=继续抓取doc url(锚点链接), 3=依次执行内容爬取和锚点提取
        if config.mode == 1:
            # 文档爬取模式
            doc_name_display = config.doc_name or "auto-detected"
            print(f"{Fore.GREEN}=== 文档爬取模式已启用 ==={Style.RESET_ALL}")
            print(f"{Fore.CYAN}=== 文档输出目录: {config.doc_dir}/{doc_name_display}@{config.doc_version}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}=== 文档版本: {config.doc_version}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}=== 最大爬取深度: {config.doc_max_depth}{Style.RESET_ALL}")

            # 检查是否需要执行URL扫描
            csv_file_exists_and_has_content = False
            if config.force_scan == 0 and os.path.exists(config.output_file):
                # 检查CSV文件是否有内容（除了表头）
                try:
                    with open(config.output_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if len(lines) > 1:  # 超过表头行
                            csv_file_exists_and_has_content = True
                            print(f"{Fore.YELLOW}=== 检测到CSV文件已存在且有内容，跳过URL扫描 ==={Style.RESET_ALL}")
                            print(f"{Fore.YELLOW}=== 使用 -force-scan 1 可强制刷新CSV文件 ==={Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.YELLOW}=== 检查CSV文件时出错，将执行URL扫描: {e} ==={Style.RESET_ALL}")

            # 第一步：执行URL扫描，将结果保存到CSV
            if config.force_scan == 1 or not csv_file_exists_and_has_content:
                print(f"{Fore.CYAN}=== 第一步：执行URL扫描 ==={Style.RESET_ALL}")
                if not args.start_url and not args.url_file:
                    print(f"{Fore.RED}错误：CSV文件不存在或为空，需要指定 -u 或 -f 进行URL扫描{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}提示：使用 -force-scan 1 可强制刷新CSV文件{Style.RESET_ALL}")
                    sys.exit(1)
                if args.start_url:
                    _scan_single_url(config, args.start_url)
                elif args.url_file:
                    _scan_multiple_urls(config, args.url_file, get_config_value)

            # 第二步：从CSV文件读取URL并爬取文档
            print(f"{Fore.CYAN}=== 第二步：从CSV文件爬取文档内容 ==={Style.RESET_ALL}")

            # === NEW: 检查是否已通过内联提取完成 ===
            if config.enable_inline_extraction:
                print(f"{Fore.YELLOW}=== 已在扫描过程中实时提取内容，跳过传统爬取 ==={Style.RESET_ALL}")
            else:
                # 如果跳过了URL扫描且没有start_url，从CSV文件中读取第一个URL作为start_url
                if not config.start_url and csv_file_exists_and_has_content:
                    try:
                        import csv
                        with open(config.output_file, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            first_row = next(reader, None)
                            if first_row and 'URL' in first_row:
                                config.start_url = first_row['URL']
                                print(f"{Fore.CYAN}=== 从CSV文件读取起始URL: {config.start_url} ==={Style.RESET_ALL}")
                    except Exception as e:
                        print(f"{Fore.RED}错误：无法从CSV文件读取起始URL: {e}{Style.RESET_ALL}")
                        sys.exit(1)

                from doc4llm.crawler.DocContentCrawler import DocContentCrawler
                doc_crawler = DocContentCrawler(config)
                doc_crawler.process_documentation_site(config.start_url)
            # === END NEW ===
        elif config.mode == 2:
            # 锚点链接爬取模式
            print(f"{Fore.GREEN}=== 锚点链接爬取模式已启用 ==={Style.RESET_ALL}")
            doc_name_display = config.doc_name or "auto-detected"
            print(f"{Fore.CYAN}=== 输出目录: {config.doc_dir}/{doc_name_display}@{config.doc_version}{Style.RESET_ALL}")

            # 检查是否需要执行URL扫描
            csv_file_exists_and_has_content = False
            if config.force_scan == 0 and os.path.exists(config.output_file):
                # 检查CSV文件是否有内容（除了表头）
                try:
                    with open(config.output_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if len(lines) > 1:  # 超过表头行
                            csv_file_exists_and_has_content = True
                            print(f"{Fore.YELLOW}=== 检测到CSV文件已存在且有内容，跳过URL扫描 ==={Style.RESET_ALL}")
                            print(f"{Fore.YELLOW}=== 使用 -force-scan 1 可强制刷新CSV文件 ==={Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.YELLOW}=== 检查CSV文件时出错，将执行URL扫描: {e} ==={Style.RESET_ALL}")

            # 第一步：执行URL扫描，将结果保存到CSV
            if config.force_scan == 1 or not csv_file_exists_and_has_content:
                print(f"{Fore.CYAN}=== 第一步：执行URL扫描 ==={Style.RESET_ALL}")
                if not args.start_url and not args.url_file:
                    print(f"{Fore.RED}错误：CSV文件不存在或为空，需要指定 -u 或 -f 进行URL扫描{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}提示：使用 -force-scan 1 可强制刷新CSV文件{Style.RESET_ALL}")
                    sys.exit(1)
                if args.start_url:
                    _scan_single_url(config, args.start_url)
                elif args.url_file:
                    _scan_multiple_urls(config, args.url_file, get_config_value)

            # 如果跳过了URL扫描且没有start_url，从CSV文件中读取第一个URL作为start_url
            if not config.start_url and csv_file_exists_and_has_content:
                try:
                    import csv
                    with open(config.output_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        first_row = next(reader, None)
                        if first_row and 'URL' in first_row:
                            config.start_url = first_row['URL']
                            print(f"{Fore.CYAN}=== 从CSV文件读取起始URL: {config.start_url} ==={Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}错误：无法从CSV文件读取起始URL: {e}{Style.RESET_ALL}")
                    sys.exit(1)

            # 确保 doc_name 被正确设置
            if not config.doc_name and config.start_url:
                from urllib.parse import urlparse
                parsed = urlparse(config.start_url)
                config.doc_name = parsed.netloc.replace('.', '_')
                print(f"{Fore.CYAN}=== 从起始URL自动设置文档名称: {config.doc_name} ==={Style.RESET_ALL}")
                # 更新显示的文档名称
                doc_name_display = config.doc_name
                print(f"{Fore.CYAN}=== 输出目录: {config.doc_dir}/{doc_name_display}@{config.doc_version}{Style.RESET_ALL}")

            # 第二步：从CSV文件读取URL并提取锚点链接
            print(f"{Fore.CYAN}=== 第二步：从CSV文件提取锚点链接 ==={Style.RESET_ALL}")

            # === NEW: 检查是否已通过内联提取完成 ===
            if config.enable_inline_extraction:
                print(f"{Fore.YELLOW}=== 已在扫描过程中实时提取TOC，跳过传统爬取 ==={Style.RESET_ALL}")
            else:
                from doc4llm.crawler.DocUrlCrawler import DocUrlCrawler
                anchor_crawler = DocUrlCrawler(config)
                anchor_crawler.process(csv_file=config.output_file)
            # === END NEW ===
        elif config.mode == 3:
            # 组合模式：依次执行文档内容爬取和锚点链接提取
            print(f"{Fore.GREEN}=== 组合模式已启用：依次执行文档内容爬取和锚点链接提取 ==={Style.RESET_ALL}")
            print(f"{Fore.CYAN}=== 文档输出目录: {config.doc_dir}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}=== 文档版本: {config.doc_version}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}=== 最大爬取深度: {config.doc_max_depth}{Style.RESET_ALL}")

            # 检查是否需要执行URL扫描
            csv_file_exists_and_has_content = False
            if config.force_scan == 0 and os.path.exists(config.output_file):
                # 检查CSV文件是否有内容（除了表头）
                try:
                    with open(config.output_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if len(lines) > 1:  # 超过表头行
                            csv_file_exists_and_has_content = True
                            print(f"{Fore.YELLOW}=== 检测到CSV文件已存在且有内容，跳过URL扫描 ==={Style.RESET_ALL}")
                            print(f"{Fore.YELLOW}=== 使用 -force-scan 1 可强制刷新CSV文件 ==={Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.YELLOW}=== 检查CSV文件时出错，将执行URL扫描: {e} ==={Style.RESET_ALL}")

            # 第一步：执行URL扫描，将结果保存到CSV
            if config.force_scan == 1 or not csv_file_exists_and_has_content:
                print(f"{Fore.CYAN}=== 第一步：执行URL扫描 ==={Style.RESET_ALL}")
                if not args.start_url and not args.url_file:
                    print(f"{Fore.RED}错误：CSV文件不存在或为空，需要指定 -u 或 -f 进行URL扫描{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}提示：使用 -force-scan 1 可强制刷新CSV文件{Style.RESET_ALL}")
                    sys.exit(1)
                if args.start_url:
                    _scan_single_url(config, args.start_url)
                elif args.url_file:
                    _scan_multiple_urls(config, args.url_file, get_config_value)

            # 如果跳过了URL扫描且没有start_url，从CSV文件中读取第一个URL作为start_url
            if not config.start_url and csv_file_exists_and_has_content:
                try:
                    import csv
                    with open(config.output_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        first_row = next(reader, None)
                        if first_row and 'URL' in first_row:
                            config.start_url = first_row['URL']
                            print(f"{Fore.CYAN}=== 从CSV文件读取起始URL: {config.start_url} ==={Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}错误：无法从CSV文件读取起始URL: {e}{Style.RESET_ALL}")
                    sys.exit(1)

            # 确保 doc_name 被正确设置，使 DocContentCrawler 和 DocUrlCrawler 使用相同的 doc_root_dir
            if not config.doc_name and config.start_url:
                from urllib.parse import urlparse
                parsed = urlparse(config.start_url)
                config.doc_name = parsed.netloc.replace('.', '_')
                print(f"{Fore.CYAN}=== 从起始URL自动设置文档名称: {config.doc_name} ==={Style.RESET_ALL}")

            # 第二步：从CSV文件读取URL并爬取文档内容
            print(f"{Fore.CYAN}=== 第二步：从CSV文件爬取文档内容 ==={Style.RESET_ALL}")

            # 第三步：从CSV文件读取URL并提取锚点链接
            print(f"{Fore.CYAN}=== 第三步：从CSV文件提取锚点链接 ==={Style.RESET_ALL}")

            # === NEW: 检查是否已通过内联提取完成 ===
            if config.enable_inline_extraction:
                print(f"{Fore.YELLOW}=== 已在扫描过程中实时提取内容和TOC，跳过传统爬取 ==={Style.RESET_ALL}")
            else:
                # 传统流程：内容爬取
                from doc4llm.crawler.DocContentCrawler import DocContentCrawler
                doc_crawler = DocContentCrawler(config)
                doc_crawler.process_documentation_site(config.start_url)

                # 传统流程：TOC爬取
                from doc4llm.crawler.DocUrlCrawler import DocUrlCrawler
                anchor_crawler = DocUrlCrawler(config)
                anchor_crawler.process(csv_file=config.output_file)
            # === END NEW ===
        else:
            # 执行扫描
            if args.start_url:
                _scan_single_url(config, args.start_url)
            elif args.url_file:
                _scan_multiple_urls(config, args.url_file, get_config_value)

    except Exception as e:
        print(f"{Fore.RED}程序运行出错: {type(e).__name__}: {e}{Style.RESET_ALL}")
        sys.exit(1)


def _print_program_info():
    """打印程序信息"""
    print(f"{Fore.YELLOW}=============================================={Style.RESET_ALL}")
    print(f"{Fore.YELLOW}=== doc4llm v.1.0.0 ===")
    print(f"{Fore.YELLOW}=== BY: Zorro  GitHub: https://github.com/zorro-gridi/doc4llm")
    print(f"{Fore.YELLOW}=== 重复的URL不会重复扫描, 结果返回相同的URL不会重复展示")
    print(f"{Fore.CYAN}=== 所有输出将同时记录到 results/output.out 文件中")
    print(f"{Fore.CYAN}=== 扫描开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def _print_usage_examples():
    """打印常用参数示例"""
    examples = [
        ("基本URL扫描", "python main.py -u https://example.com"),
        ("文档爬取模式", "python main.py -u https://example.com -mode 3 -force-scan 1"),
        ("批量URL扫描", "python main.py -f urls.txt -workers 20"),
        ("使用配置文件", "python main.py -config custom_config.json"),
    ]
    print(f"\n{Fore.CYAN}=== 常用命令示例 ==={Style.RESET_ALL}")
    for desc, cmd in examples:
        print(f"{Fore.YELLOW}{desc}:{Style.RESET_ALL} {cmd}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")


def _parse_arguments():
    """解析命令行参数"""
    try:
        parser = argparse.ArgumentParser(
            description="doc4llm 扫描工具",
            epilog="提示: 使用 -force-scan 而非 -force_scan（参数名用连字符）",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        parser.add_argument('-u', dest='start_url', type=str, help='起始URL')
        parser.add_argument('-f', dest='url_file', type=str, help='批量URL文件，每行一个URL')
        parser.add_argument('-workers', dest='max_workers', type=int, help='最大线程数')
        parser.add_argument('-delay', dest='delay', type=float, help='请求延迟（秒）')
        parser.add_argument('-timeout', dest='timeout', type=int, help='请求超时（秒）')
        parser.add_argument('-depth', dest='max_depth', type=int, help='最大递归深度')
        parser.add_argument('-out', dest='output_file', type=str, help='实时输出文件')
        parser.add_argument('-proxy', dest='proxy', type=str, help='代理设置')
        parser.add_argument('-debug', dest='debug_mode', type=int, help='调试模式 1开启 0关闭')
        parser.add_argument('-scope', dest='url_scope_mode', type=int, help='URL扫描范围模式 0主域 1外部一次 2全放开 3白名单模式')
        parser.add_argument('-danger', dest='danger_filter_enabled', type=int, default=1, help='危险接口过滤 1开启 0关闭 (默认: 1)')
        parser.add_argument('-fuzz', dest='fuzz', type=int, default=0, help='是否启用自定义URL拼接参数 1启用 0关闭 (默认: 0)')
        parser.add_argument('-config', dest='config_file', type=str, default='doc4llm/config/config.json', help='配置文件路径 (默认: doc4llm/config/config.json)')
        parser.add_argument('-force-scan', dest='force_scan', type=int, default=0, help='强制启动URL扫描器 (mode 1/2/3时有效，1=强制扫描刷新CSV，0=CSV不为空则跳过扫描) (默认: 0)')
        # 文档爬取模式参数
        parser.add_argument('-mode', dest='mode', type=int, default=0, help='爬取模式 0=仅爬取CSV 1=抓取文档内容 2=抓取锚点链接 3=依次执行内容爬取和锚点提取 (默认: 0)')
        parser.add_argument('-doc-dir', dest='doc_dir', type=str, help='文档输出目录路径')
        parser.add_argument('-doc-name', dest='doc_name', type=str, help='文档名称（覆盖自动检测）')
        parser.add_argument('-doc-version', dest='doc_version', type=str, help='文档版本号 (默认: latest)')
        parser.add_argument('-doc-depth', dest='doc_max_depth', type=int, help='文档爬取最大深度 (默认: 10)')
        parser.add_argument('-doc-toc-selector', dest='doc_toc_selector', type=str, help='TOC区域CSS选择器 (如: .toc, #navigation)')
        return parser.parse_args()
    except SystemExit:
        # argparse 触发 --help 或参数错误时会抛出 SystemExit
        # 打印使用示例后再退出
        _print_usage_examples()
        raise
    except Exception as e:
        print(f"{Fore.RED}解析命令行参数时出错: {type(e).__name__}: {e}{Style.RESET_ALL}")
        _print_usage_examples()
        sys.exit(1)


def _validate_arguments(args, config_data):
    """验证命令行参数

    验证逻辑：
    - mode 0 或 force_scan=1：需要指定扫描目标（-u 或 -f）
    - mode 1/2/3 且 force_scan=0：
      - 如果 CSV 文件存在且有内容：不需要 -u 或 -f
      - 如果 CSV 文件不存在或为空：需要 -u 或 -f
    """
    # 优先使用命令行参数（如果指定），其次使用配置文件中的值
    mode = getattr(args, 'mode', None)
    if mode is None:
        mode = config_data.get('mode', 0)

    force_scan = getattr(args, 'force_scan', None)
    if force_scan is None:
        force_scan = config_data.get('force_scan', 0)

    output_file = config_data.get('output_file', 'results/实时输出文件.csv')

    # 检查是否需要扫描目标
    needs_scan_target = True

    if mode in [1, 2, 3] and force_scan == 0:
        # mode 1/2/3 且不强制扫描，检查 CSV 文件状态
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if len(lines) > 1:  # CSV 文件有内容（超过表头）
                        needs_scan_target = False
            except Exception:
                pass  # 读取失败，保守起见需要扫描目标

    # 根据判断结果验证
    if needs_scan_target and not args.start_url and not args.url_file:
        print(f"{Fore.RED}错误：必须通过 -u 或 -f 至少指定一个扫描目标！{Style.RESET_ALL}")
        if mode in [1, 2, 3]:
            print(f"{Fore.YELLOW}提示：mode {mode} 时，如果CSV文件已存在且有内容，可以不指定 -u 或 -f{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}提示：或者使用 -force-scan 1 强制刷新CSV文件{Style.RESET_ALL}")
        _print_usage_examples()
        sys.exit(1)


def _load_config(config_file='doc4llm/config/config.json'):
    """加载配置文件"""
    try:
        config_path = config_file
        default_config = {
            "start_url": None,
            "proxy": None,
            "delay": 0.1,
            "max_workers": 30,
            "timeout": 20,
            "max_depth": 5,
            "blacklist_domains": ["www.w3.org", "www.baidu.com", "github.com"],
            "whitelist_domains": ["example.com", "test.com"],
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            },
            "output_file": "results/实时输出文件.csv",
            "color_output": True,
            "verbose": True,
            "extension_blacklist": [".css", ".mp4"],
            "max_urls": 10000,
            "smart_concatenation": True,
            "debug_mode": 0,
            "is_duplicate": 0,
            "url_scope_mode": 0,
            "danger_filter_enabled": 1,
            "danger_api_list": ["del","delete","insert","logout","loginout","remove","drop","shutdown","stop","poweroff","restart","rewrite","terminate","deactivate","halt","disable"],
            "allowed_api_list": [],
            "custom_base_url": ["https://www.canopyu.com/"],
            "path_route": ["/api/v1/user/login"],
            "api_route": ["/api/v1/user/login"],
            "fuzz": 0,
            # URL过滤配置
            "exclude_fuzzy": ["/blog/", "/news/", "/community/", "/forum/"],
            # 标题过滤配置
            "title_filter_list": ["Page Not Found"],
            "title_cleanup_patterns": [],
            # 状态码过滤配置
            "status_code_filter": [404, 503, 502, 504, 403, 401, 500],
            # 文档爬取模式配置
            "mode": 0,  # 0=仅爬取CSV, 1=抓取文档内容, 2=抓取锚点链接, 3=依次执行内容爬取和锚点提取
            "force_scan": 0,  # mode 1/2/3时，是否强制启动URL扫描器（0：CSV不为空则跳过，1：强制扫描）
            "results_dir": "results",  # 结果文件保存目录
            "doc_dir": "md_docs",
            "doc_name": None,
            "doc_version": "latest",
            "toc_url_filters": {
                "subdomains": ["docs.", "api.", "developer."],
                "fuzzy_match": ["/docs/", "/guide/", "/tutorial/", "/api/", "/reference/"],
                "exclude_fuzzy": ["/blog/", "/news/", "/community/", "/forum/"]
            },
            "doc_max_depth": 10,
            "doc_timeout": 30,
            "doc_toc_selector": None,  # CSS选择器，如 '.toc', '#navigation', '.sidebar-nav, .table-of-contents'
            # 输出文件路径配置
            "output_log_file": "results/output.out",
            "debug_log_file": "results/debug.log",
            # 日志文件行数限制配置
            "log_max_lines": 10000
        }
        if not os.path.exists(config_path):
            print(f"{Fore.YELLOW}=== 配置文件 {config_path} 不存在，使用默认配置 ==={Style.RESET_ALL}")
            return default_config
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"{Fore.RED}读取配置文件时出错: {type(e).__name__}: {e}{Style.RESET_ALL}")
        sys.exit(1)


def _load_headers(headers_path):
    """加载 headers 文件"""
    if not headers_path:
        return None
    try:
        with open(headers_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"{Fore.YELLOW}警告: 无法加载 headers 文件 {headers_path}: {e}{Style.RESET_ALL}")
        return None


def _create_config(args, config_data, get_config_value):
    """创建配置对象"""
    print(f"{Fore.CYAN}=== 正在初始化扫描器...{Style.RESET_ALL}")

    # 加载 headers 文件
    headers_path = config_data.get('headers_path')
    headers = _load_headers(headers_path) if headers_path else get_config_value('headers')

    return ScannerConfig(
        start_url=get_config_value('start_url'),
        proxy=get_config_value('proxy'),
        delay=get_config_value('delay', 0.1),
        max_workers=get_config_value('max_workers', 30),
        timeout=get_config_value('timeout', 20),
        max_depth=get_config_value('max_depth', 5),
        blacklist_domains=get_config_value('blacklist_domains'),
        whitelist_domains=get_config_value('whitelist_domains'),
        headers=headers,
        output_file=get_config_value('output_file', 'results/实时输出文件.csv'),
        color_output=get_config_value('color_output', True),
        verbose=get_config_value('verbose', True),
        extension_blacklist=get_config_value('extension_blacklist', ['.css','.mp4']),
        max_urls=get_config_value('max_urls', 10000),
        smart_concatenation=get_config_value('smart_concatenation', True),
        debug_mode=get_config_value('debug_mode', 0),
        url_scope_mode=get_config_value('url_scope_mode', 0),
        danger_filter_enabled=get_config_value('danger_filter_enabled', 1),
        danger_api_list=get_config_value('danger_api_list'),
        allowed_api_list=get_config_value('allowed_api_list'),
        is_duplicate=get_config_value('is_duplicate', 0),
        custom_base_url=get_config_value('custom_base_url', []),
        path_route=get_config_value('path_route', []),
        api_route=get_config_value('api_route', []),
        fuzz=get_config_value('fuzz', 0),
        # URL过滤参数
        exclude_fuzzy=get_config_value('exclude_fuzzy'),
        # 标题过滤参数
        title_filter_list=get_config_value('title_filter_list'),
        title_cleanup_patterns=get_config_value('title_cleanup_patterns'),
        # 状态码过滤参数
        status_code_filter=get_config_value('status_code_filter'),
        # 文档爬取模式参数
        mode=get_config_value('mode', 0),
        force_scan=get_config_value('force_scan', 0),
        results_dir=get_config_value('results_dir', 'results'),
        doc_dir=get_config_value('doc_dir'),
        doc_name=get_config_value('doc_name'),
        doc_version=get_config_value('doc_version', 'latest'),
        toc_url_filters=get_config_value('toc_url_filters'),
        doc_max_depth=get_config_value('doc_max_depth', 10),
        doc_timeout=get_config_value('doc_timeout', 30),
        doc_toc_selector=get_config_value('doc_toc_selector'),
        # 输出文件路径参数
        output_log_file=get_config_value('output_log_file', 'results/output.out'),
        debug_log_file=get_config_value('debug_log_file', 'results/debug.log'),
        # 日志文件行数限制
        log_max_lines=get_config_value('log_max_lines', 10000),
        # TOC 过滤配置
        toc_filter=get_config_value('toc_filter'),
        # 内容过滤器配置
        content_filter=get_config_value('content_filter', {}),
        # 内联提取配置
        enable_inline_extraction=get_config_value('enable_inline_extraction', 1)
    )


def _print_config_info(config):
    """打印配置信息"""
    print(f"{Fore.CYAN}=============================================={Style.RESET_ALL}")
    print(f"{Fore.CYAN}=== 开始链接: {config.start_url}")
    print(f"{Fore.CYAN}=== 代理设置: {config.proxy}")
    print(f"{Fore.CYAN}=== 延迟设置: {config.delay}")
    print(f"{Fore.CYAN}=== 最大线程: {config.max_workers}")
    print(f"{Fore.CYAN}=== 请求超时: {config.timeout}")
    print(f"{Fore.CYAN}=== 最大深度: {config.max_depth}")
    print(f"{Fore.CYAN}=== 黑域名单: {config.blacklist_domains}")
    print(f"{Fore.CYAN}=== 白域名单: {config.whitelist_domains}")
    print(f"{Fore.CYAN}=== 请求的头: {config.headers}")
    print(f"{Fore.CYAN}=== 实时文件: {config.output_file}")
    print(f"{Fore.CYAN}=== 彩色输出: {config.color_output}")
    print(f"{Fore.CYAN}=== 详细输出: {config.verbose}")
    print(f"{Fore.CYAN}=== 跳过扩展: {config.extension_blacklist}")
    print(f"{Fore.CYAN}=== 最大请求: {config.max_urls}")
    print(f"{Fore.CYAN}=== 智能拼接: {config.smart_concatenation}")
    print(f"{Fore.CYAN}=== 调试模式: {config.debug_mode}")
    print(f"{Fore.CYAN}=== 扫描范围: {config.url_scope_mode}")
    print(f"{Fore.CYAN}=== 危险过滤: {config.danger_filter_enabled}")
    print(f"{Fore.CYAN}=== 危险接口: {config.danger_api_list}")
    print(f"{Fore.CYAN}=== 允许接口: {config.allowed_api_list}")
    print(f"{Fore.CYAN}=== 开启重复: {config.is_duplicate}")
    print(f"{Fore.CYAN}=== 自定地址: {config.custom_base_url}")
    print(f"{Fore.CYAN}=== 自定路径: {config.path_route}")
    print(f"{Fore.CYAN}=== 自定API: {config.api_route}")
    print(f"{Fore.CYAN}=== 启用fuzz: {config.fuzz}")
    print(f"{Fore.CYAN}=============================================={Style.RESET_ALL}")


def _scan_single_url(config, start_url):
    """扫描单个URL"""
    print(f"{Fore.YELLOW}开始扫描: {start_url}{Style.RESET_ALL}")
    scanner = UltimateURLScanner(config)
    scanner.start_scanning()


def _scan_multiple_urls(config, url_file, get_config_value):
    """扫描多个URL"""
    try:
        if not os.path.exists(url_file):
            print(f"{Fore.RED}错误：URL文件 {url_file} 不存在！{Style.RESET_ALL}")
            sys.exit(1)

        with open(url_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]

        print(f"{Fore.YELLOW}从文件读取到 {len(urls)} 个URL，开始批量扫描...{Style.RESET_ALL}")

        # 加载 headers 文件
        headers_path = get_config_value('headers_path')
        headers = _load_headers(headers_path) if headers_path else get_config_value('headers')

        all_results = []
        all_external_results = []
        all_danger_results = []
        results_dir = get_config_value('results_dir', 'results')
        batch_summary_file = f"{results_dir}/all_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        for i, url in enumerate(urls, 1):
            try:
                print(f"{Fore.CYAN}[{i}/{len(urls)}] 开始扫描: {url}{Style.RESET_ALL}")
                # 为每个URL创建独立的配置实例
                url_config = ScannerConfig(
                    start_url=url,
                    proxy=get_config_value('proxy'),
                    delay=get_config_value('delay', 0.1),
                    max_workers=get_config_value('max_workers', 30),
                    timeout=get_config_value('timeout', 20),
                    max_depth=get_config_value('max_depth', 5),
                    blacklist_domains=get_config_value('blacklist_domains'),
                    whitelist_domains=get_config_value('whitelist_domains'),
                    headers=headers,
                    output_file=get_config_value('output_file', 'results/实时输出文件.csv'),
                    color_output=get_config_value('color_output', True),
                    verbose=get_config_value('verbose', True),
                    extension_blacklist=get_config_value('extension_blacklist', ['.css','.mp4']),
                    max_urls=get_config_value('max_urls', 10000),
                    smart_concatenation=get_config_value('smart_concatenation', True),
                    debug_mode=get_config_value('debug_mode', 0),
                    url_scope_mode=get_config_value('url_scope_mode', 0),
                    danger_filter_enabled=get_config_value('danger_filter_enabled', 1),
                    danger_api_list=get_config_value('danger_api_list'),
                    is_duplicate=get_config_value('is_duplicate', 0),
                    custom_base_url=get_config_value('custom_base_url', []),
                    path_route=get_config_value('path_route', []),
                    api_route=get_config_value('api_route', []),
                    fuzz=get_config_value('fuzz', 0),
                    # URL过滤参数
                    exclude_fuzzy=get_config_value('exclude_fuzzy'),
                    # 标题过滤参数
                    title_filter_list=get_config_value('title_filter_list'),
                    title_cleanup_patterns=get_config_value('title_cleanup_patterns'),
                    # 状态码过滤参数
                    status_code_filter=get_config_value('status_code_filter'),
                    # 文档爬取模式参数
                    mode=get_config_value('mode', 0),
                    force_scan=get_config_value('force_scan', 0),
                    results_dir=get_config_value('results_dir', 'results'),
                    doc_dir=get_config_value('doc_dir'),
                    doc_name=get_config_value('doc_name'),
                    doc_version=get_config_value('doc_version', 'latest'),
                    toc_url_filters=get_config_value('toc_url_filters'),
                    doc_max_depth=get_config_value('doc_max_depth', 10),
                    doc_timeout=get_config_value('doc_timeout', 30),
                    # 输出文件路径参数
                    output_log_file=get_config_value('output_log_file', 'results/output.out'),
                    debug_log_file=get_config_value('debug_log_file', 'results/debug.log'),
                    # 日志文件行数限制
                    log_max_lines=get_config_value('log_max_lines', 10000),
                    # TOC URL 过滤配置
                    toc_url_filter=get_config_value('toc_url_filter'),
                    # 内容过滤器配置
                    content_filter=get_config_value('content_filter', {}),
                    # 内联提取配置
                    enable_inline_extraction=get_config_value('enable_inline_extraction', 1)
                )
                scanner = UltimateURLScanner(url_config)
                scanner.start_scanning()
                # 收集每个URL的扫描结果
                if hasattr(scanner, 'results'):
                    all_results.extend(scanner.results)
                if hasattr(scanner, 'external_results'):
                    all_external_results.extend(scanner.external_results)
                # 收集危险接口
                if hasattr(scanner, 'config') and hasattr(scanner, 'output_handler'):
                    from doc4llm.scanner import URLMatcher
                    for danger_url in URLMatcher.danger_api_filtered:
                        danger_types = []
                        for danger_api in scanner.config.danger_api_list:
                            if danger_api in danger_url and not danger_url.endswith(".js"):
                                danger_types.append(danger_api)
                        danger_type_str = ", ".join(danger_types) if danger_types else "未知"
                        danger_result = {
                            'url': danger_url,
                            'status': '危险',
                            'title': '危险接口',
                            'length': 0,
                            'redirects': '',
                            'depth': 0,
                            'time': 0,
                            'sensitive': danger_type_str,
                            'sensitive_raw': [{'type': danger_type_str, 'count': 1, 'samples': [danger_url]}],
                            'is_duplicate_signature': False,
                            'content_type': '',
                            'headers_count': 0,
                            'error_type': None,
                            'original_url': url,
                        }
                        all_danger_results.append(danger_result)
            except Exception as e:
                print(f"{Fore.RED}扫描URL {url} 时出错: {type(e).__name__}: {e}{Style.RESET_ALL}")
                continue

        # 批量扫描结束后，统一输出汇总文件
        from doc4llm.scanner import OutputHandler
        output_handler = OutputHandler(url_config)
        if all_results:
            output_handler.generate_report(all_results, batch_summary_file)
        if all_external_results:
            output_handler.append_results(all_external_results, batch_summary_file)
        if all_danger_results:
            output_handler.append_results(all_danger_results, batch_summary_file)
        if all_results or all_external_results or all_danger_results:
            print(f"{Fore.GREEN}所有扫描结果（含外链/危险接口）已汇总到: {batch_summary_file}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}未收集到任何扫描结果，未生成汇总文件。{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}处理URL文件时出错: {type(e).__name__}: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    finally:
        # 恢复原始的stdout和stderr
        if output_logger:
            sys.stdout = output_logger.original_stdout
            sys.stderr = output_logger.original_stderr
            # 关闭日志文件
            output_logger.close()
            print(f"{Fore.GREEN}输出日志已保存到: {output_logger.log_file}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}扫描结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
