import os
os.environ['HF_PROXY'] = 'http://127.0.0.1:7890'

from huggingface_hub import set_client_factory
import httpx

proxy = os.environ.get('HF_PROXY')
print(f'HF_PROXY: {proxy}')

def create_proxy_client() -> httpx.Client:
    return httpx.Client(proxy=proxy)

set_client_factory(create_proxy_client)
print('代理工厂函数设置成功')
print('通过 HuggingFace Hub 发出的所有请求将使用代理:', proxy)