import os
import atexit
import sys
import time
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from engine.session import CXSession
from engine.api import CXApi

router = APIRouter()

session = CXSession()
api = CXApi(session)

ENC_FILE_PATH = "temp_enc.txt"

def _clean_enc_file():
    try:
        if os.path.exists(ENC_FILE_PATH):
            os.remove(ENC_FILE_PATH)
            print("✅ 进程退出，临时enc文件已自动删除")
    except Exception as e:
        print(f"⚠️ 清理文件失败: {e}")

atexit.register(_clean_enc_file)

class LoginRequest(BaseModel):
    username: str
    password: str

class CookieInjectRequest(BaseModel):
    cookies: str

class EncSaveRequest(BaseModel):
    enc: str

class SignRequest(BaseModel):
    activeId: str
    courseId: str = ""
    classId: str = ""
    signType: int
    signCode: Optional[str] = ""
    longitude: Optional[float] = -1
    latitude: Optional[float] = -1
    address: Optional[str] = ""
    enc: Optional[str] = ""
    objectId: Optional[str] = ""

class MultiSignRequest(BaseModel):
    activeId: str
    signType: int
    users: List[dict]

@router.get("/")
async def index():
    return FileResponse("web/static/index.html")

@router.post("/api/login")
async def login(req: LoginRequest):
    success = await session.login(req.username, req.password)
    if success:
        user_info = await session.get_user_info()
        return {"success": True, "msg": "登录成功", "userinfo": user_info}
    return {"success": False, "msg": "登录失败"}

@router.post("/api/inject")
async def inject_cookies(req: CookieInjectRequest):
    try:
        count = 0
        for item in req.cookies.split(';'):
            item = item.strip()
            if not item or '=' not in item:
                continue
            k, v = item.split('=', 1)
            k, v = k.strip(), v.strip().strip('"\'')
            if k and v:
                # 移除 domain 限制，避免 requests 产生同名多路径 Cookie 冲突
                session.session.cookies.set(k, v)
                count += 1
        
        # 安全提取 UID，彻底规避 CookieConflictError
        uid = None
        for cookie in session.session.cookies:
            if cookie.name in ('UID', '_uid'):
                uid = cookie.value
                break
                
        if uid:
            session.uid = uid
            session.cookie_update_time = int(time.time() * 1000)
            session.save_config()
            return {"success": True, "msg": f"成功注入 {count} 项 Cookie", "uid": uid}
        return {"success": False, "msg": "未检测到有效UID"}
    except Exception as e:
        return {"success": False, "msg": str(e)}

@router.get("/api/userinfo")
async def get_userinfo():
    # 核心修复：必须校验登录状态，未登录时返回失败，前端据此正确显示登录页
    is_login = await session.check_login()
    if not is_login:
        return {"success": False, "msg": "未登录或登录已失效"}
        
    info = await session.get_user_info()
    return {"success": True, "data": info}

@router.get("/api/saved-account")
async def get_saved_account():
    return {"success": True, "username": session.username or "", "password": session.password or ""}

@router.get("/api/courses")
async def get_courses():
    try:
        courses = await api.get_courses()
        return {"success": True, "data": courses}
    except Exception as e:
        return {"success": False, "msg": str(e), "data": []}

@router.get("/api/activities")
async def get_activities(courseId: str, classId: str):
    try:
        acts = await api.get_activities(courseId, classId)
        return {"success": True, "data": acts}
    except Exception as e:
        return {"success": False, "msg": str(e), "data": []}

@router.get("/api/activity-info")
async def get_activity_info(activeId: str):
    try:
        info = await api.get_activity_info(activeId)
        return {"success": True, "data": info}
    except Exception as e:
        return {"success": False, "msg": str(e)}

@router.get("/api/teacher-location")
async def get_teacher_location(activeId: str):
    try:
        loc = await api.get_teacher_location(activeId)
        if loc:
            return {"success": True, "data": loc}
        return {"success": False, "msg": "未获取到老师位置"}
    except Exception as e:
        return {"success": False, "msg": str(e)}

@router.get("/api/brute-force-code")
async def brute_force_code(activeId: str):
    try:
        result = await api.brute_force_sign_code(activeId)
        return {"success": result['found'], "data": result}
    except Exception as e:
        return {"success": False, "msg": str(e)}

@router.get("/api/class-photos")
async def get_class_photos(activeId: str):
    try:
        photos = await api.get_class_photos(activeId)
        return {"success": True, "data": photos}
    except Exception as e:
        return {"success": False, "msg": str(e)}

@router.post("/api/sign")
async def do_sign(req: SignRequest):
    try:
        # 默认使用前端传入的坐标/地址
        final_lon = req.longitude if req.longitude != -1 else -1
        final_lat = req.latitude if req.latitude != -1 else -1
        final_addr = req.address or ""

        # 🔑 位置签到自动补全逻辑（仅当 signType=4 且坐标为默认值时触发）
        if req.signType == 4 and (final_lon == -1 or final_lat == -1):
            loc = await api.get_teacher_location(req.activeId)
            if loc:
                import random
                # 在老师位置基础上 ±15米 随机偏移（防风控连签检测）
                final_lon = loc['longitude'] + random.uniform(-0.000135, 0.000135)
                final_lat = loc['latitude'] + random.uniform(-0.000135, 0.000135)
                final_addr = loc['address']
                print(f"✅ 自动获取老师位置: {final_addr} (已添加防风控偏移)")
            else:
                print("⚠️ 未获取到老师位置，将使用默认坐标签到")

        # 执行底层签到请求
        result = await api.default_sign(
            active_id=req.activeId,
            sign_type=req.signType,
            object_id=req.objectId or "",
            longitude=final_lon,
            latitude=final_lat,
            address=final_addr,
            sign_code=req.signCode or "",
            enc=req.enc or "",
            course_id=req.courseId,
            class_id=req.classId
        )
        return result
    except Exception as e:
        return {"success": False, "message": str(e)}

@router.post("/api/multi-sign")
async def multi_sign(req: MultiSignRequest):
    results = []
    for user in req.users:
        from engine.session import CXSession
        temp_session = CXSession(config_path=f"config_{user['username']}.json")
        success = await temp_session.login(user['username'], user['password'])
        if success:
            temp_api = CXApi(temp_session)
            result = await temp_api.default_sign(
                active_id=req.activeId,
                sign_type=req.signType
            )
            results.append({
                "username": user['username'],
                "success": result['success'],
                "message": result['message']
            })
        else:
            results.append({
                "username": user['username'],
                "success": False,
                "message": "登录失败"
            })
    return {"success": True, "data": results}

@router.get("/api/qr-sign-url")
async def get_qr_sign_url(activeId: str, enc: Optional[str] = ""):
    try:
        url = await api.generate_qr_sign_url(activeId, enc)
        return {"success": True, "url": url}
    except Exception as e:
        return {"success": False, "msg": str(e)}

@router.get("/api/token")
async def get_pan_token():
    token = await api.get_token()
    return {"success": bool(token), "token": token}

@router.post("/api/save-enc")
async def save_enc(req: EncSaveRequest):
    try:
        with open(ENC_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(req.enc)
        return {"success": True, "msg": "enc已覆盖保存"}
    except Exception as e:
        return {"success": False, "msg": f"写入失败: {str(e)}"}

@router.post("/api/shutdown")
async def shutdown():
    sys.exit(0)
