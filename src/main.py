from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.exceptions import register_exception_handlers
from src.api import api_routes
from src.core.limiter import limiter

app = FastAPI(title="Fishing agent")

# 加上CORS配置，解决OPTIONS预检405
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 开发环境，允许全部来源；生产不要用*
    allow_credentials=True,
    allow_methods=["*"],         # 允许OPTIONS、POST等全部method
    allow_headers=["*"],
)

# 注册全局异常处理器
register_exception_handlers(app)

# ========== 注册限流器 ==========
app.state.limiter = limiter

# 注册路由
app.include_router(api_routes.router)