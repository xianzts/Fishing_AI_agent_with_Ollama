import pwinput

import src.llm_services
import src.user_account
import src.config


def chat_interaction(rag, llm, account):
    retriever = rag.load_vector_dataset()

    print("---本地钓鱼AI Agent终端交互系统登录页面---")
    while True:
        user_name = input("请输入账号：")
        password = pwinput.pwinput("请输入密码：")

        token_details = account.confirm(user_name, password)
        if token_details is not None:
            token = token_details["access_token"]
            print("你的access token是：{}".format(token))
            print("token详细信息：{}".format(account.verify_access_token(token)))
            account.user_name = user_name
            break

    print("---本地钓鱼AI Agent终端交互系统（输入“exit”退出, 输入”clear“清除上下文记忆）---")
    while True:
        new_question = input("{}>".format(account.user_name))

        if len(new_question) == 0:
            print("请输入问题！")
            continue

        if new_question.lower() == 'exit':
            print("See You Next Time!")
            break

        if new_question.lower() == 'clear':
            llm.clear_history()
            print("已清空上下文记忆！")
            continue

        print("AI>", end="", flush=True)
        try:
            # stream output with each line
            answer_stream = llm.stream_answer(account.user_name, new_question, retriever)
            for answer_line in answer_stream:
                content = answer_line.content
                print(content, end="", flush=True)

            print("\n---------------")
            print("agent已生成完毕！")
            print("---------------")

        except Exception as err:
            print("\n执行异常，异常原因：{}".format(err))