from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from rag_services import RagServices
from llm_services import LLMServices
from user_account import UserAccount

app = FastAPI(title="Fishing agent")

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
    return account_instance.verify_access_token(token)


# =========受保护接口示例：访问个人信息，必须携带token=========
@app.get("/me")
def get_profile(current_user = Depends(get_current_user)):
    # current_user就是JWT解析出来的 {user_id:xxx, username:xxx}
    return {"user_id": current_user["user_id"], "username": current_user["username"]}


@app.post("/rag/chat")
def rag_query(
    question: str,
    current_user = Depends(get_current_user)
):
    LLM_instance = LLMServices()
    print(f"用户{current_user['username']}提问：{question}")
    try:
        # 直接复用全局已经加载好的 retriever，不要再load
        answer_stream = LLM_instance.stream_answer(current_user['username'], question, global_retriever)
        answer = ""
        for answer_line in answer_stream:
            answer = answer + answer_line.content

    except Exception as err:
        print("\n执行异常，异常原因：{}".format(err))
        # 不要吞掉异常，向上抛出，前端收到错误信息
        raise HTTPException(status_code=500, detail=f"服务内部异常：{str(err)}")

    return {"answer": answer, "who": current_user["username"]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)