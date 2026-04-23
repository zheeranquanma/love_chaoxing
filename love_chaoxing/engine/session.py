import os
import json
import time
import requests
from requests.utils import dict_from_cookiejar, add_dict_to_cookiejar
from typing import Optional, Dict, Any

class CXSession:
    def __init__(self, config_path: str = "config.json"):
        self.session = requests.Session()
        self.config_path = config_path
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.uid: Optional[str] = None
        self.cookie_update_time: int = 0
        self.user_info_cache: Dict[str, Any] = {}
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://passport2.chaoxing.com/login'
        })
        # 启动时立即恢复会话状态
        self._load_config()

    def _load_config(self):
        try:
            if not os.path.exists(self.config_path):
                return
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            self.username = config.get('username')
            self.password = config.get('password')
            self.uid = config.get('uid')
            self.cookie_update_time = config.get('cookie_update_time', 0)
            self.user_info_cache = config.get('user_info_cache', {})
            
            # 【核心修复】使用 requests 官方工具安全恢复 Cookie，自动补全域名匹配
            cookies_dict = config.get('cookies', {})
            if cookies_dict:
                add_dict_to_cookiejar(self.session.cookies, cookies_dict)
        except Exception as e:
            print(f"加载配置失败: {e}")

    def save_config(self):
        try:
            # 【核心修复】提取完整 Cookie 字典，保留路径/域名元数据
            cookies_dict = dict_from_cookiejar(self.session.cookies)
            config = {
                'cookies': cookies_dict,
                'username': self.username,
                'password': self.password,
                'uid': self.uid,
                'cookie_update_time': self.cookie_update_time,
                'user_info_cache': self.user_info_cache
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def _safe_get_cookie(self, name: str) -> Optional[str]:
        """安全提取Cookie，彻底规避 CookieConflictError"""
        for cookie in self.session.cookies:
            if cookie.name == name:
                return cookie.value
        return None

    async def check_login(self) -> bool:
        uid = self._safe_get_cookie('UID') or self._safe_get_cookie('_uid')

        if not uid:
            self._load_config()
            uid = self._safe_get_cookie('UID') or self._safe_get_cookie('_uid')

        if not uid:
            if self.username and self.password:
                print("未找到有效Cookie，尝试重新登录...")
                return await self.login(self.username, self.password)
            return False

        # 7天过期检查
        if self.cookie_update_time > 0:
            current_time_ms = int(time.time() * 1000)
            if current_time_ms > self.cookie_update_time + 7 * 24 * 60 * 60 * 1000:
                print("Cookie已过期，自动重新登录")
                if self.username and self.password:
                    return await self.login(self.username, self.password)

        self.uid = uid
        return True

    async def login(self, username: str, password: str) -> bool:
        self.username = username
        self.password = password
        url = "https://passport2.chaoxing.com/api/login"
        params = {
            'name': username,
            'pwd': password,
            'schoolid': '',
            'verify': '0'
        }
        try:
            resp = self.session.post(url, data=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get('result'):
                # 缓存登录返回的完整用户信息，避免额外请求
                self.user_info_cache = {
                    'name': data.get('realname') or data.get('uname', '未知'),
                    'uid': str(data.get('uid', '')),
                    'dept': '',
                    'school': '',
                    'phone': data.get('phone', ''),
                    'sex': ''
                }
                self.uid = self._safe_get_cookie('UID') or self._safe_get_cookie('_uid')
                self.cookie_update_time = int(time.time() * 1000)
                self.save_config()
                print("✅ 登录成功，状态已持久化")
                return True
            else:
                print(f"❌ 登录失败: {data.get('msg', '账号或密码错误')}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络请求异常: {e}")
            return False
        except Exception as e:
            print(f"❌ 登录处理异常: {e}")
            return False

    async def get_user_info(self) -> Dict[str, Any]:
        """直接返回缓存数据，零延迟、零报错"""
        if not self.user_info_cache:
            return {'name': '未知', 'uid': self.uid or '', 'dept': '', 'school': '', 'phone': '', 'sex': ''}
        return self.user_info_cache
