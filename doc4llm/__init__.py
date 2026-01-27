"""
doc4llm - Web URL扫描和信息安全收集工具

A comprehensive web security testing tool for URL scanning,
asset discovery, and reconnaissance.
"""
from .crawler import DocContentCrawler, DocUrlCrawler
from .extractor import WebContentExtractor
from .link_processor import LinkProcessor
from .scanner import (
    BloomFilter,
    DebugMixin,
    OutputHandler,
    OutputLogger,
    SensitiveDetector,
    ScannerConfig,
    URLConcatenator,
    URLMatcher,
    UltimateURLScanner,
    domain_matches,
    handle_exceptions,
    output_lock,
)
from .tool import MarkdownDocExtractor
from .llm import invoke, LLM_Config, AnthropicClient

__version__ = '2.0.0'
__all__ = [
    # Version
    '__version__',
    # Core Scanner
    'UltimateURLScanner',
    'ScannerConfig',
    'OutputLogger',
    'OutputHandler',
    # Utilities
    'URLMatcher',
    'URLConcatenator',
    'SensitiveDetector',
    'DebugMixin',
    'BloomFilter',
    'domain_matches',
    'handle_exceptions',
    'output_lock',
    # Crawlers
    'DocContentCrawler',
    'DocUrlCrawler',
    # Extractors & Processors
    'WebContentExtractor',
    'LinkProcessor',
    # Tool
    'MarkdownDocExtractor',
    # LLM
    'invoke',
    'LLM_Config',
    'AnthropicClient',
]
