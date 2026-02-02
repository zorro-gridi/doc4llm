"""
配置管理模块
负责扫描器的配置初始化和管理
"""
import logging
import urllib.parse
from .utils import DebugMixin, Fore

try:
    import tldextract
    DOMAIN_EXTRACTION = True
except ImportError:
    DOMAIN_EXTRACTION = False


class ScannerConfig(DebugMixin):
    """扫描器配置类"""

    def __init__(self, start_url, proxy=None, delay=0, max_workers=10, timeout=20,
                 max_depth=1, blacklist_domains=None, whitelist_domains=None, headers=None, output_file=None,
                 sensitive_patterns=None, color_output=True, verbose=True,
                 extension_blacklist=None, max_urls=5000, smart_concatenation=True,
                 debug_mode=False, url_scope_mode=0, danger_filter_enabled=1,
                 danger_api_list=None, allowed_api_list=None, is_duplicate=0,
                 custom_base_url=None, path_route=None, api_route=None,
                 fuzz=0,  # fuzz 参数
                 # URL过滤参数
                 exclude_fuzzy=None,
                 # 标题过滤参数
                 title_filter_list=None,
                 title_cleanup_patterns=None,
                 # 状态码过滤参数
                 status_code_filter=None,
                 # 文档爬取模式参数
                 mode=0, force_scan=0, doc_dir=None, doc_name=None, doc_version=None,
                 toc_url_filters=None, doc_max_depth=10, doc_timeout=30,
                 doc_toc_selector=None,
                 # TOC 过滤配置
                 toc_filter=None,
                 # 输出文件路径参数
                 results_dir=None, output_log_file=None, debug_log_file=None,
                 # 日志文件行数限制
                 log_max_lines=None,
                 # 内容过滤器配置
                 content_filter=None,
                 # 内联提取配置
                 enable_inline_extraction=1,
                 # 图片URL列表配置
                 extract_image_list=None):
        # 基础配置
        self.start_url = start_url
        self.proxy = self._init_proxy(proxy)
        self.delay = delay
        self.max_workers = max_workers
        self.timeout = timeout
        self.max_depth = max_depth
        self.output_file = output_file
        self.color_output = color_output
        self.verbose = verbose
        self.max_urls = max_urls
        self.smart_concatenation = smart_concatenation
        self.debug_mode = debug_mode

        # 输出文件路径配置
        self.results_dir = results_dir or 'results'
        self.output_log_file = output_log_file or 'results/output.out'
        self.debug_log_file = debug_log_file or 'results/debug.log'

        # 日志文件行数限制配置（默认10000行）
        self.log_max_lines = int(log_max_lines) if log_max_lines is not None else 10000

        # 域名和URL配置
        self.url_scope_mode = int(url_scope_mode)
        self.blacklist_domains = set(blacklist_domains or [])
        self.whitelist_domains = set(whitelist_domains or [])
        self.base_domain = self._init_base_domain(start_url)

        # 自定义URL拼接配置
        self.danger_filter_enabled = int(danger_filter_enabled)
        self.danger_api_list = danger_api_list
        self.allowed_api_list = allowed_api_list or []
        self.is_duplicate = int(is_duplicate)
        self.fuzz = int(fuzz)
        self.custom_base_url, self.path_route, self.api_route = self._init_fuzz_config(
            fuzz, custom_base_url, path_route, api_route)

        # URL过滤配置
        self.exclude_fuzzy = exclude_fuzzy or []

        # 标题过滤配置
        self.title_filter_list = title_filter_list or ['Page Not Found']
        self.title_cleanup_patterns = title_cleanup_patterns or []

        # 状态码过滤配置
        self.status_code_filter = status_code_filter or [404, 503, 502, 504, 403, 401, 500]

        # 文档爬取模式配置
        # mode: 0=仅爬取.csv url文件, 1=继续抓取文档内容, 2=继续抓取doc url(锚点链接)
        # force_scan: 在mode 1/2时，是否强制启动URL扫描器（默认0：如果CSV不为空则跳过扫描，1：强制扫描）
        self.mode = int(mode)
        self.force_scan = int(force_scan or 0)
        self.doc_dir = doc_dir or md_docs
        self.doc_name = doc_name
        self.doc_version = doc_version or 'latest'
        self.toc_url_filters = toc_url_filters or {}
        self.doc_max_depth = int(doc_max_depth)
        self.doc_timeout = int(doc_timeout) if doc_timeout else 30
        # doc_toc_selector: CSS选择器，指定TOC容器区域，如 '.toc', '#navigation', '.sidebar-nav, .table-of-contents'
        self.doc_toc_selector = doc_toc_selector

        # TOC 过滤配置（用于 DocUrlCrawler）
        self.toc_filter = toc_filter or {}

        # 内容过滤器配置（用于 DocContentCrawler）
        self.content_filter = content_filter or {}

        # 内联提取配置
        # 0=关闭（使用传统爬虫流程），1=开启（在扫描过程中实时提取内容/TOC）
        self.enable_inline_extraction = int(enable_inline_extraction)

        # 图片URL列表配置
        # None=启用并提取所有图片，False=禁用，list=只提取匹配的URL
        self.extract_image_list = extract_image_list

        # 扩展名过滤配置
        self.extension_blacklist = self._init_extension_blacklist(extension_blacklist)

        # 请求头配置
        self.headers = self._init_headers(headers)

        # 敏感信息检测配置
        self.sensitive_patterns = sensitive_patterns or self.default_sensitive_patterns()

        # 调试配置
        self._init_debug_logging()

        if self.debug_mode:
            self._debug_print(f"配置初始化完成: 起始URL: {start_url} 基础域名: {self.base_domain} 代理: {proxy} 最大深度: {max_depth} 最大URL数: {max_urls} 线程数: {max_workers} 调试: {debug_mode}")

    def _init_proxy(self, proxy):
        """初始化代理配置"""
        return {'http': proxy, 'https': proxy} if proxy else None

    def _init_base_domain(self, start_url):
        """初始化基础域名"""
        if start_url and DOMAIN_EXTRACTION:
            ext = tldextract.extract(start_url)
            return f"{ext.domain}.{ext.suffix}"
        elif start_url:
            parsed = urllib.parse.urlparse(start_url)
            return parsed.netloc
        else:
            return None

    def _init_fuzz_config(self, fuzz, custom_base_url, path_route, api_route):
        """初始化fuzz配置"""
        if int(fuzz) == 1:
            return custom_base_url, path_route, api_route
        else:
            return [], [], []

    def _init_extension_blacklist(self, extension_blacklist):
        """初始化扩展名黑名单"""
        # 如果没有配置，则默认过滤下面的类型
        return set(extension_blacklist or [
            '.css', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.woff', '.woff2',
            '.ttf', '.eot', '.ico', '.mp4', '.mp3', '.avi', '.mov', '.pdf',
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar',
            '.gz', '.tar', '.7z', '.exe', '.dll', '.bin', '.swf', '.flv'
        ])

    def _init_headers(self, headers):
        """初始化请求头"""
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        if headers:
            default_headers.update(headers)
        return default_headers

    def _init_debug_logging(self):
        """初始化调试日志"""
        if self.debug_mode:
            # 确保日志目录存在
            import os
            os.makedirs(os.path.dirname(self.debug_log_file), exist_ok=True)
            logging.basicConfig(
                filename=self.debug_log_file,
                filemode='a',
                format='%(asctime)s %(levelname)s %(message)s',
                level=logging.DEBUG,
                encoding='utf-8'
            )

    @staticmethod
    def default_sensitive_patterns():
        """默认敏感信息检测模式"""
        return {
            # 国内敏感信息
            '身份证号': r'\b[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b',
            '手机号': r'\b1(?:3\d|4[5-9]|5[0-35-9]|6[5-7]|7[0-8]|8\d|9[189])\d{8}\b',
            '统一社会信用代码': r'\b[0-9A-Z]{18}\b',
            '企业注册号': r'\b\d{13,15}\b',
            '内网IP': r'\b(127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b',
            'IP地址': r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
            'MAC地址': r'\b([a-fA-F0-9]{2}[:-]){5}[a-fA-F0-9]{2}\b',

            # 邮箱和认证
            '邮箱': r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?!js|css|jpg|jpeg|png|ico|svg|gif|woff|ttf|eot|mp4|mp3|json|map|zip|rar|exe|dll|bin|swf|flv)[a-zA-Z]{2,10}\b',
            'Basic认证': r'\b(?:basic|bearer)\s+[a-zA-Z0-9=:_\+/-]{5,100}\b',
            'Authorization': r'(?i)(basic [a-z0-9=:_\+/-]{5,100}|bearer [a-z0-9_.=:_\+/-]{5,100})',

            # 云服务密钥
            '阿里云密钥': r'\bLTAI[a-zA-Z0-9]{12,20}\b',
            '腾讯云密钥': r'\bAKID[a-zA-Z0-9]{16,28}\b',
            '百度云密钥': r'\bAK[a-zA-Z0-9]{32}\b',
            'AWS访问密钥': r'\bA[SK]IA[0-9A-Z]{16}\b',
            'AWS密钥ID': r'(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}',
            'Google API密钥': r'\bAIza[0-9A-Za-z\-_]{35}\b',
            'Firebase密钥': r'\bAAAA[A-Za-z0-9_-]{7}:[A-Za-z0-9_-]{140}\b',
            'Google验证码': r'\b6L[0-9A-Za-z\-_]{38}\b',
            'Google OAuth': r'\bya29\.[0-9A-Za-z\-_]+\b',

            # 第三方服务密钥
            'Twilio API密钥': r'\bSK[0-9a-fA-F]{32}\b',
            'Twilio账户SID': r'\bAC[a-zA-Z0-9_\-]{32}\b',
            'Twilio应用SID': r'\bAP[a-zA-Z0-9_\-]{32}\b',
            'Stripe标准API': r'\bsk_live_[0-9a-zA-Z]{24}\b',
            'Stripe限制API': r'\brk_live_[0-9a-zA-Z]{24}\b',
            'GitHub访问令牌': r'[a-zA-Z0-9_-]*:[a-zA-Z0-9_\-]+@github\.com',
            'Slack令牌': r'\bxox[baprs]-[0-9a-zA-Z]{10,48}\b',
            'Slack Webhook': r'https://hooks\.slack\.com/services/T[a-zA-Z0-9_]{8}/B[a-zA-Z0-9_]{8}/[a-zA-Z0-9_]{24}',
            'Mailgun API密钥': r'\bkey-[0-9a-zA-Z]{32}\b',
            'Square访问令牌': r'\bsqOatp-[0-9A-Za-z\-_]{22}\b',
            'Square OAuth密钥': r'\bsq0csp-[0-9A-Za-z\-_]{43}\b',
            'PayPal Braintree令牌': r'\baccess_token\$production\$[0-9a-z]{16}\$[0-9a-f]{32}\b',
            'Facebook访问令牌': r'\bEAACEdEose0cBA[0-9A-Za-z]+\b',

            # 社交媒体密钥
            'Facebook客户端ID': r'(?i)(facebook|fb)(.{0,20})?[\'\"][0-9]{13,17}[\'\"]',
            'Facebook密钥': r'(?i)(facebook|fb)(.{0,20})?[\'\"][0-9a-f]{32}[\'\"]',
            'Twitter OAuth': r'[t|T][w|W][i|I][t|T][t|T][e|E][r|R].{0,30}[\'"\s][0-9a-zA-Z]{35,44}[\'"\s]',
            'Twitter密钥': r'(?i)twitter(.{0,20})?[\'\"][0-9a-z]{35,44}[\'\"]',
            'LinkedIn密钥': r'(?i)linkedin(.{0,20})?[\'\"][0-9a-z]{16}[\'\"]',
            'Github密钥': r'(?i)github(.{0,20})?[\'\"][0-9a-zA-Z]{35,40}[\'\"]',

            # 云存储和数据库
            '阿里云OSS': r'[\\w.]\.oss\.aliyuncs\.com',
            'AWS S3': r's3\.amazonaws\.com[/]+|[a-zA-Z0-9_-]*\.s3\.amazonaws\.com',
            'AWS S3 URL': r'[a-zA-Z0-9-\.\_]+\.s3\.amazonaws\.com|s3://[a-zA-Z0-9-\.\_]+|s3-[a-zA-Z0-9-\.\_\/]+|s3\.amazonaws\.com/[a-zA-Z0-9-\.\_]+|s3\.console\.aws\.amazon\.com/s3/buckets/[a-zA-Z0-9-\.\_]+',
            'Cloudinary认证': r'cloudinary://[0-9]{15}:[0-9A-Za-z]+@[a-z]+',
            '数据库连接': r'(?i)(mysql|postgresql|mongodb|redis|oracle|sqlserver)://[a-zA-Z0-9_]+:[^@]+@[a-zA-Z0-9.-]+:[0-9]+/[a-zA-Z0-9_]+',
            'JDBC连接': r'jdbc:[a-z:]+://[a-zA-Z0-9_\-\.:;=/@?&,]+',

            # 密钥和令牌
            'JWT令牌': r'\bey[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*\b',
            'RSA私钥': r'-----BEGIN RSA PRIVATE KEY-----',
            'SSH私钥': r'-----BEGIN [^\s]+ PRIVATE KEY-----',
            'PGP私钥': r'-----BEGIN PGP PRIVATE KEY BLOCK-----',
            'SSH私钥块': r'([-]+BEGIN [^\s]+ PRIVATE KEY[-]+[\s]*[^-]*[-]+END [^\s]+ PRIVATE KEY[-]+)',

            # 通用敏感字段
            'API密钥': r'(?i)(api[_-]?key|access[_-]?key|secret[_-]?key)\s*[:=]\s*[\'\"][a-zA-Z0-9_\-]{10,}[\'\"]',
            '密码': r'(?i)(password|passwd|pwd|pass|passcode|userpass)\s*[:=]\s*[\'\"][^\'\"]{6,}[\'\"]',
            '密钥字段': r'(?i)(key|secret|token|config|auth|access|admin|ticket)\s*[:=]\s*[\'\"][^\'\"]{6,}[\'\"]',
            'OSS云存储桶': r'([A|a]ccess[K|k]ey[I|i]d|[A|a]ccess[K|k]ey[S|s]ecret|[Aa]ccess-[Kk]ey)|[A|a]ccess[K|k]ey',
            'Secret Key': r'[Ss](ecret|ECRET)_?[Kk](ey|EY)',

            # 文件路径
            'Windows路径': r'(?:[a-zA-Z]:\\\\(?:[^<>:"|?*\r\n]+\\\\)*[^<>:"|?*\r\n]*)',

            # 通用密钥模式
            'Secrets': r'(access_key|Access-Key|access_token|SecretKey|SecretId|admin_pass|admin_user|algolia_admin_key|algolia_api_key|alias_pass|alicloud_access_key|amazon_secret_access_key|amazonaws|ansible_vault_password|aos_key|api_key|api_key_secret|api_key_sid|api_secret|api\.googlemaps|AIza|apidocs|apikey|apiSecret|app_debug|app_id|app_key|app_log_level|app_secret|appkey|appkeysecret|application_key|appsecret|appspot|auth_token|authorizationToken|authsecret|aws_access|aws_access_key_id|aws_bucket|aws_key|aws_secret|aws_secret_key|aws_token|AWSSecretKey|b2_app_key|bashrc|password|bintray_apikey|bintray_gpg_password|bintray_key|bintraykey|bluemix_api_key|bluemix_pass|browserstack_access_key|bucket_password|bucketeer_aws_access_key_id|bucketeer_aws_secret_access_key|built_branch_deploy_key|bx_password|cache_driver|cache_s3_secret_key|cattle_access_key|cattle_secret_key|certificate_password|ci_deploy_password|client_secret|client_zpk_secret_key|clojars_password|cloud_api_key|cloud_watch_aws_access_key|cloudant_password|cloudflare_api_key|cloudflare_auth_key|cloudinary_api_secret|cloudinary_name|codecov_token|config|conn\.login|connectionstring|consumer_key|consumer_secret|credentials|cypress_record_key|database_password|database_schema_test|datadog_api_key|datadog_app_key|db_password|db_server|db_username|dbpasswd|dbpassword|dbuser|deploy_password|digitalocean_ssh_key_body|digitalocean_ssh_key_ids|docker_hub_password|docker_key|docker_pass|docker_passwd|docker_password|dockerhub_password|dockerhubpassword|dot|files|dotfiles|droplet_travis_password|dynamoaccesskeyid|dynamosecretaccesskey|elastica_host|elastica_port|elasticsearch_password|encryption_key|encryption_password|env\.heroku_api_key|env\.sonatype_password|eureka\.awssecretkey)[a-z0-9_.\-,]{0,25}[a-z0-9A-Z_ .\-,]{0,25}(=|>|:=|\||:|<=|=>|:).{0,5}[\'\"]([0-9a-zA-Z\-_=]{6,64})[\'\"]',
        }
