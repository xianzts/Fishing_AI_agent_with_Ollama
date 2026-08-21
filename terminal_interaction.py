import llm_services
import user_account
import config
import pwinput


def chat_interaction(rag, llm, account):
    retriever = rag.load_vector_dataset()

    print("---本地钓鱼AI Agent终端交互系统登录页面---")
    while True:
        user_name = input("请输入账号：")
        password = pwinput.pwinput("请输入密码：")
        if account.confirm(user_name, password):
            print("{} 成功登录！".format(user_name))
            account.user_name = user_name
            break
        else:
            print("账号或密码错误，请重新输入！")

    print("---本地钓鱼AI Agent终端交互系统（输入“exit”退出, 输入”clear“清除上下文记忆）---")
    while True:
        new_question = input("{}>".format(account.user_name))

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
            answer_stream = llm.stream_answer(new_question, retriever)
            for answer_line in answer_stream:
                content = answer_line.content
                print(content, end="", flush=True)

            print("\n---------------")
            print("agent已生成完毕！")
            print("---------------")

        except Exception as err:
            print("\n执行异常，异常原因：{}".format(err))