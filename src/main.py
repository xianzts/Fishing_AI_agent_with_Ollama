from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api import api_routes

app = FastAPI(title="Fishing agent")

# 加上CORS配置，解决OPTIONS预检405
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 开发环境，允许全部来源；生产不要用*
    allow_credentials=True,
    allow_methods=["*"],         # 允许OPTIONS、POST等全部method
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_routes.router)