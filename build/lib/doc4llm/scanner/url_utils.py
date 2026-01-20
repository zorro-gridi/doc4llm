"""
URL拼接工具模块
提供智能URL拼接功能
"""
import os
import re
import urllib.parse
from .utils import DebugMixin


class URLConcatenator(DebugMixin):
    """URL智能拼接类"""

    def __init__(self, debug_mode=False, base_url=None, relative_url=None, custom_base_url=None, path_route=None, api_route=None):
        self.debug_mode = debug_mode
        # 支持字符串或列表，统一转为列表
        self.base_url = base_url if isinstance(base_url, list) else [base_url] if base_url else []
        self.relative_url = relative_url if isinstance(relative_url, list) else [relative_url] if relative_url else []
        self.custom_base_url = custom_base_url if isinstance(custom_base_url, list) else [custom_base_url] if custom_base_url else []
        self.path_route = path_route if isinstance(path_route, list) else [path_route] if path_route else []
        self.api_route = api_route if isinstance(api_route, list) else [api_route] if api_route else []
        self.url_list = set()

        if self.debug_mode:
            self._debug_print(f"[URLConcatenator]初始化URLConcatenator: base_url={self.base_url}, relative_url={self.relative_url}, custom_base_url={self.custom_base_url}, path_route={self.path_route}, api_route={self.api_route}")

    def smart_concatenation(self):
        """智能URL拼接"""
        results = set()
        for base_url in self.base_url:
            for relative_url in self.relative_url:
                if self.debug_mode:
                    self._debug_print(f"[smart_concatenation]开始拼接URL: base={base_url}, relative={relative_url}")

                # 根据不同类型的URL进行处理
                result = self._process_url_type(base_url, relative_url)
                if result:
                    results.add(result)
        return list(results)

    def _process_url_type(self, base_url, relative_url):
        """根据URL类型进行处理"""
        # 处理协议相对URL (//example.com/path)
        if relative_url.startswith('//'):
            base = urllib.parse.urlparse(base_url)
            return f"{base.scheme}:{relative_url}"

        # 处理hash路由（SPA应用）
        if relative_url.startswith('#/'):
            base = urllib.parse.urlparse(base_url)
            return f"{base.scheme}://{base.netloc}{base.path}{relative_url}"

        # 处理绝对路径
        if relative_url.startswith('/'):
            base = urllib.parse.urlparse(base_url)
            clean_path = relative_url.lstrip('/')
            return f"{base.scheme}://{base.netloc}/{clean_path}"

        # 处理相对路径
        if relative_url.startswith('./'):
            base = urllib.parse.urlparse(base_url)
            base_path = os.path.dirname(base.path) if not base.path.endswith('/') else base.path
            clean_relative = relative_url[2:].lstrip('/')
            return f"{base.scheme}://{base.netloc}{base_path}/{clean_relative}"

        # 处理上级目录
        if relative_url.startswith('../'):
            return self._process_parent_directory_url(base_url, relative_url)

        # 处理完整URL
        if relative_url.startswith(('http://', 'https://')):
            return relative_url

        # 默认拼接 - 使用urljoin但清理双斜杠
        joined = urllib.parse.urljoin(base_url, relative_url)
        parsed = urllib.parse.urlparse(joined)
        clean_path = re.sub(r'/{2,}', '/', parsed.path)
        return urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc,
            clean_path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

    def _process_parent_directory_url(self, base_url, relative_url):
        """
        处理上级目录URL

        Args:
            base_url: 基础URL，如 http://example.com/admin/login.aspx
            relative_url: 相对URL，如 ../scripts/jquery/jquery-1.11.2.min.js

        Returns:
            拼接后的完整URL
        """
        # 解析基础URL
        base = urllib.parse.urlparse(base_url)

        # 获取基础URL的目录路径（去掉文件名）
        base_path = base.path
        if not base_path.endswith('/'):
            # 如果不是以/结尾，说明是文件，需要获取其目录
            path_parts = base_path.split('/')
            if len(path_parts) > 1:
                base_path = '/'.join(path_parts[:-1])
            else:
                base_path = ''

        # 确保路径以/开头
        if base_path and not base_path.startswith('/'):
            base_path = '/' + base_path

        # 将基础路径分割成部分
        base_parts = [part for part in base_path.split('/') if part]

        # 处理相对URL中的../和./
        rel_parts = relative_url.split('/')
        back_count = 0
        new_parts = []

        for part in rel_parts:
            if part == '..':
                back_count += 1
            elif part == '.' or part == '':
                # 忽略当前目录和空字符串
                pass
            else:
                new_parts.append(part)

        # 计算新的基础路径（回退指定级数）
        if back_count > 0:
            if len(base_parts) >= back_count:
                # 回退指定级数
                remaining_parts = base_parts[:-back_count]
                new_base_path = '/' + '/'.join(remaining_parts) if remaining_parts else '/'
            else:
                # 如果回退次数超过路径深度，则回到根目录
                new_base_path = '/'
        else:
            # 没有回退，保持原路径
            new_base_path = '/' + '/'.join(base_parts) if base_parts else '/'

        # 添加新的路径部分
        if new_parts:
            if new_base_path.endswith('/'):
                final_path = new_base_path + '/'.join(new_parts)
            else:
                final_path = new_base_path + '/' + '/'.join(new_parts)
        else:
            final_path = new_base_path

        # 清理双斜杠
        final_path = re.sub(r'/{2,}', '/', final_path)

        # 构建完整URL
        return f"{base.scheme}://{base.netloc}{final_path}"

    def api_concatenation(self):
        """API路由拼接"""
        results = set()
        for base in self.custom_base_url:
            for route in self.api_route:
                for rel in self.relative_url:
                    if rel.startswith(('http://', 'https://')):
                        results.add(rel)
                        continue
                    base_clean = base.rstrip('/')
                    route_clean = route.strip('/')
                    rel_clean = rel.lstrip('/')
                    if route_clean:
                        result = f"{base_clean}/{route_clean}/{rel_clean}"
                    else:
                        result = f"{base_clean}/{rel_clean}"
                    if self.debug_mode:
                        self._debug_print(f"[api_concatenation]API拼接结果: {result}")
                    results.add(result)
        return list(results)

    def path_concatenation(self):
        """路径路由拼接"""
        results = set()
        for base in self.custom_base_url:
            for route in self.path_route:
                for rel in self.relative_url:
                    if rel.startswith(('http://', 'https://')):
                        results.add(rel)
                        continue
                    base_clean = base.rstrip('/')
                    route_clean = route.strip('/')
                    rel_clean = rel.lstrip('/')
                    if route_clean:
                        result = f"{base_clean}/{route_clean}/{rel_clean}"
                    else:
                        result = f"{base_clean}/{rel_clean}"
                    if self.debug_mode:
                        self._debug_print(f"[path_concatenation]路径拼接结果: {result}")
                    results.add(result)
        return list(results)

    def concatenate_urls(self):
        """拼接URL返回列表"""
        if self.debug_mode:
            self._debug_print(f"[concatenate_urls]开始拼接: base={self.base_url}, relative_url={self.relative_url} , custom_base_url={self.custom_base_url} , api_route={self.api_route} , path_route={self.path_route}")

        results = set()
        # 智能拼接
        if self.relative_url and self.base_url:
            results.update(self.smart_concatenation())
        # API拼接
        if self.api_route and self.custom_base_url:
            results.update(self.api_concatenation())
        # 路径拼接
        if self.path_route and self.custom_base_url:
            results.update(self.path_concatenation())
        if self.debug_mode:
            self._debug_print(f"[concatenate_urls]批量拼接完成，成功拼接 {len(results)} 个URL")
        return list(results)

    def url_check(self, url):
        """简单检查URL格式是否符合规范"""
        try:
            # 基本格式检查
            if not url or not isinstance(url, str):
                self._debug_print(f"URL格式不符合规范: {url} (空值或非字符串)")
                return False

            # 去除首尾空格
            url = url.strip()
            if not url:
                self._debug_print(f"URL格式不符合规范: {url} (空字符串)")
                return False

            # 检查URL解析
            parsed = urllib.parse.urlparse(url)

            # 检查协议
            if not parsed.scheme:
                self._debug_print(f"URL格式不符合规范: {url} (缺少协议)")
                return False

            # 检查协议是否有效
            valid_schemes = ['http', 'https', 'ftp', 'sftp', 'ws', 'wss']
            if parsed.scheme.lower() not in valid_schemes:
                self._debug_print(f"URL格式不符合规范: {url} (协议无效: {parsed.scheme})")
                return False

            # 检查域名
            if not parsed.netloc:
                self._debug_print(f"URL格式不符合规范: {url} (缺少域名)")
                return False

            # 检查域名格式
            domain_parts = parsed.netloc.split('.')
            if len(domain_parts) < 2:
                self._debug_print(f"URL格式不符合规范: {url} (域名格式无效: {parsed.netloc})")
                return False

            # 检查顶级域名
            tld = domain_parts[-1]
            if len(tld) < 2:
                self._debug_print(f"URL格式不符合规范: {url} (顶级域名无效: {tld})")
                return False

            # 检查端口号（如果存在）
            if ':' in parsed.netloc:
                host_port = parsed.netloc.split(':')
                if len(host_port) == 2:
                    try:
                        port = int(host_port[1])
                        if port < 1 or port > 65535:
                            self._debug_print(f"URL格式不符合规范: {url} (端口号无效: {port})")
                            return False
                    except ValueError:
                        self._debug_print(f"URL格式不符合规范: {url} (端口号格式无效: {host_port[1]})")
                        return False

            # 检查URL总长度
            if len(url) > 2048:
                self._debug_print(f"URL格式不符合规范: {url} (URL过长: {len(url)}字符)")
                return False

            return True

        except Exception as e:
            self._debug_print(f"URL格式检查异常: {url} (错误: {e})")
            return False

    def process_and_return_urls(self):
        """处理URL列表并返回结果"""
        # 清空当前列表
        self.url_list = set()

        self._debug_print(f"[process_and_return_urls]开始处理URL列表: base={self.base_url}, path={self.relative_url}")

        # 拼接URL
        concatenated_urls = self.concatenate_urls()

        # 添加到内部列表
        for url in concatenated_urls:
            if self.url_check(url):
                self.url_list.add(url)

        self._debug_print(f"[process_and_return_urls]处理完成，返回 {len(self.url_list)} 个URL")

        return list(self.url_list)
