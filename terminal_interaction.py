import llm_services
import config


def chat_interaction(rag, llm):
    retriever = rag.load_vector_dataset()
    print("---本地钓鱼AI Agent终端交互系统（输入“exit”退出, 输入”clear“清除上下文记忆）---")
    while True:
        new_question = input("{}>".format(config.USER))

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