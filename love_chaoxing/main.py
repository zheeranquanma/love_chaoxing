import os
import sys
import subprocess
import time
import threading
import webbrowser
from pathlib import Path
import hashlib

# ====================== 【每周算法锁 - 核心】 ======================
def get_week_seed():
    """每周唯一种子，同一周内不变"""
    t = time.localtime()
    year = t.tm_year
    week = t.tm_yday // 7  # 按自然周算
    return f"ChaoxingSign_{year}_W{week}"

def verify_code(input_code: str) -> bool:
    """校验码算法：每周固定密钥哈希，进群发码"""
    seed = get_week_seed()
    true_code = hashlib.md5(seed.encode()).hexdigest()[:8].upper()
    return input_code.strip().upper() == true_code

def check_license():
    """启动前校验，失败直接退出"""
    print("=" * 50)
    print("🔒 超星签到助手 - 每周授权校验")
    print("📌 请进群获取本周【8位校验码】")
    print("=" * 50)
    code = input("请输入本周校验码：").strip()
    if not verify_code(code):
        print("❌ 校验码错误！请联系管理员进群获取")
        input("按回车退出...")
        sys.exit(1)
    print("✅ 校验通过，本周可正常使用\n")
# ==================================================================


required = ['fastapi', 'uvicorn', 'requests', 'aiofiles']
for pkg in required:
    try:
        __import__(pkg.replace('-', '_'))
    except ImportError:
        print(f"安装依赖: {pkg}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])

check_license()


from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from web.routes import router

app = FastAPI(title="Chaoxing Sign Helper")
STATIC_DIR = Path(__file__).parent / "web" / "static"

# 路由
@app.get("/")
async def serve_index():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/index.html")
async def serve_scanner_file():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/index")
async def serve_scanner():
    return FileResponse(STATIC_DIR / "index.html")

app.include_router(router)
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# 启动服务
if __name__ == '__main__':
    def open_browser():
        time.sleep(1.5)
        webbrowser.open('http://127.0.0.1:8000')
    
    if not os.getenv('DEBUG'):
        threading.Thread(target=open_browser, daemon=True).start()
    
    print("\n" + "="*50)
    print("超星签到助手已启动")
    print("访问地址: http://127.0.0.1:8000")
    print("按 Ctrl+C 停止服务")
    print("="*50 + "\n")
    
    uvicorn.run(app, host='127.0.0.1', port=8000, log_level='warning')