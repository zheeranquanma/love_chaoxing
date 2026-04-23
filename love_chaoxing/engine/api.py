import json
import re
import random
import time


from typing import List, Dict, Any, Optional

from engine.session import CXSession

class CXApi:
    def __init__(self, session: CXSession):
        self.s = session
        self.base_url = "https://mobilelearn.chaoxing.com"
    
    async def get_courses(self) -> List[Dict]:
        """获取课程列表"""
        await self.s.check_login()
        
        url = "https://mooc1-api.chaoxing.com/mycourse/backclazzdata"
        params = {'view': 'json', 'rss': '1'}
        
        try:
            resp = self.s.session.get(url, params=params, timeout=15)
            data = resp.json()
            
            if data.get('result') != 1:
                return []
            
            courses = []
            for channel in data.get('channelList', []):
                content = channel.get('content', {})
                if content.get('course', {}).get('data'):
                    course_data = content['course']['data'][0]
                    courses.append({
                        'courseId': str(course_data.get('id')),
                        'classId': str(content.get('id')),
                        'courseName': course_data.get('name', '未知课程'),
                        'className': content.get('name', ''),
                        'teacherName': course_data.get('teacherfactor', ''),
                        'img': course_data.get('imageurl', ''),
                        'isTeach': False
                    })
                else:
                    courses.append({
                        'courseId': str(content.get('id')),
                        'classId': str(content.get('clazz', [{}])[0].get('id', '')),
                        'courseName': content.get('name', '未知课程'),
                        'className': content.get('clazz', [{}])[0].get('name', ''),
                        'teacherName': content.get('teacherfactor', ''),
                        'img': content.get('imageurl', ''),
                        'isTeach': True
                    })
            
            courses.sort(key=lambda x: x['isTeach'])
            return courses
            
        except Exception as e:
            print(f"获取课程异常: {e}")
            return []
    
    async def get_activities(self, course_id: str, class_id: str) -> List[Dict]:
        """获取活动列表"""
        await self.s.check_login()
        
        url = f"{self.base_url}/v2/apis/active/student/activelist"
        params = {
            'fid': '0',
            'courseId': course_id,
            'classId': class_id,
            'showNotStartedActive': '0'
        }
        
        try:
            resp = self.s.session.get(url, params=params, timeout=15)
            data = resp.json()
            
            if data.get('result') != 1:
                print(f"获取活动失败，result={data.get('result')}, msg={data.get('msg')}")
                return []
            
            activities = []
            active_list = data.get('data', {}).get('activeList', [])
            
            for act in active_list:
                act_type = act.get('type', -1)
                if not (0 <= act_type <= 5):
                    continue
                
                is_expire = act.get('endTime', 0) < int(time.time() * 1000)
                
                activities.append({
                    'activeId': str(act.get('id')),
                    'nameOne': act.get('nameOne', '未知活动'),
                    'nameFour': act.get('nameFour', ''),
                    'type': act_type,
                    'startTime': act.get('startTime', ''),
                    'courseId': course_id,
                    'classId': class_id,
                    'img': act.get('logo', ''),
                    'isExpire': is_expire,
                    'otherId': act.get('otherId', ''),
                    'ifphoto': act.get('ifphoto', 0),
                    'status': act.get('status', 0)
                })
            
            return activities[:20]
            
        except Exception as e:
            print(f"获取活动失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def get_activity_info(self, active_id: str) -> Dict:
        """获取活动详情"""
        await self.s.check_login()
        
        url = f"{self.base_url}/v2/apis/active/getPPTActiveInfo"
        params = {'activeId': active_id}
        
        try:
            resp = self.s.session.get(url, params=params, timeout=10)
            return resp.json()
        except Exception as e:
            print(f"获取活动详情失败: {e}")
            return {}
    
    async def before_sign(self, active_id: str, course_id: str, class_id: str):
        """预签到"""
        await self.s.check_login()
        
        uid = await self._ensure_uid()
        url = f"{self.base_url}/newsign/preSign"
        params = {
            'activePrimaryId': active_id,
            'courseId': course_id,
            'classId': class_id,
            'uid': uid,
            'appType': '15',
            'general': '1',
            'sys': '1',
            'ls': '1',
            'tid': '',
            'ut': 's'
        }
        
        try:
            resp = self.s.session.get(url, params=params, timeout=10)
            return resp.text
        except Exception as e:
            print(f"预签到失败: {e}")
            return None
    
    async def default_sign(self, active_id: str, sign_type: int, **kwargs) -> Dict[str, Any]:
        """执行签到"""
        await self.s.check_login()
        
        await self.before_sign(active_id, kwargs.get('course_id', ''), kwargs.get('class_id', ''))
        
        user_info = await self.s.get_user_info()
        random_names = ['龙傲天', '聂云竹', '叶青雨', '唐舞麟', '江玉饵', '君莫邪']
        name = user_info.get('name') or random.choice(random_names)
        
        # 统一使用 GET 请求参数结构
        params = {
            'activeId': active_id,
            'objectId': kwargs.get('object_id', ''),
            'uid': await self._ensure_uid(),
            'clientip': '',
            'useragent': '',
            'longitude': '-1',
            'latitude': '-1',
            'address': '',
            'location': '',
            'signCode': '',
            'role': '',
            'enc': kwargs.get('enc', ''),
            'name': name,
            'appType': '15',
            'ifTiJiao': '1',
            'fid': '0',
            'validate': kwargs.get('validate', ''),
            'vpProbability': '0',
            'vpStrategy': ''
        }
        
        if sign_type == 0:
            params['objectId'] = kwargs.get('object_id', '')
        elif sign_type == 4:
            lon = kwargs.get('longitude', -1)
            lat = kwargs.get('latitude', -1)
            addr = kwargs.get('address', '')
            params['longitude'] = str(lon)[:10] if lon > 0 else '-1'
            params['latitude'] = str(lat)[:10] if lat > 0 else '-1'
            params['address'] = addr
            if lon > 0 and lat > 0:
                params['location'] = json.dumps({
                    'result': '1',
                    'latitude': str(lat)[:10],
                    'longitude': str(lon)[:10],
                    'address': addr,
                    'altitude': '0.0'
                }, ensure_ascii=False)
        elif sign_type in [3, 5]:
            params['signCode'] = kwargs.get('sign_code', '')
        elif sign_type == 2:
            # 构造 location 嵌套 JSON，外层坐标强制 -1
            addr = kwargs.get('address', '默认位置')
            lat = kwargs.get('latitude', -1)
            lon = kwargs.get('longitude', -1)
            lat_str = str(lat) if lat != -1 else '39.9042'
            lon_str = str(lon) if lon != -1 else '116.4074'
            
            params['location'] = json.dumps({
                'result': '1',
                'address': addr,
                'latitude': lat_str,
                'longitude': lon_str,
                'altitude': '0.0'
            }, ensure_ascii=False)
            params['longitude'] = '-1'
            params['latitude'] = '-1'
            params['signCode'] = ''
        
        url = f"{self.base_url}/pptSign/stuSignajax"
        
        try:
          
            resp = self.s.session.get(url, params=params, timeout=15)
            result_text = resp.text
            
            return {
                'success': 'success' in result_text or '成功' in result_text,
                'message': self._parse_result(result_text),
                'raw': result_text
            }
        except Exception as e:
            return {'success': False, 'message': f'请求异常: {str(e)}'}
    
    async def check_sign_code(self, active_id: str, sign_code: str) -> bool:
        """检查签到码"""
        url = f"{self.base_url}/widget/sign/pcStuSignController/checkSignCode"
        params = {'activeId': active_id, 'signCode': sign_code}
        
        try:
            resp = self.s.session.get(url, params=params, timeout=5)
            data = resp.json()
            return bool(data.get('status'))
        except:
            return False
    
    async def brute_force_sign_code(self, active_id: str, max_try: int = 10000) -> Dict:
        """暴力破解手势/签到码"""
        await self.s.check_login()
        
        common_codes = ['0000', '1111', '1234', '5678', '9999', 
                       '2580', '0852', '1470', '3690', '1230',
                       '000000', '111111', '123456', '654321']
        
        for code in common_codes:
            if await self.check_sign_code(active_id, code):
                return {'found': True, 'code': code, 'type': 'common'}
        
        for i in range(1000, min(max_try, 10000)):
            code = str(i).zfill(4)
            if await self.check_sign_code(active_id, code):
                return {'found': True, 'code': code, 'type': 'brute'}
            time.sleep(0.05)
        
        return {'found': False, 'code': None}
    
    async def get_teacher_location(self, active_id: str) -> Optional[Dict[str, Any]]:
        info = await self.get_activity_info(active_id)
        if not info or info.get('result') != 1:
            print(f"⚠️ 活动详情请求失败: {info.get('msg', '未知错误')}")
            return None

        data = info.get('data')
        if not isinstance(data, dict):
            return None

        loc_obj = None
        strategy_used = "无"

        loc_obj = self._extract_by_paths(data, [
            ['location'], ['activeDetail', 'location'], ['signInfo', 'location'],
            ['signConfig', 'location'], ['activityExt', 'location'], ['properties', 'location']
        ])
        if loc_obj:
            strategy_used = "①预设路径"

        if not loc_obj:
            for field in ['extraInfo', 'activeOtherParam', 'signRule', 'ext', 'extend', 'otherInfo']:
                val = data.get(field)
                if isinstance(val, str) and val.strip():
                    try:
                        parsed = json.loads(val)
                        loc_obj = self._extract_by_paths(parsed, [['location']]) or self._deep_search(parsed)
                        if loc_obj:
                            strategy_used = "②序列化解析"
                            break
                    except Exception:
                        continue

        if not loc_obj:
            flat = self._flatten_dict(data)
        
        # 过滤无效值
            def is_valid_coord_val(v):
                if v is None:
                    return False
                if isinstance(v, (int, float)) and v in (0, -1, 1):
                 return False
                if isinstance(v, str) and v.strip() in ('0', '-1', '1', '', 'None', 'null'):
                    return False
                return True
        
        # 找坐标时优先用有效值
            lon_candidates = [(k, v) for k, v in flat.items() if re.search(r'lon(gitude)?$', k, re.I) and is_valid_coord_val(v)]
            lat_candidates = [(k, v) for k, v in flat.items() if re.search(r'lat(itude)?$', k, re.I) and not re.search(r'alt|latency|latest', k, re.I) and is_valid_coord_val(v)]
        
            lon_v = lon_candidates[0][1] if lon_candidates else None
            lat_v = lat_candidates[0][1] if lat_candidates else None
        
            if lon_v or lat_v:
                # address 过滤数字状态码
                addr_candidates = [(k, v) for k, v in flat.items() 
                                   if re.search(r'addr|address|locName', k, re.I) 
                                   and isinstance(v, str) and len(v) > 1 and not v.isdigit()]
                addr_v = addr_candidates[0][1] if addr_candidates else '未知位置'
            
                rng_v = next((v for k, v in flat.items() if re.search(r'range|radius|distance|signRange', k, re.I)), 200)
            
                loc_obj = {
                    'longitude': lon_v, 
                    'latitude': lat_v if lat_v is not None else -1,
                    'address': addr_v,
                    'range': rng_v
                }
                strategy_used = "③展平模糊匹配(过滤无效值)"

        if not loc_obj:
            if data.get('longitude') or data.get('latitude'):
                loc_obj = {
                    'longitude': data.get('longitude'), 'latitude': data.get('latitude'),
                    'address': data.get('address') or data.get('locationName', '未知位置'),
                    'range': data.get('range') or data.get('signRange', 200)
                }
                strategy_used = "④根节点直取"

        if not loc_obj:
            return None

        print(f"✅ 成功提取位置 [策略:{strategy_used}] -> {loc_obj.get('address', '未知')}")
        return self._clean_loc(loc_obj)
    def _extract_by_paths(self, d: dict, paths: List[List[str]]) -> Optional[dict]:
        for path in paths:
            node = d
            for k in path:
                if isinstance(node, dict) and k in node:
                    node = node[k]
                else:
                    break
            else:
                if isinstance(node, dict) and ('longitude' in node or 'lng' in node or 'latitude' in node):
                    return node
        return None

    def _deep_search(self, obj: Any) -> Optional[dict]:
        if isinstance(obj, dict):
            if any(k in obj for k in ['longitude', 'latitude', 'lng', 'lat', 'address', 'range']):
                return obj
            for v in obj.values():
                res = self._deep_search(v)
                if res:
                    return res
        elif isinstance(obj, list):
            for i in obj:
                res = self._deep_search(i)
                if res:
                    return res
        return None

    def _flatten_dict(self, d: dict, parent: str = '', sep: str = '.') -> dict:
        items = []
        for k, v in d.items():
            nk = f"{parent}{sep}{k}" if parent else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, nk, sep).items())
            else:
                items.append((nk, v))
        return dict(items)

    def _clean_loc(self, obj: dict) -> Optional[dict]:
        print(f"🔍 清洗前原始数据: {obj}")
        try:
            lon_raw = (obj.get('longitude') or obj.get('lng') or 
                       obj.get('lon') or obj.get('Lng') or 0)
            lat_raw = (obj.get('latitude') or obj.get('lat') or 
                       obj.get('Latitude') or obj.get('Lat') or 0)
            addr_raw = (obj.get('address') or obj.get('addr') or 
                        obj.get('name') or obj.get('locationName') or 
                        obj.get('Address') or '')
            rng_raw = (obj.get('range') or obj.get('signRange') or 
                      obj.get('radius') or obj.get('distance') or 200)

            longitude = float(lon_raw) if lon_raw is not None else 0
            latitude = float(lat_raw) if lat_raw is not None else -1
            sign_range = float(rng_raw) if rng_raw is not None else 200

       
            if latitude == -1:
                print(f"ℹ️ 检测到范围签到模式（无精确坐标），范围: {sign_range}米")
                # 如果经度有效，返回一个特殊标记，让前端知道"只能参考，不能直接用"
                if longitude != 0 and 73.5 <= longitude <= 135.0:
                    return {
                        'longitude': longitude,
                        'latitude': -1,  # 标记为无效
                        'address': '',   # 无具体地址文字
                        'range': sign_range,
                        'mode': 'range_only',  # 范围签到模式
                        'hint': f'老师设置了{sign_range}米范围签到，未指定精确坐标'
                    }
                return None

            # address 如果是纯数字（如1），说明是状态码，不是地址文字
            address = str(addr_raw).strip()
            if address.isdigit() or address in ('0', '1', '-1', 'None', 'null', 'true', 'false'):
                address = '未知位置'

            if not (73.5 <= longitude <= 135.0 and 18.0 <= latitude <= 53.5):
                print(f"⚠️ 坐标可能为加密/偏移值: lon={longitude}, lat={latitude}")

            return {
                'longitude': longitude, 
                'latitude': latitude, 
                'address': address, 
                'range': sign_range,
                'mode': 'precise'
            }
        except Exception as e:
            print(f"❌ 坐标清洗失败: {e}, 原始数据: {obj}")
            return None

            # address 如果是纯数字（如1），说明是状态码，不是地址文字
            address = str(addr_raw).strip()
            if address.isdigit() or address in ('0', '1', '-1', 'None', 'null', 'true', 'false'):
                address = '未知位置'

            if not (73.5 <= longitude <= 135.0 and 18.0 <= latitude <= 53.5):
                print(f"⚠️ 坐标可能为加密/偏移值: lon={longitude}, lat={latitude}")

            return {
                'longitude': longitude, 
                'latitude': latitude, 
                'address': address, 
                'range': sign_range,
                'mode': 'precise'
            }
        except Exception as e:
            print(f"❌ 坐标清洗失败: {e}, 原始数据: {obj}")
            return None
    async def get_class_photos(self, active_id: str) -> List[str]:
        """获取同学照片"""
        url = f"{self.base_url}/newsign/stuSign"
        params = {'activePrimaryId': active_id}
        
        try:
            resp = self.s.session.get(url, params=params, timeout=10)
            import re
            object_ids = re.findall(r'"objectId":"([a-f0-9]{32})"', resp.text)
            return list(set(object_ids))
        except:
            return []
    
    async def generate_qr_sign_url(self, active_id: str, enc: str = '') -> str:
        """生成二维码代签链接"""
        uid = await self._ensure_uid()
        base = "https://mobilelearn.chaoxing.com/pptSign/stuSignajax"
        params = {
            'activeId': active_id,
            'uid': uid,
            'enc': enc or f"FAKE_{random.randint(100000, 999999)}"
        }
        return f"{base}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
    
    def _parse_result(self, result: str) -> str:
        if not result:
            return "未知错误"
        if result == 'success':
            return "签到成功"
        if 'success2' in result:
            return "签到成功，但是已迟到"
        if '您已签到过了' in result:
            return "您已签到过了"
        if '验证码' in result:
            return "需要滑块验证码"
        if '不在签到范围' in result:
            return "不在签到范围内"
        if '二维码' in result or 'enc' in result:
            return "二维码已失效或enc错误"
        if '签到码' in result or '错误' in result:
            return "签到码错误"
        return result
    
    async def _ensure_uid(self) -> str:
        if self.s.uid:
            return self.s.uid
        await self.s.check_login()
        return self.s.uid or "0"
    
    async def get_token(self) -> Optional[str]:
        """获取云盘token"""
        await self.s.check_login()
        url = "https://pan-yz.chaoxing.com/api/token/uservalid"
        try:
            resp = self.s.session.get(url, timeout=10)
            data = resp.json()
            return data.get('_token')
        except:
            return None
