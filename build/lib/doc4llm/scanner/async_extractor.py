"""
异步内容提取器模块 - 高性能架构

功能：
1. 使用生产者-消费者模式，将I/O线程和CPU处理线程解耦
2. 扫描线程只负责网络请求，将响应放入队列
3. 专门的CPU线程池处理内容提取和文件写入
4. 批量写入优化，减少锁竞争和I/O开销

性能优势：
- 扫描线程不会被CPU密集型任务阻塞
- CPU线程池可以独立扩展，充分利用多核
- 批量写入减少文件系统调用次数
- 队列缓冲平滑处理突发流量
"""

import os
import time
import threading
from typing import Dict, Optional, Tuple, List
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, unquote

try:
    from colorama import Fore, Style
    COLOR_SUPPORT = True
except ImportError:
    COLOR_SUPPORT = False
    Fore = Style = type('', (), {'__getattr__': lambda *args: ''})()

from bs4 import BeautifulSoup

from doc4llm.filter import ContentFilter, EnhancedContentFilter
from doc4llm.filter.config import FilterConfigLoader, TocFilterConfigLoader
from doc4llm.filter.config import (
    TOC_CLASS_PATTERNS,
    TOC_LINK_CLASS_PATTERNS,
    TOC_PARENT_CLASS_PATTERNS,
    CONTENT_AREA_PATTERNS,
    NON_TOC_LINK_PATTERNS
)
from doc4llm.convertor.MarkdownConverter import MarkdownConverter
from doc4llm.link_processor.LinkProcessor import LinkProcessor
from doc4llm.scanner.utils import BloomFilter, DebugMixin


class ExtractionTask:
    """提取任务数据结构"""

    __slots__ = ['url', 'title', 'html_content', 'mode', 'timestamp']

    def __init__(self, url: str, title: str, html_content: str, mode: int):
        self.url = url
        self.title = title
        self.html_content = html_content
        self.mode = mode
        self.timestamp = time.time()


class BatchWriter:
    """批量文件写入器 - 减少I/O和锁竞争"""

    def __init__(self, batch_size: int = 50, flush_interval: float = 5.0, debug_mode: bool = False):
        """
        Args:
            batch_size: 批量大小，达到此数量时触发写入
            flush_interval: 最大缓冲时间，超过此时间触发写入
            debug_mode: 调试模式
        """
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.debug_mode = debug_mode

        # 待写入内容缓冲区 {filepath: content}
        self.content_buffer = {}

        # 线程锁
        self.lock = threading.Lock()

        # 最后刷新时间
        self.last_flush_time = time.time()

    def add_content(self, filepath: str, content: str) -> bool:
        """
        添加内容到缓冲区

        Args:
            filepath: 文件路径
            content: 文件内容

        Returns:
            bool: 是否应该触发批量写入
        """
        with self.lock:
            self.content_buffer[filepath] = content
            buffer_size = len(self.content_buffer)
            current_time = time.time()
            elapsed = current_time - self.last_flush_time

            # 达到批量大小或超过时间间隔时触发写入
            should_flush = buffer_size >= self.batch_size or elapsed >= self.flush_interval

            if should_flush:
                self._flush_unlocked()
                self.last_flush_time = time.time()

            return should_flush

    def _flush_unlocked(self):
        """内部刷新方法（不加锁，调用前已获取锁）"""
        if not self.content_buffer:
            return

        if self.debug_mode:
            print(f"[BatchWriter] 批量写入 {len(self.content_buffer)} 个文件")

        for filepath, content in self.content_buffer.items():
            try:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                if self.debug_mode:
                    print(f"[BatchWriter] 写入失败: {filepath}, 错误: {e}")

        self.content_buffer.clear()

    def flush(self):
        """强制刷新所有缓冲内容"""
        with self.lock:
            self._flush_unlocked()
            self.last_flush_time = time.time()


class AsyncContentExtractor(DebugMixin):
    """
    异步内容提取器 - 生产者-消费者模式

    架构：
    - 生产者: 扫描线程调用 queue_task() 将任务放入队列
    - 消费者: CPU线程池从队列取任务并处理
    - 批量写入: 减少文件I/O和锁竞争
    """

    def __init__(self, config, cpu_workers: int = 4, batch_size: int = 50):
        """
        Args:
            config: ScannerConfig配置对象
            cpu_workers: CPU处理线程数量（建议为核心数的1-2倍）
            batch_size: 批量写入大小
        """
        super().__init__(debug_mode=config.debug_mode)

        self.config = config
        self.cpu_workers = cpu_workers
        self.batch_size = batch_size

        # 初始化过滤器
        self.content_filter = self._load_content_filter()

        # 加载 TOC 过滤器配置
        toc_filter_dict = {'toc_filter': config.toc_filter} if hasattr(config, 'toc_filter') else {}
        toc_filter_config = TocFilterConfigLoader.load_from_config(toc_filter_dict)

        self.TOC_CLASS_PATTERNS = toc_filter_config.get('toc_class_patterns', TOC_CLASS_PATTERNS)
        self.TOC_LINK_CLASS_PATTERNS = toc_filter_config.get('toc_link_class_patterns', TOC_LINK_CLASS_PATTERNS)
        self.TOC_PARENT_CLASS_PATTERNS = toc_filter_config.get('toc_parent_class_patterns', TOC_PARENT_CLASS_PATTERNS)
        self.CONTENT_AREA_PATTERNS = toc_filter_config.get('content_area_patterns', CONTENT_AREA_PATTERNS)
        self.NON_TOC_LINK_PATTERNS = toc_filter_config.get('non_toc_link_patterns', NON_TOC_LINK_PATTERNS)
        self.TOC_END_MARKERS = toc_filter_config.get('toc_end_markers', [])

        # 使用布隆过滤器去重
        self.bloom_filter = BloomFilter(expected_elements=10000, false_positive_rate=0.001)

        # Markdown转换器（线程安全，每个线程创建独立实例）
        self.markdown_converter_class = MarkdownConverter

        # 任务队列（有界队列，防止内存爆炸）
        self.task_queue = Queue(maxsize=500)

        # 批量写入器
        self.batch_writer = BatchWriter(batch_size=batch_size, debug_mode=config.debug_mode)

        # 统计信息
        self.stats = {
            'queued': 0,
            'processing': 0,
            'content_extracted': 0,
            'toc_extracted': 0,
            'content_failed': 0,
            'toc_failed': 0,
            'toc_no_anchors': 0,
            'total_processing_time': 0.0
        }

        # 线程锁
        self.stats_lock = threading.Lock()

        # 控制标志
        self.running = False
        self.executor = None

        # 输出目录结构
        self.doc_root_dir = self._build_doc_root_path()

        # 已爬取的URL集合（线程安全）
        self.crawled_urls = set()
        self.crawled_lock = threading.Lock()

    def _load_content_filter(self):
        """加载内容过滤器"""
        try:
            filter_config = FilterConfigLoader.load_from_config({'content_filter': self.config.content_filter})

            if filter_config and (filter_config.get('content_end_markers') or
                                 filter_config.get('documentation_preset')):
                content_filter = EnhancedContentFilter(
                    non_content_selectors=filter_config.get('non_content_selectors'),
                    fuzzy_keywords=filter_config.get('fuzzy_keywords'),
                    log_levels=filter_config.get('log_levels'),
                    meaningless_content=filter_config.get('meaningless_content'),
                    preset=filter_config.get('documentation_preset'),
                    auto_detect_framework=True,
                    merge_mode=filter_config.get('merge_mode', 'extend')
                )
                if filter_config.get('content_end_markers'):
                    content_filter.content_end_markers = filter_config['content_end_markers']
                if filter_config.get('content_preserve_selectors'):
                    content_filter.content_preserve_selectors = filter_config['content_preserve_selectors']
                if filter_config.get('code_container_selectors'):
                    content_filter.code_container_selectors = filter_config['code_container_selectors']

                return content_filter
            else:
                return ContentFilter()
        except Exception as e:
            if self.debug_mode:
                self._debug_print(f"无法加载内容过滤器配置 ({e})，使用标准内容过滤器")
            return ContentFilter()

    def _build_doc_root_path(self) -> str:
        """构建文档根目录路径"""
        doc_name = self.config.doc_name
        if not doc_name:
            if self.config.start_url:
                parsed = urlparse(self.config.start_url)
                doc_name = parsed.netloc.replace('.', '_')
            else:
                doc_name = 'documentation'

        dir_name = f"{doc_name}@{self.config.doc_version}"
        full_path = os.path.join(self.config.doc_dir, dir_name)
        os.makedirs(full_path, exist_ok=True)

        if self.debug_mode:
            self._debug_print(f"文档根目录: {full_path}")

        return full_path

    def start(self):
        """启动异步提取器"""
        if self.running:
            return

        self.running = True
        self.executor = ThreadPoolExecutor(max_workers=self.cpu_workers, thread_name_prefix="extractor")

        # 启动消费者线程
        for i in range(self.cpu_workers):
            self.executor.submit(self._consumer_loop, f"extractor-{i}")

        if self.debug_mode:
            self._debug_print(f"异步提取器已启动: {self.cpu_workers} 个CPU线程")

    def stop(self):
        """停止异步提取器"""
        if not self.running:
            return

        self.running = False

        # 等待队列处理完成
        if self.executor:
            # 提交空任务唤醒消费者
            for _ in range(self.cpu_workers):
                self.task_queue.put(None)

            self.executor.shutdown(wait=True)
            self.executor = None

        # 刷新剩余缓冲内容
        self.batch_writer.flush()

        if self.debug_mode:
            self._debug_print("异步提取器已停止")

    def queue_task(self, url: str, title: str, html_content: str, mode: int):
        """
        将提取任务加入队列（非阻塞）

        Args:
            url: 页面URL
            title: 页面标题
            html_content: HTML内容
            mode: 提取模式 (1=内容, 2=TOC, 3=两者)
        """
        # 检查是否已爬取
        with self.crawled_lock:
            if url in self.crawled_urls:
                return
            # 暂时不标记，等处理成功再标记

        # 标题过滤
        title = self._clean_title(title)
        if self._should_skip_title(title):
            if self.debug_mode:
                self._debug_print(f"因标题匹配过滤规则跳过提取: {url} (标题: {title})")
            return

        # 检查模式
        if mode not in [1, 2, 3]:
            return

        # 创建任务
        task = ExtractionTask(url, title, html_content, mode)

        # 非阻塞入队
        try:
            self.task_queue.put_nowait(task)

            with self.stats_lock:
                self.stats['queued'] += 1

            if self.debug_mode:
                self._debug_print(f"任务已入队: {url}, 队列大小: {self.task_queue.qsize()}")

        except Exception:
            # 队列满，丢弃任务（防止内存溢出）
            if self.debug_mode:
                self._debug_print(f"队列已满，丢弃任务: {url}")

    def _clean_title(self, title: str) -> str:
        """清理页面标题"""
        if not title:
            return title

        cleaned = title
        for pattern in self.config.title_cleanup_patterns:
            cleaned = cleaned.replace(pattern, '')

        return cleaned.strip()

    def _should_skip_title(self, title: str) -> bool:
        """检查页面标题是否匹配过滤规则"""
        if not title:
            return False
        for filter_title in self.config.title_filter_list:
            if title.lower() == filter_title.lower():
                return True
        return False

    def _consumer_loop(self, worker_name: str):
        """
        消费者线程循环

        Args:
            worker_name: 工作线程名称
        """
        if self.debug_mode:
            self._debug_print(f"[{worker_name}] 消费者线程启动")

        # 每个线程创建自己的MarkdownConverter实例（如果需要）
        markdown_converter = None

        while self.running:
            try:
                # 获取任务（带超时，避免永久阻塞）
                task = self.task_queue.get(timeout=5)

                # 空任务表示停止信号
                if task is None:
                    break

                # 处理任务
                start_time = time.time()

                with self.stats_lock:
                    self.stats['processing'] += 1

                try:
                    # mode 1 或 3: 提取内容
                    if task.mode in [1, 3]:
                        self._extract_content(task, markdown_converter)

                    # mode 2 或 3: 提取TOC
                    if task.mode in [2, 3]:
                        self._extract_toc(task)

                    # 标记为已爬取
                    with self.crawled_lock:
                        self.crawled_urls.add(task.url)

                except Exception as e:
                    if self.debug_mode:
                        self._debug_print(f"[{worker_name}] 处理任务失败: {task.url}, 错误: {e}")

                processing_time = time.time() - start_time

                with self.stats_lock:
                    self.stats['total_processing_time'] += processing_time

                self.task_queue.task_done()

            except Empty:
                # 超时，继续循环
                continue
            except Exception as e:
                if self.debug_mode:
                    self._debug_print(f"[{worker_name}] 消费者线程异常: {e}")
                continue

        if self.debug_mode:
            self._debug_print(f"[{worker_name}] 消费者线程结束")

    def _extract_content(self, task: ExtractionTask, markdown_converter):
        """提取文档内容"""
        try:
            soup = BeautifulSoup(task.html_content, 'html.parser')

            # 提取页面标题
            title = task.title
            if not title:
                title = self.content_filter.get_page_title(task.url, soup)
                title = self._clean_title(title)
            else:
                title = self._clean_title(title)

            # 转换相对链接
            link_processor = LinkProcessor(task.url)
            soup = link_processor.convert_relative_links(soup)

            # 过滤内容
            cleaned_soup = self.content_filter.filter_non_content_blocks(soup)
            cleaned_soup = self.content_filter.filter_logging_outputs(cleaned_soup)

            # 转换为Markdown
            if markdown_converter is None:
                markdown_converter = self.markdown_converter_class()
            markdown_content = markdown_converter.convert_to_markdown(str(cleaned_soup))

            # 后处理
            markdown_content = self.content_filter.filter_content_end_markers(markdown_content)
            markdown_content = self.content_filter.remove_meaningless_content(markdown_content)

            # 添加元数据
            header = f"# {title}\n\n"
            header += f"> **原文链接**: {task.url}\n\n"
            header += "---\n\n"
            final_content = header + markdown_content

            # 生成文件路径
            page_dir_name = self._sanitize_filename(title, is_directory=True)
            page_directory = os.path.join(self.doc_root_dir, page_dir_name)
            content_file = os.path.join(page_directory, 'docContent.md')

            # 批量写入
            self.batch_writer.add_content(content_file, final_content)

            with self.stats_lock:
                self.stats['content_extracted'] += 1

            if self.debug_mode:
                self._debug_print(f"✓ 内容提取成功: {title[:50]}...")

        except Exception as e:
            if self.debug_mode:
                self._debug_print(f"内容提取失败: {task.url}, 错误: {e}")
            with self.stats_lock:
                self.stats['content_failed'] += 1

    def _extract_toc(self, task: ExtractionTask):
        """提取TOC锚点链接"""
        try:
            soup = BeautifulSoup(task.html_content, 'html.parser')

            # 提取页面标题
            title = task.title
            if not title:
                title = self.content_filter.get_page_title(task.url, soup)
                title = self._clean_title(title)
            else:
                title = self._clean_title(title)

            # 提取锚点链接
            anchor_links = self._extract_anchor_links(soup, task.url)

            if not anchor_links:
                with self.stats_lock:
                    self.stats['toc_no_anchors'] += 1
                return

            # 过滤和编号
            filtered_anchor_links = self._filter_toc_end_markers(anchor_links)
            anchor_links_with_numbers = self._add_hierarchy_numbers(filtered_anchor_links)

            # 生成内容
            content = f"# {title}\n\n"
            content += f"原文链接: {task.url}\n\n"
            content += f"提取的锚点数量: {len(filtered_anchor_links)}\n\n"

            for link in anchor_links_with_numbers:
                level = link.get('level', 4)
                link_url = link.get('url', '')
                hierarchy_number = link.get('hierarchy_number', '')
                display_name = link.get('text', link.get('name', ''))

                if level == 1:
                    content += f"## {hierarchy_number}. {display_name}：{link_url}\n\n"
                elif level == 2:
                    content += f"### {hierarchy_number}. {display_name}：{link_url}\n\n"
                elif level == 3:
                    content += f"#### {hierarchy_number}. {display_name}：{link_url}\n\n"
                else:
                    content += f"- {hierarchy_number}. {display_name}：{link_url}\n"

            # 生成文件路径
            page_dir_name = self._sanitize_filename(title, is_directory=True)
            page_directory = os.path.join(self.doc_root_dir, page_dir_name)
            toc_file = os.path.join(page_directory, 'docTOC.md')

            # 批量写入
            self.batch_writer.add_content(toc_file, content)

            with self.stats_lock:
                self.stats['toc_extracted'] += 1

            if self.debug_mode:
                self._debug_print(f"✓ TOC提取成功: {title[:40]}... ({len(filtered_anchor_links)} anchors)")

        except Exception as e:
            if self.debug_mode:
                self._debug_print(f"TOC提取失败: {task.url}, 错误: {e}")
            with self.stats_lock:
                self.stats['toc_failed'] += 1

    def _sanitize_filename(self, title: str, is_directory: bool = False) -> str:
        """清理文件名"""
        return self.content_filter.sanitize_filename(title, is_directory=is_directory)

    def _extract_anchor_links(self, soup, base_url: str) -> List[Dict]:
        """提取锚点链接"""
        anchor_links = []

        try:
            # 构建 id 到元素的映射
            id_to_element = {}
            for elem in soup.find_all(id=True):
                elem_id = elem['id']
                id_to_element[elem_id] = elem
                decoded_id = unquote(elem_id)
                if decoded_id != elem_id:
                    id_to_element[decoded_id] = elem

            # 根据配置决定搜索范围
            if self.config.doc_toc_selector:
                toc_containers = soup.select(self.config.doc_toc_selector)
                for container in toc_containers:
                    for a_tag in container.find_all('a', href=True):
                        self._process_anchor_tag(a_tag, base_url, id_to_element, soup, anchor_links)
            else:
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    if str(href).startswith('#'):
                        if not self._is_in_toc(a_tag):
                            continue
                        self._process_anchor_tag(a_tag, base_url, id_to_element, soup, anchor_links)

        except Exception as e:
            if self.debug_mode:
                self._debug_print(f"提取锚点链接时出错: {e}")

        return anchor_links

    def _is_in_toc(self, a_tag) -> bool:
        """判断锚点链接是否在目录（TOC）区域"""
        try:
            # 白名单检查
            direct_parent = a_tag.parent
            if direct_parent and direct_parent.has_attr('class'):
                parent_classes = ' '.join(direct_parent['class']).lower()
                for pattern in self.TOC_PARENT_CLASS_PATTERNS:
                    if pattern in parent_classes:
                        return True

            if a_tag.has_attr('class'):
                classes = ' '.join(a_tag['class']).lower()
                for pattern in self.TOC_LINK_CLASS_PATTERNS:
                    if pattern in classes:
                        return True

            parent = a_tag.parent
            depth = 0
            while parent and depth < 10:
                if parent.has_attr('id'):
                    elem_id = parent['id'].lower()
                    for pattern in self.TOC_CLASS_PATTERNS:
                        if pattern in elem_id:
                            return True
                if parent.has_attr('class'):
                    classes = ' '.join(parent['class']).lower()
                    for pattern in self.TOC_CLASS_PATTERNS:
                        if pattern in classes:
                            return True
                parent = parent.parent
                depth += 1

            return False

        except Exception as e:
            return False

    def _process_anchor_tag(self, a_tag, base_url: str, id_to_element: dict, soup: BeautifulSoup, anchor_links: List[Dict]):
        """处理单个锚点标签"""
        href = a_tag['href']
        if not str(href).startswith('#'):
            return

        anchor_name = str(href)[1:]
        anchor_text = a_tag.get_text(strip=True)
        full_url = f"{base_url}{href}"

        # 布隆过滤器去重
        if full_url in self.bloom_filter:
            return
        self.bloom_filter.add(full_url)

        decoded_anchor_name = unquote(anchor_name)
        level = self._determine_anchor_level(decoded_anchor_name, id_to_element, soup)
        if level == 4:
            level = self._determine_anchor_level(anchor_name, id_to_element, soup)

        decoded_text = unquote(anchor_text) if anchor_text else anchor_name

        anchor_links.append({
            'name': anchor_name,
            'text': decoded_text,
            'url': full_url,
            'level': level
        })

    def _determine_anchor_level(self, anchor_name: str, id_to_element: dict, soup: BeautifulSoup) -> int:
        """判断锚点的层级级别"""
        try:
            if anchor_name in id_to_element:
                element = id_to_element[anchor_name]
                tag_name = element.name

                if tag_name == 'section':
                    heading = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    if heading:
                        tag_name = heading.name

                if tag_name == 'h2':
                    return 1
                elif tag_name == 'h3':
                    return 2
                elif tag_name == 'h4':
                    return 3
                elif tag_name in ['h5', 'h6']:
                    return 4

            return 4

        except Exception as e:
            return 4

    def _filter_toc_end_markers(self, anchor_links: List[Dict]) -> List[Dict]:
        """使用统一后处理模板过滤 TOC 锚点链接"""
        from doc4llm.filter.base import filter_by_end_markers

        return filter_by_end_markers(
            anchor_links,
            self.TOC_END_MARKERS,
            text_extractor=lambda link: link.get('text', '').strip(),
            debug_mode=self.debug_mode
        )

    def _add_hierarchy_numbers(self, anchor_links: List[Dict]) -> List[Dict]:
        """为锚点链接添加层级编号"""
        counters = {1: 0, 2: 0, 3: 0, 4: 0}
        result = []

        for link in anchor_links:
            level = link.get('level', 4)

            for l in range(level + 1, 5):
                counters[l] = 0

            counters[level] += 1

            if level == 1:
                hierarchy_number = str(counters[1])
            elif level == 2:
                hierarchy_number = f"{counters[1]}.{counters[2]}"
            elif level == 3:
                hierarchy_number = f"{counters[1]}.{counters[2]}.{counters[3]}"
            else:
                hierarchy_number = f"{counters[1]}.{counters[2]}.{counters[3]}.{counters[4]}"

            link_with_number = link.copy()
            link_with_number['hierarchy_number'] = hierarchy_number
            result.append(link_with_number)

        return result

    def get_queue_size(self) -> int:
        """获取当前队列大小"""
        return self.task_queue.qsize()

    def print_statistics(self):
        """打印统计信息"""
        self.batch_writer.flush()

        if not COLOR_SUPPORT:
            print(f"\n{'='*60}")
            print(f"异步提取完成统计")
            print(f"{'='*60}")
            print(f"已入队任务: {self.stats['queued']}")
            print(f"已处理任务: {self.stats['processing']}")
            print(f"内容提取成功: {self.stats['content_extracted']}")
            print(f"内容提取失败: {self.stats['content_failed']}")
            print(f"TOC提取成功: {self.stats['toc_extracted']}")
            print(f"TOC提取失败: {self.stats['toc_failed']}")
            print(f"无锚点页面: {self.stats['toc_no_anchors']}")
            print(f"输出目录: {self.doc_root_dir}")

            if self.stats['processing'] > 0:
                avg_time = self.stats['total_processing_time'] / self.stats['processing']
                print(f"平均处理时间: {avg_time:.3f}秒/任务")

            print(f"{'='*60}\n")
        else:
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}异步提取完成统计{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}已入队任务: {self.stats['queued']}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}已处理任务: {self.stats['processing']}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}内容提取成功: {self.stats['content_extracted']}{Style.RESET_ALL}")
            print(f"{Fore.RED}内容提取失败: {self.stats['content_failed']}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}TOC提取成功: {self.stats['toc_extracted']}{Style.RESET_ALL}")
            print(f"{Fore.RED}TOC提取失败: {self.stats['toc_failed']}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}无锚点页面: {self.stats['toc_no_anchors']}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}输出目录: {self.doc_root_dir}{Style.RESET_ALL}")

            if self.stats['processing'] > 0:
                avg_time = self.stats['total_processing_time'] / self.stats['processing']
                print(f"{Fore.CYAN}平均处理时间: {avg_time:.3f}秒/任务{Style.RESET_ALL}")

            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
