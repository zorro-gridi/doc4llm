#!/usr/bin/env python3
"""
doc4llm 命令行入口

使用方式:
    python -m doc4llm -u https://example.com
    python -m doc4llm -u https://example.com -mode 3 -force-scan 1
"""
from doc4llm.cli import main

if __name__ == "__main__":
    main()
