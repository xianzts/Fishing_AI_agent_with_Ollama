from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import logging

from datetime import datetime, timedelta, timezone

from src.services.rag_services import RagServices
from src.services.llm_services import LLMServices
from src.services.user_account import UserAccount

from src.core.security import Security
from src.core import config

logger = logging.getLogger(__name__)

# =========全局：服务启动一次性加载向量库，仅执行一次=========
rag_service = RagServices()
global_retriever = rag_service.load_vector_dataset()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# 创建一个 router 实例
router = APIRouter()


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    form_data.username 输入账号
    form_data.password 输入明文密码
    """
    username = form_data.username
    password = form_data.password

    access_token_details = UserAccount().confirm(username, password)
    if access_token_details is None:
        raise HTTPException(status_code=401, detail="账号或密码错误")

    # 必须返回这个固定结构！
    return {"access_token": access_token_details["access_token"], "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme), response: Response = None):
    payload = Security().verify_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Token无效！请检查输入的token是否正确，或重新登录获取新token"
        )

    current_time = datetime.now(timezone.utc)
    exp_time = datetime.fromtimestamp(payload["expire"], tz=timezone.utc)
    if exp_time - current_time < config.JWT_REFRESH_TOKEN_EXPIRES:
        logger.info("token即将过期，正在刷新token")
        new_token = Security().jwt_token_generation(payload["user_id"], payload["username"])

        # 把新 token 放入响应头
        if response:
            response.headers["X-New-Token"] = new_token
            response.headers["Access-Control-Expose-Headers"] = "X-New-Token"
            logger.info("新token已放入响应头")

        new_payload = Security().verify_access_token(new_token)
        if new_payload is None:
            raise HTTPException(
                status_code=401,
                detail="Token刷新失败"
            )
        payload = new_payload

    return payload


# =========受保护接口示例：访问个人信息，必须携带token=========
@router.get("/me")
def get_profile(current_user=Depends(get_current_user)):
    # current_user就是JWT解析出来的 {user_id:xxx, username:xxx}
    return {"user_id": current_user["user_id"], "username": current_user["username"],
            "issue_at": current_user["issue_at"], "expire": current_user["expire"]}


@router.post("/rag/chat")
def rag_query(
        question: str,
        current_user=Depends(get_current_user)
):
    LLM_instance = LLMServices()

    user_id = current_user["user_id"]
    user_name = current_user['username']

    # SSE生成器闭包
    def sse_generator():
        try:
            if question == "clear":
                LLM_instance.clear_history(user_id)
                yield f"data: {json.dumps({'chunk': '所有历史对话记录删除完成'})}\n\n"
            else:
                stream_iter = LLM_instance.stream_answer(user_id, user_name, question, global_retriever)
                full_ai_response = ""  # 攒完整回答
                for chunk in stream_iter:
                    content = chunk.content
                    full_ai_response += content
                    # SSE协议格式：data: json字符串\n\n，两个换行符是协议分隔符
                    yield f"data: {json.dumps({'chunk': content})}\n\n"
                # 流结束标记
                yield f"data: {json.dumps({'chunk': '[DONE]'})}\n\n"
                # 全部流式结束，保存本轮问答到内存记忆
                LLM_instance.append_history(user_id, user_name, question, full_ai_response)

        except Exception as err:
            err_msg = str(err)
            yield f"data: {json.dumps({'error': err_msg, 'chunk': '[DONE]'})}\n\n"

    # 设置SSE标准响应头
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    }
    return StreamingResponse(sse_generator(), headers=headers)
