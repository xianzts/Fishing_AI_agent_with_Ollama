from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json

from src import RagServices
from src import LLMServices
from src import UserAccount

app = FastAPI(title="Fishing agent")

# 加上CORS配置，解决OPTIONS预检405
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 开发环境，允许全部来源；生产不要用*
    allow_credentials=True,
    allow_methods=["*"],         # 允许OPTIONS、POST等全部method
    allow_headers=["*"],
)

# =========全局：服务启动一次性加载向量库，仅执行一次=========
rag_service = RagServices()
global_retriever = rag_service.load_vector_dataset()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    form_data.username 输入账号
    form_data.password 输入明文密码
    """
    account_instance = UserAccount()
    username = form_data.username
    password = form_data.password

    access_token_details = account_instance.confirm(username, password)
    if access_token_details is None:
        raise HTTPException(status_code=401, detail="账号或密码错误")

    # 必须返回这个固定结构！
    return {"access_token": access_token_details["access_token"], "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme)):
    account_instance = UserAccount()
    payload = account_instance.verify_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Token无效！请检查输入的token是否正确，或重新登录获取新token"
        )
    return payload


# =========受保护接口示例：访问个人信息，必须携带token=========
@app.get("/me")
def get_profile(current_user=Depends(get_current_user)):
    # current_user就是JWT解析出来的 {user_id:xxx, username:xxx}
    return {"user_id": current_user["user_id"], "username": current_user["username"]}


@app.post("/rag/chat")
def rag_query(
        question: str,
        current_user=Depends(get_current_user)
):
    LLM_instance = LLMServices()
    print(f"用户{current_user['username']}提问：{question}")
    username = current_user['username']

    # SSE生成器闭包
    def sse_generator():
        try:
            stream_iter = LLM_instance.stream_answer(username, question, global_retriever)
            full_ai_response = ""  # 攒完整回答
            for chunk in stream_iter:
                content = chunk.content
                full_ai_response += content
                # SSE协议格式：data: json字符串\n\n，两个换行符是协议分隔符
                yield f"data: {json.dumps({'chunk': content})}\n\n"
            # 流结束标记
            yield f"data: {json.dumps({'chunk': '[DONE]'})}\n\n"
            # 全部流式结束，保存本轮问答到内存记忆
            LLM_instance.append_history(username, question, full_ai_response)

        except Exception as err:
            print(f"LLM异常: {err}")
            err_msg = str(err)
            yield f"data: {json.dumps({'error': err_msg, 'chunk': '[DONE]'})}\n\n"

    # 设置SSE标准响应头
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    }
    return StreamingResponse(sse_generator(), headers=headers)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
