#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import time
import random
import string
import os
import json

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 常量定义
BASE_URL = 'https://pan.baidu.com'
HEADERS = {
    'Host': 'pan.baidu.com',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Sec-Fetch-Site': 'same-site',
    'Sec-Fetch-Mode': 'navigate',
    'Referer': 'https://pan.baidu.com',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7,en-GB;q=0.6,ru;q=0.5',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
}
EXP_MAP = {"1天": 1, "7天": 7, "30天": 30, "永久": 0}
ERROR_CODES = {
    -1: '链接错误，链接失效或缺少提取码',
    -4: '转存失败，无效登录。请退出账号在其他地方的登录',
    -6: '转存失败，请用浏览器无痕模式获取 Cookie 后再试',
    -7: '转存失败，转存文件夹名有非法字符，不能包含 < > | * ? \\ :，请改正目录名后重试',
    -8: '转存失败，目录中已有同名文件或文件夹存在',
    -9: '链接错误，提取码错误',
    -10: '转存失败，容量不足',
    -12: '链接错误，提取码错误',
    -62: '转存失败，链接访问次数过多，请手动转存或稍后再试',
    0: '转存成功',
    2: '转存失败，目标目录不存在',
    4: '转存失败，目录中存在同名文件',
    12: '转存失败，转存文件数超过限制',
    20: '转存失败，容量不足',
    105: '链接错误，所访问的页面不存在',
    404: '转存失败，秒传无效',
}

# 预编译正则表达式
SHARE_ID_REGEX = re.compile(r'"shareid":(\d+?),"')
USER_ID_REGEX = re.compile(r'"share_uk":"(\d+?)","')
FS_ID_REGEX = re.compile(r'"fs_id":(\d+?),"')
SERVER_FILENAME_REGEX = re.compile(r'"server_filename":"(.+?)","')
ISDIR_REGEX = re.compile(r'"isdir":(\d+?),"')

# 缓存文件路径
CACHE_FILE = 'api_cache.json'
# 缓存过期时间（小时），优先从环境变量读取，默认24小时
def get_cache_expire_hours():
    val = os.getenv('CACHE_EXPIRE_HOURS', '24')
    return int(val) if val and val.strip() else 24

CACHE_EXPIRE_HOURS = get_cache_expire_hours()


class Network:
    def __init__(self):
        self.s = requests.Session()
        self.headers = HEADERS.copy()
        self.bdstoken = ''
        requests.packages.urllib3.disable_warnings()

    def get_bdstoken(self):
        url = f'{BASE_URL}/api/gettemplatevariable'
        params = {
            'clienttype': '0',
            'app_id': '38824127',
            'web': '1',
            'fields': '["bdstoken","token","uk","isdocuser","servertime"]'
        }

        r = self.s.get(url=url, params=params, headers=self.headers, timeout=10, allow_redirects=False, verify=False)
        if r.json()['errno'] != 0:
            return r.json()['errno']

        return r.json()['result']['bdstoken']

    def get_dir_list(self, folder_name):
        url = f'{BASE_URL}/api/list'
        params = {
            'order': 'time',
            'desc': '1',
            'showempty': '0',
            'web': '1',
            'page': '1',
            'num': '1000',
            'dir': folder_name,
            'bdstoken': self.bdstoken
        }

        r = self.s.get(url=url, params=params, headers=self.headers, timeout=15, allow_redirects=False, verify=False)
        if r.json()['errno'] != 0:
            return r.json()['errno']

        return r.json()['list']

    def create_dir(self, folder_name):
        url = f'{BASE_URL}/api/create'
        params = {
            'a': 'commit',
            'bdstoken': self.bdstoken
        }
        data = {
            'path': folder_name,
            'isdir': '1',
            'block_list': '[]',
        }

        r = self.s.post(url=url, params=params, headers=self.headers, data=data, timeout=15, allow_redirects=False, verify=False)
        return r.json()['errno']

    def verify_pass_code(self, link_url, pass_code):
        url = f'{BASE_URL}/share/verify'
        params = {
            'surl': link_url[25:48],
            'bdstoken': self.bdstoken,
            't': str(int(round(time.time() * 1000))),
            'channel': 'chunlei',
            'web': '1',
            'clienttype': '0'
        }
        data = {
            'pwd': pass_code,
            'vcode': '',
            'vcode_str': ''
        }

        r = self.s.post(url=url, params=params, headers=self.headers, data=data, timeout=10, allow_redirects=False, verify=False)
        if r.json()['errno'] != 0:
            return r.json()['errno']

        return r.json()['randsk']

    def get_transfer_params(self, url):
        r = self.s.get(url=url, headers=self.headers, timeout=15, verify=False)
        return r.content.decode("utf-8")

    def transfer_file(self, params_list, folder_name):
        url = f'{BASE_URL}/share/transfer'
        params = {
            'shareid': params_list[0],
            'from': params_list[1],
            'bdstoken': self.bdstoken,
            'channel': 'chunlei',
            'web': '1',
            'clienttype': '0'
        }
        data = {
            'fsidlist': f"[{','.join(params_list[2])}]",
            'path': f'/{folder_name}'
        }

        r = self.s.post(url=url, params=params, headers=self.headers, data=data, timeout=30, allow_redirects=False, verify=False)
        return r.json()['errno']

    def create_share(self, fs_id, expiry, password):
        url = f'{BASE_URL}/share/set'
        params = {
            'channel': 'chunlei',
            'bdstoken': self.bdstoken,
            'clienttype': '0',
            'app_id': '250528',
            'web': '1'
        }
        data = {
            'period': expiry,
            'pwd': password,
            'eflag_disable': 'true',
            'channel_list': '[]',
            'schannel': '4',
            'fid_list': f'[{fs_id}]'
        }

        r = self.s.post(url=url, params=params, headers=self.headers, data=data, timeout=15, allow_redirects=False, verify=False)
        if r.json()['errno'] != 0:
            return r.json()['errno']

        return r.json()['link']


# 工具函数
def normalize_link(url_code):
    normalized = url_code.replace("share/init?surl=", "s/1")
    normalized = re.sub(r'[?&]pwd=', ' ', normalized)
    normalized = re.sub(r'提取码*[：:]', ' ', normalized)
    normalized = re.sub(r'^.*?(https?://)', 'https://', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def parse_url_and_code(url_code):
    parts = url_code.strip().split(' ')
    url = parts[0]
    code = parts[1] if len(parts) > 1 else ''
    return url[:47], code[-4:] if code else ''


def parse_response(response):
    shareid_list = SHARE_ID_REGEX.findall(response)
    user_id_list = USER_ID_REGEX.findall(response)
    fs_id_list = FS_ID_REGEX.findall(response)
    server_filename_list = SERVER_FILENAME_REGEX.findall(response)
    isdir_list = ISDIR_REGEX.findall(response)
    if not all([shareid_list, user_id_list, fs_id_list, server_filename_list, isdir_list]):
        return -1

    return [shareid_list[0], user_id_list[0], fs_id_list, list(dict.fromkeys(server_filename_list)), isdir_list]


def update_cookie(bdclnd, cookie):
    cookies_dict = dict(map(lambda item: item.split('=', 1), filter(None, cookie.split(';'))))
    cookies_dict['BDCLND'] = bdclnd
    updated_cookie = ';'.join([f'{key}={value}' for key, value in cookies_dict.items()])
    return updated_cookie


def generate_code():
    characters = string.ascii_letters + string.digits
    code = ''.join(random.choice(characters) for _ in range(4))
    return code


def load_cache():
    """加载本地缓存数据"""
    if not os.path.exists(CACHE_FILE):
        return None
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        # 检查缓存是否过期
        cache_time = cache.get('cache_time', 0)
        current_time = time.time()
        if (current_time - cache_time) < (CACHE_EXPIRE_HOURS * 3600):
            print(f'使用本地缓存（缓存时间：{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cache_time))}）')
            return cache.get('data')
        else:
            print('本地缓存已过期')
            return None
    except Exception as e:
        print(f'读取缓存失败：{e}')
        return None


def save_cache(data):
    """保存数据到本地缓存"""
    try:
        cache = {
            'data': data,
            'cache_time': time.time()
        }
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=4)
        print('数据已保存到本地缓存')
    except Exception as e:
        print(f'保存缓存失败：{e}')


def fetch_and_transfer():
    """从API获取资源，转存并分享，推送到webhook"""
    # 从环境变量获取配置
    cookie = os.getenv('COOKIE', '')
    count = int(os.getenv('COUNT', 5))
    webhook_url = os.getenv('WEBHOOK_URL', '')
    target_folder = os.getenv('TARGET_FOLDER', '转存资源')
    
    if not cookie:
        print('错误：请在.env文件中设置COOKIE')
        return
    
    print(f'开始获取资源，计划转存 {count} 个...')
    
    # 优先从本地缓存读取
    cached_data = load_cache()

    if cached_data:
        # 使用缓存数据
        api_data = cached_data
        resources = api_data.get('merged_by_type', {}).get('baidu', [])
    else:
        # 从在线API获取
        print('本地缓存不存在或已过期，从在线API获取数据...')
        api_url = 'https://so.252035.xyz/api/search'
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://so.252035.xyz',
            'priority': 'u=1, i',
            'referer': 'https://so.252035.xyz/',
            'sec-ch-ua': '"Not?A_Brand";v="99", "Chromium";v="130"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 QuarkPC/6.7.7.829'
        }
        payload = json.dumps({
            "kw": "",
            "cloud_types": ["baidu"]
        })
        try:
            response = requests.post(api_url, headers=headers, data=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f'获取API数据失败：{e}')
            return

        # 检查API响应状态
        if data.get('code') != 0:
            print(f'API返回错误：{data.get("message")}')
            return

        # 解析数据：data.merged_by_type.baidu
        api_data = data.get('data', {})
        resources = api_data.get('merged_by_type', {}).get('baidu', [])

        # 保存到缓存（保存整个data对象）
        if resources:
            save_cache(api_data)
    
    if not resources:
        print('没有找到百度网盘资源')
        return
    
    # 随机打乱资源列表
    random.shuffle(resources)
    print('已随机打乱资源列表')
    
    # 限制转存数量
    resources = resources[:count]
    print(f'获取到 {len(resources)} 个资源')
    
    # 初始化网络对象
    network = Network()
    network.headers['Cookie'] = cookie
    
    # 获取 bdstoken
    bdstoken = network.get_bdstoken()
    if isinstance(bdstoken, int):
        print(f'获取bdstoken失败，错误代码：{bdstoken}')
        return
    network.bdstoken = bdstoken
    
    # 创建目标目录
    result = network.get_dir_list(f'/{target_folder}')
    if isinstance(result, int):
        return_code = network.create_dir(target_folder)
        if return_code != 0:
            print(f'创建目录失败，错误代码：{return_code}')
            return
    print(f'目标目录：{target_folder}')
    
    # 处理每个资源
    results = []
    for idx, resource in enumerate(resources, 1):
        url = resource.get('url', '')
        password = resource.get('password', '')
        note = resource.get('note', '')
        
        if not url or 'pan.baidu.com' not in url:
            print(f'跳过无效链接：{url}')
            continue
        
        print(f'正在处理第 {idx} 个资源: {note}')
        
        try:
            # 处理链接
            normalized_link = normalize_link(f'{url} {password}')
            parsed_url, code = parse_url_and_code(normalized_link)
            
            # 验证提取码
            if code:
                bdclnd = network.verify_pass_code(parsed_url, code)
                if isinstance(bdclnd, int):
                    print(f'验证提取码失败：{ERROR_CODES.get(bdclnd, f"错误代码({bdclnd})")}')
                    continue
                network.headers['Cookie'] = update_cookie(bdclnd, network.headers['Cookie'])
            
            # 获取转存参数
            response = network.get_transfer_params(parsed_url)
            result = parse_response(response)
            
            if not isinstance(result, list):
                print(f'解析链接失败：{ERROR_CODES.get(result, f"错误代码({result})")}')
                continue
            
            # 转存文件
            transfer_result = network.transfer_file(result, target_folder)
            if transfer_result != 0:
                print(f'转存失败：{ERROR_CODES.get(transfer_result, f"错误代码({transfer_result})")}')
                continue
            
            print('转存成功，正在创建分享链接...')
            
            # 获取转存后的文件信息并创建分享
            file_name = result[3][0] if result[3] else "未知文件"
            is_dir = result[4] == ["1"]
            
            # 获取目录列表，查找转存的文件
            dir_list = network.get_dir_list(f'/{target_folder}')
            if not isinstance(dir_list, list):
                print('获取目录列表失败')
                continue
            
            share_link = None
            for item in dir_list:
                if item['server_filename'] == file_name and item['isdir'] == (1 if is_dir else 0):
                    # 生成分享链接（永久，随机密码）
                    share_password = generate_code()
                    share_result = network.create_share(item['fs_id'], str(EXP_MAP['永久']), share_password)
                    if isinstance(share_result, str):
                        share_link = f'{share_result}?pwd={share_password}'
                    break
            
            if share_link:
                results.append({
                    'note': note,
                    'share_link': share_link
                })
                print(f'分享成功：{note} -> {share_link}')
            else:
                print(f'创建分享链接失败：{note}')
            
            # 随机延迟，避免请求过快
            time.sleep(random.uniform(1, 3))
            
        except Exception as e:
            print(f'处理资源失败 {note}：{e}')
    
    # 输出结果
    print('\n=== 转存分享结果 ===')
    for res in results:
        print(f"资源名: {res['note']}")
        print(f"分享链接: {res['share_link']}")
        print('---')
    
    # 推送到webhook
    if webhook_url and results:
        print(f'\n正在推送到webhook...')
        try:
            # 构建消息内容
            msg_lines = []
            for res in results:
                msg_lines.append(f"📁 {res['note']}")
                msg_lines.append(f"🔗 {res['share_link']}")
                msg_lines.append('')
            
            message = '\n'.join(msg_lines)
            
            webhook_data = {
                'msgtype': 'text',
                'text': {
                    'content': message
                }
            }
            
            response = requests.post(webhook_url, json=webhook_data, timeout=30)
            response.raise_for_status()
            print('推送成功！')
        except Exception as e:
            print(f'推送webhook失败：{e}')
    
    print(f'\n完成！成功处理 {len(results)} 个资源')
    return results


if __name__ == '__main__':
    fetch_and_transfer()
