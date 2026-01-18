#!/usr/bin/env python3
"""
doc4llm CLI Module
命令行接口模块

提供结构化的命令行接口，支持多种扫描模式：
- Mode 0: 仅爬取CSV URL文件
- Mode 1: 抓取文档内容
- Mode 2: 抓取锚点链接
- Mode 3: 依次执行内容爬取和锚点提取
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime
from urllib.parse import urlparse

from colorama import Fore, Style

from doc4llm.crawler import DocContentCrawler, DocUrlCrawler
from doc4llm.scanner import (
    OutputHandler,
    OutputLogger,
    ScannerConfig,
    URLMatcher,
    UltimateURLScanner,
)

# 禁用SSL警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CLIConfig:
    """CLI配置管理类"""

    DEFAULT_CONFIG = {
        "start_url": None,
        "proxy": None,
        "delay": 0.1,
        "max_workers": 30,
        "timeout": 20,
        "max_depth": 5,
        "blacklist_domains": ["www.w3.org", "www.baidu.com", "github.com"],
        "whitelist_domains": ["example.com", "test.com"],
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
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
        "danger_api_list": ["del", "delete", "insert", "logout", "loginout", "remove", "drop", "shutdown", "stop", "poweroff", "restart", "rewrite", "terminate", "deactivate", "halt", "disable"],
        "allowed_api_list": [],
        "custom_base_url": ["https://www.canopyu.com/"],
        "path_route": ["/api/v1/user/login"],
        "api_route": ["/api/v1/user/login"],
        "fuzz": 0,
        "exclude_fuzzy": ["/blog/", "/news/", "/community/", "/forum/"],
        "title_filter_list": ["Page Not Found"],
        "status_code_filter": [404, 503, 502, 504, 403, 401, 500],
        "mode": 0,
        "force_scan": 0,
        "results_dir": "results",
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
        "doc_toc_selector": None,
        "output_log_file": "results/output.out",
        "debug_log_file": "results/debug.log",
        "log_max_lines": 10000
    }

    @staticmethod
    def load(config_file='doc4llm/config/config.json'):
        """加载配置文件，如果不存在则返回默认配置"""
        if not os.path.exists(config_file):
            print(f"{Fore.YELLOW}=== 配置文件 {config_file} 不存在，使用默认配置 ==={Style.RESET_ALL}")
            return CLIConfig.DEFAULT_CONFIG.copy()
        return CLIConfig._read_config(config_file)

    @staticmethod
    def _read_config(config_file):
        """读取配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"{Fore.RED}读取配置文件时出错: {type(e).__name__}: {e}{Style.RESET_ALL}")
            sys.exit(1)


class ArgumentParser:
    """命令行参数解析器"""

    VERSION = "1.7.4"
    AUTHOR = "Zorro"
    GITHUB_URL = "https://github.com/zorro-gridi/doc4llm"

    @staticmethod
    def parse():
        """解析命令行参数"""
        parser = argparse.ArgumentParser(
            description="doc4llm 扫描工具",
            epilog="提示: 使用 -force-scan 而非 -force_scan（参数名用连字符）",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        # 基本参数
        parser.add_argument('-u', dest='start_url', type=str, help='起始URL')
        parser.add_argument('-f', dest='url_file', type=str, help='批量URL文件，每行一个URL')
        parser.add_argument('-config', dest='config_file', type=str, default='doc4llm/config/config.json', help='配置文件路径 (默认: doc4llm/config/config.json)')

        # 扫描参数
        parser.add_argument('-workers', dest='max_workers', type=int, help='最大线程数')
        parser.add_argument('-delay', dest='delay', type=float, help='请求延迟（秒）')
        parser.add_argument('-timeout', dest='timeout', type=int, help='请求超时（秒）')
        parser.add_argument('-depth', dest='max_depth', type=int, help='最大递归深度')
        parser.add_argument('-out', dest='output_file', type=str, help='实时输出文件')
        parser.add_argument('-proxy', dest='proxy', type=str, help='代理设置')
        parser.add_argument('-debug', dest='debug_mode', type=int, help='调试模式 1开启 0关闭')

        # 扫描范围和过滤
        parser.add_argument('-scope', dest='url_scope_mode', type=int, help='URL扫描范围模式 0主域 1外部一次 2全放开 3白名单模式')
        parser.add_argument('-danger', dest='danger_filter_enabled', type=int, default=1, help='危险接口过滤 1开启 0关闭 (默认: 1)')
        parser.add_argument('-fuzz', dest='fuzz', type=int, default=0, help='是否启用自定义URL拼接参数 1启用 0关闭 (默认: 0)')

        # 文档爬取模式参数
        parser.add_argument('-mode', dest='mode', type=int, default=0, help='爬取模式 0=仅爬取CSV 1=抓取文档内容 2=抓取锚点链接 3=依次执行内容爬取和锚点提取 (默认: 0)')
        parser.add_argument('-force-scan', dest='force_scan', type=int, default=0, help='强制启动URL扫描器 (mode 1/2/3时有效，1=强制扫描刷新CSV，0=CSV不为空则跳过扫描) (默认: 0)')
        parser.add_argument('-doc-dir', dest='doc_dir', type=str, help='文档输出目录路径')
        parser.add_argument('-doc-name', dest='doc_name', type=str, help='文档名称（覆盖自动检测）')
        parser.add_argument('-doc-version', dest='doc_version', type=str, help='文档版本号 (默认: latest)')
        parser.add_argument('-doc-depth', dest='doc_max_depth', type=int, help='文档爬取最大深度 (默认: 10)')
        parser.add_argument('-doc-toc-selector', dest='doc_toc_selector', type=str, help='TOC区域CSS选择器 (如: .toc, #navigation)')

        return parser.parse_args()

    @staticmethod
    def print_program_info():
        """打印程序信息"""
        print(f"{Fore.YELLOW}=============================================={Style.RESET_ALL}")
        print(f"{Fore.YELLOW}=== doc4llm v{ArgumentParser.VERSION} ===")
        print(f"{Fore.YELLOW}=== BY: {ArgumentParser.AUTHOR}  GitHub: {ArgumentParser.GITHUB_URL}")
        print(f"{Fore.YELLOW}=== 重复的URL不会重复扫描, 结果返回相同的URL不会重复展示")
        print(f"{Fore.CYAN}=== 所有输出将同时记录到 results/output.out 文件中")
        print(f"{Fore.CYAN}=== 扫描开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    @staticmethod
    def print_usage_examples():
        """打印常用参数示例"""
        examples = [
            ("基本URL扫描", "python cli.py -u https://example.com"),
            ("文档爬取模式", "python cli.py -u https://example.com -mode 3 -force-scan 1"),
            ("批量URL扫描", "python cli.py -f urls.txt -workers 20"),
            ("使用配置文件", "python cli.py -config custom_config.json"),
        ]
        print(f"\n{Fore.CYAN}=== 常用命令示例 ==={Style.RESET_ALL}")
        for desc, cmd in examples:
            print(f"{Fore.YELLOW}{desc}:{Style.RESET_ALL} {cmd}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")


class ArgumentValidator:
    """参数验证器"""

    @staticmethod
    def validate(args, config_data):
        """验证命令行参数

        验证逻辑：
        - mode 0 或 force_scan=1：需要指定扫描目标（-u 或 -f）
        - mode 1/2/3 且 force_scan=0：
          - 如果 CSV 文件存在且有内容：不需要 -u 或 -f
          - 如果 CSV 文件不存在或为空：需要 -u 或 -f
        """
        # 修复：使用正确的优先级：命令行参数 > 配置文件
        args_mode = getattr(args, 'mode', None)
        args_force_scan = getattr(args, 'force_scan', None)
        mode = args_mode if args_mode is not None else config_data.get('mode', 0)
        force_scan = args_force_scan if args_force_scan is not None else config_data.get('force_scan', 0)
        output_file = config_data.get('output_file', 'results/实时输出文件.csv')

        needs_scan_target = True

        if mode in [1, 2, 3] and force_scan == 0:
            if os.path.exists(output_file):
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        if len(f.readlines()) > 1:
                            needs_scan_target = False
                except Exception:
                    pass

        if needs_scan_target and not args.start_url and not args.url_file:
            print(f"{Fore.RED}错误：必须通过 -u 或 -f 至少指定一个扫描目标！{Style.RESET_ALL}")
            if mode in [1, 2, 3] and force_scan == 0:
                print(f"{Fore.YELLOW}提示：mode {mode} 且不使用 -force-scan 时，如果CSV文件已存在且有内容，可以不指定 -u 或 -f{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}提示：使用 -u <URL> 或 -f <文件> 指定扫描目标{Style.RESET_ALL}")
            ArgumentParser.print_usage_examples()
            sys.exit(1)


class ConfigBuilder:
    """配置构建器"""

    @staticmethod
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

    @staticmethod
    def build(args, config_data):
        """构建ScannerConfig对象"""
        def get_value(key, default=None):
            return getattr(args, key, None) if getattr(args, key, None) is not None else config_data.get(key, default)

        print(f"{Fore.CYAN}=== 正在初始化扫描器...{Style.RESET_ALL}")

        # 加载 headers 文件
        headers_path = config_data.get('headers_path')
        headers = ConfigBuilder._load_headers(headers_path) if headers_path else get_value('headers')

        return ScannerConfig(
            start_url=get_value('start_url'),
            proxy=get_value('proxy'),
            delay=get_value('delay', 0.1),
            max_workers=get_value('max_workers', 30),
            timeout=get_value('timeout', 20),
            max_depth=get_value('max_depth', 5),
            blacklist_domains=get_value('blacklist_domains'),
            whitelist_domains=get_value('whitelist_domains'),
            headers=headers,
            output_file=get_value('output_file', 'results/实时输出文件.csv'),
            color_output=get_value('color_output', True),
            verbose=get_value('verbose', True),
            extension_blacklist=get_value('extension_blacklist', ['.css', '.mp4']),
            max_urls=get_value('max_urls', 10000),
            smart_concatenation=get_value('smart_concatenation', True),
            debug_mode=get_value('debug_mode', 0),
            url_scope_mode=get_value('url_scope_mode', 0),
            danger_filter_enabled=get_value('danger_filter_enabled', 1),
            danger_api_list=get_value('danger_api_list'),
            allowed_api_list=get_value('allowed_api_list'),
            is_duplicate=get_value('is_duplicate', 0),
            custom_base_url=get_value('custom_base_url', []),
            path_route=get_value('path_route', []),
            api_route=get_value('api_route', []),
            fuzz=get_value('fuzz', 0),
            exclude_fuzzy=get_value('exclude_fuzzy'),
            title_filter_list=get_value('title_filter_list'),
            title_cleanup_patterns=get_value('title_cleanup_patterns'),
            status_code_filter=get_value('status_code_filter'),
            mode=get_value('mode', 0),
            force_scan=get_value('force_scan', 0),
            results_dir=get_value('results_dir', 'results'),
            doc_dir=get_value('doc_dir'),
            doc_name=get_value('doc_name'),
            doc_version=get_value('doc_version', 'latest'),
            toc_url_filters=get_value('toc_url_filters'),
            doc_max_depth=get_value('doc_max_depth', 10),
            doc_timeout=get_value('doc_timeout', 30),
            doc_toc_selector=get_value('doc_toc_selector'),
            output_log_file=get_value('output_log_file', 'results/output.out'),
            debug_log_file=get_value('debug_log_file', 'results/debug.log'),
            log_max_lines=get_value('log_max_lines', 10000),
            toc_filter=get_value('toc_filter'),
            content_filter=get_value('content_filter', {})
        )

    @staticmethod
    def print_config(config):
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


class OutputManager:
    """输出管理器"""

    def __init__(self):
        self.output_logger = None
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def init(self, output_log_file='results/output.out', max_lines=None):
        """初始化输出日志记录器"""
        if self.output_logger:
            self.output_logger.close()
        self.output_logger = OutputLogger(output_log_file, max_lines=max_lines)
        sys.stdout = self.output_logger
        sys.stderr = self.output_logger

    def cleanup(self):
        """清理资源"""
        if self.output_logger:
            sys.stdout = self.output_logger.original_stdout
            sys.stderr = self.output_logger.original_stderr
            self.output_logger.close()
            print(f"{Fore.GREEN}输出日志已保存到: {self.output_logger.log_file}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}扫描结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")


class CSVHelper:
    """CSV文件辅助类"""

    @staticmethod
    def has_content(file_path):
        """检查CSV文件是否有内容（除了表头）"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return len(f.readlines()) > 1
        except Exception:
            return False

    @staticmethod
    def get_first_url(file_path):
        """从CSV文件中读取第一个URL"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                first_row = next(reader, None)
                if first_row and 'URL' in first_row:
                    return first_row['URL']
        except Exception as e:
            print(f"{Fore.RED}错误：无法从CSV文件读取起始URL: {e}{Style.RESET_ALL}")
            sys.exit(1)
        return None

    @staticmethod
    def auto_detect_doc_name(url):
        """从URL自动检测文档名称"""
        parsed = urlparse(url)
        return parsed.netloc.replace('.', '_')


class ScannerRunner:
    """扫描执行器"""

    @staticmethod
    def scan_single(config, start_url):
        """扫描单个URL"""
        print(f"{Fore.YELLOW}开始扫描: {start_url}{Style.RESET_ALL}")
        scanner = UltimateURLScanner(config)
        scanner.start_scanning()

    @staticmethod
    def scan_multiple(config, url_file, get_config_value):
        """扫描多个URL"""
        try:
            if not os.path.exists(url_file):
                print(f"{Fore.RED}错误：URL文件 {url_file} 不存在！{Style.RESET_ALL}")
                sys.exit(1)

            with open(url_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]

            print(f"{Fore.YELLOW}从文件读取到 {len(urls)} 个URL，开始批量扫描...{Style.RESET_ALL}")

            if not urls:
                print(f"{Fore.YELLOW}URL文件为空，未执行扫描。{Style.RESET_ALL}")
                return

            all_results = []
            all_external_results = []
            all_danger_results = []
            results_dir = get_config_value('results_dir', 'results')
            batch_summary_file = f"{results_dir}/all_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            url_config = None  # 初始化变量

            for i, url in enumerate(urls, 1):
                try:
                    print(f"{Fore.CYAN}[{i}/{len(urls)}] 开始扫描: {url}{Style.RESET_ALL}")
                    url_config = ConfigBuilder.build(
                        type('Args', (), {'start_url': url}).__dict__,
                        {k: get_config_value(k) for k in ['start_url'] if False}  # 使用原始配置
                    )
                    # 复制配置但修改start_url
                    url_config.start_url = url
                    for attr in ['proxy', 'delay', 'max_workers', 'timeout', 'max_depth',
                                'blacklist_domains', 'whitelist_domains', 'headers', 'output_file',
                                'color_output', 'verbose', 'extension_blacklist', 'max_urls',
                                'smart_concatenation', 'debug_mode', 'url_scope_mode',
                                'danger_filter_enabled', 'danger_api_list', 'allowed_api_list',
                                'is_duplicate', 'custom_base_url', 'path_route', 'api_route',
                                'fuzz', 'exclude_fuzzy', 'title_filter_list', 'title_cleanup_patterns', 'status_code_filter',
                                'mode', 'force_scan', 'results_dir', 'doc_dir', 'doc_name',
                                'doc_version', 'toc_url_filters', 'doc_max_depth', 'doc_timeout',
                                'output_log_file', 'debug_log_file', 'log_max_lines', 'toc_filter',
                                'content_filter']:
                        setattr(url_config, attr, getattr(config, attr, None))

                    scanner = UltimateURLScanner(url_config)
                    scanner.start_scanning()

                    if hasattr(scanner, 'results'):
                        all_results.extend(scanner.results)
                    if hasattr(scanner, 'external_results'):
                        all_external_results.extend(scanner.external_results)

                    # 收集危险接口
                    if hasattr(scanner, 'config'):
                        for danger_url in URLMatcher.danger_api_filtered:
                            danger_types = [api for api in scanner.config.danger_api_list if api in danger_url and not danger_url.endswith(".js")]
                            if danger_types:
                                all_danger_results.append({
                                    'url': danger_url,
                                    'status': '危险',
                                    'title': '危险接口',
                                    'length': 0,
                                    'redirects': '',
                                    'depth': 0,
                                    'time': 0,
                                    'sensitive': ", ".join(danger_types),
                                    'sensitive_raw': [{'type': ", ".join(danger_types), 'count': 1, 'samples': [danger_url]}],
                                    'is_duplicate_signature': False,
                                    'content_type': '',
                                    'headers_count': 0,
                                    'error_type': None,
                                    'original_url': url,
                                })
                except Exception as e:
                    print(f"{Fore.RED}扫描URL {url} 时出错: {type(e).__name__}: {e}{Style.RESET_ALL}")
                    continue

            # 输出汇总文件
            if all_results or all_external_results or all_danger_results:
                output_handler = OutputHandler(url_config)
                if all_results:
                    output_handler.generate_report(all_results, batch_summary_file)
                if all_external_results:
                    output_handler.append_results(all_external_results, batch_summary_file)
                if all_danger_results:
                    output_handler.append_results(all_danger_results, batch_summary_file)
                print(f"{Fore.GREEN}所有扫描结果（含外链/危险接口）已汇总到: {batch_summary_file}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}未收集到任何扫描结果，未生成汇总文件。{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}处理URL文件时出错: {type(e).__name__}: {e}{Style.RESET_ALL}")
            sys.exit(1)


class ModeExecutor:
    """模式执行器 - 处理不同的爬取模式"""

    def __init__(self, args, config, output_manager):
        self.args = args
        self.config = config
        self.output_manager = output_manager

    def execute_mode_0(self):
        """Mode 0: 仅爬取CSV URL文件"""
        if self.args.start_url:
            ScannerRunner.scan_single(self.config, self.args.start_url)
        elif self.args.url_file:
            ScannerRunner.scan_multiple(self.config, self.args.url_file, lambda k: getattr(self.args, k, None))

    def execute_mode_1(self):
        """Mode 1: 抓取文档内容"""
        self._print_doc_mode_info("文档爬取模式已启用")
        csv_exists = CSVHelper.has_content(self.config.output_file)

        if csv_exists and self.config.force_scan == 0:
            print(f"{Fore.YELLOW}=== 检测到CSV文件已存在且有内容，跳过URL扫描 ==={Style.RESET_ALL}")
            print(f"{Fore.YELLOW}=== 使用 -force-scan 1 可强制刷新CSV文件 ==={Style.RESET_ALL}")
        else:
            self._execute_url_scan()
            csv_exists = True

        if not self.config.start_url and csv_exists:
            self.config.start_url = CSVHelper.get_first_url(self.config.output_file)
            print(f"{Fore.CYAN}=== 从CSV文件读取起始URL: {self.config.start_url} ==={Style.RESET_ALL}")

        print(f"{Fore.CYAN}=== 第二步：从CSV文件爬取文档内容 ==={Style.RESET_ALL}")
        doc_crawler = DocContentCrawler(self.config)
        doc_crawler.process_documentation_site(self.config.start_url)

    def execute_mode_2(self):
        """Mode 2: 抓取锚点链接"""
        self._print_doc_mode_info("锚点链接爬取模式已启用")
        csv_exists = CSVHelper.has_content(self.config.output_file)

        if csv_exists and self.config.force_scan == 0:
            print(f"{Fore.YELLOW}=== 检测到CSV文件已存在且有内容，跳过URL扫描 ==={Style.RESET_ALL}")
            print(f"{Fore.YELLOW}=== 使用 -force-scan 1 可强制刷新CSV文件 ==={Style.RESET_ALL}")
        else:
            self._execute_url_scan()
            csv_exists = True

        if not self.config.start_url and csv_exists:
            self.config.start_url = CSVHelper.get_first_url(self.config.output_file)
            print(f"{Fore.CYAN}=== 从CSV文件读取起始URL: {self.config.start_url} ==={Style.RESET_ALL}")

        if not self.config.doc_name and self.config.start_url:
            self.config.doc_name = CSVHelper.auto_detect_doc_name(self.config.start_url)
            print(f"{Fore.CYAN}=== 从起始URL自动设置文档名称: {self.config.doc_name} ==={Style.RESET_ALL}")

        print(f"{Fore.CYAN}=== 第二步：从CSV文件提取锚点链接 ==={Style.RESET_ALL}")
        anchor_crawler = DocUrlCrawler(self.config)
        anchor_crawler.process(csv_file=self.config.output_file)

    def execute_mode_3(self):
        """Mode 3: 依次执行内容爬取和锚点提取"""
        self._print_doc_mode_info("组合模式已启用：依次执行文档内容爬取和锚点链接提取")
        csv_exists = CSVHelper.has_content(self.config.output_file)

        if csv_exists and self.config.force_scan == 0:
            print(f"{Fore.YELLOW}=== 检测到CSV文件已存在且有内容，跳过URL扫描 ==={Style.RESET_ALL}")
            print(f"{Fore.YELLOW}=== 使用 -force-scan 1 可强制刷新CSV文件 ==={Style.RESET_ALL}")
        else:
            self._execute_url_scan()
            csv_exists = True

        if not self.config.start_url and csv_exists:
            self.config.start_url = CSVHelper.get_first_url(self.config.output_file)
            print(f"{Fore.CYAN}=== 从CSV文件读取起始URL: {self.config.start_url} ==={Style.RESET_ALL}")

        if not self.config.doc_name and self.config.start_url:
            self.config.doc_name = CSVHelper.auto_detect_doc_name(self.config.start_url)
            print(f"{Fore.CYAN}=== 从起始URL自动设置文档名称: {self.config.doc_name} ==={Style.RESET_ALL}")

        print(f"{Fore.CYAN}=== 第二步：从CSV文件爬取文档内容 ==={Style.RESET_ALL}")
        doc_crawler = DocContentCrawler(self.config)
        doc_crawler.process_documentation_site(self.config.start_url)

        print(f"{Fore.CYAN}=== 第三步：从CSV文件提取锚点链接 ==={Style.RESET_ALL}")
        anchor_crawler = DocUrlCrawler(self.config)
        anchor_crawler.process(csv_file=self.config.output_file)

    def _print_doc_mode_info(self, mode_name):
        """打印文档模式信息"""
        doc_name_display = self.config.doc_name or "auto-detected"
        print(f"{Fore.GREEN}=== {mode_name} ==={Style.RESET_ALL}")
        print(f"{Fore.CYAN}=== 文档输出目录: {self.config.doc_dir}/{doc_name_display}:{self.config.doc_version}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}=== 文档版本: {self.config.doc_version}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}=== 最大爬取深度: {self.config.doc_max_depth}{Style.RESET_ALL}")

    def _execute_url_scan(self):
        """执行URL扫描"""
        print(f"{Fore.CYAN}=== 第一步：执行URL扫描 ==={Style.RESET_ALL}")
        if not self.args.start_url and not self.args.url_file:
            print(f"{Fore.RED}错误：CSV文件不存在或为空，需要指定 -u 或 -f 进行URL扫描{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}提示：使用 -force-scan 1 可强制刷新CSV文件{Style.RESET_ALL}")
            sys.exit(1)
        if self.args.start_url:
            ScannerRunner.scan_single(self.config, self.args.start_url)
        elif self.args.url_file:
            ScannerRunner.scan_multiple(self.config, self.args.url_file, lambda k: getattr(self.args, k, None))


class CLI:
    """命令行接口主类"""

    def __init__(self):
        self.output_manager = OutputManager()

    def run(self):
        """运行CLI"""
        try:
            # 初始化临时输出日志
            self.output_manager.init()

            # 打印程序信息
            ArgumentParser.print_program_info()

            # 解析命令行参数
            args = ArgumentParser.parse()

            # 加载配置
            config_data = CLIConfig.load(args.config_file)

            # 验证参数
            ArgumentValidator.validate(args, config_data)

            # 重新初始化输出日志
            output_log_file = config_data.get('output_log_file', 'results/output.out')
            log_max_lines = config_data.get('log_max_lines', 10000)
            self.output_manager.init(output_log_file, max_lines=log_max_lines)

            # 创建配置对象
            config = ConfigBuilder.build(args, config_data)

            # 打印配置信息
            ConfigBuilder.print_config(config)

            # 执行对应模式
            executor = ModeExecutor(args, config, self.output_manager)
            mode_handlers = {
                0: executor.execute_mode_0,
                1: executor.execute_mode_1,
                2: executor.execute_mode_2,
                3: executor.execute_mode_3,
            }
            handler = mode_handlers.get(config.mode, executor.execute_mode_0)
            handler()

        except SystemExit:
            raise
        except Exception as e:
            print(f"{Fore.RED}程序运行出错: {type(e).__name__}: {e}{Style.RESET_ALL}")
            sys.exit(1)
        finally:
            self.output_manager.cleanup()


def main():
    """主入口函数"""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
