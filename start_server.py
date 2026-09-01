import time
import threading
import webbrowser
from pathlib import Path
import uvicorn

# ============ 配置区 ============
HOST = "127.0.0.1"
PORT = 8000
# FastAPI app 位置 src/fastAPI.py 的 app 对象
FASTAPI_APP = "src.fastAPI:app"
# 本地SSE测试html路径（assets文件夹）
HTML_REL_PATH = r"assets/sse_test.html"
# 等待服务启动秒数
WAIT_SEC = 2
# ===============================

# 获取项目根目录
ROOT_DIR = Path(__file__).parent.resolve()


def run_uvicorn_server():
    """子线程运行uvicorn服务，不会阻塞主线程"""
    server = uvicorn.Server(
        config=uvicorn.Config(
            FASTAPI_APP,
            host=HOST,
            port=PORT,
            reload=False,   # ⚠️多线程模式reload必须关闭，会报错！
            log_level="info"
        )
    )
    server.run()


if __name__ == "__main__":
    # 1. 启动uvicorn后台线程
    server_thread = threading.Thread(target=run_uvicorn_server, daemon=True)
    server_thread.start()

    print(f"✅ FastAPI服务正在启动，等待 {WAIT_SEC}s ...")
    time.sleep(WAIT_SEC)

    # 2. 打开 Swagger UI 接口文档
    swagger_url = f"http://{HOST}:{PORT}/docs"
    webbrowser.open(swagger_url)
    print(f"🌐 已打开Swagger UI: {swagger_url}")

    # 3. 打开本地 sse_test.html
    html_file = ROOT_DIR / HTML_REL_PATH
    if html_file.exists():
        # file协议打开本地静态页面
        webbrowser.open(f"file://{html_file}")
        print(f"🌐 已打开SSE测试页面: {html_file}")
    else:
        print(f"⚠️警告：找不到文件 {html_file}，跳过打开html")

    print("\n💡按 Ctrl+C 停止服务")
    # 主线程阻塞等待，防止程序直接退出
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n🛑收到终止信号，程序退出。")