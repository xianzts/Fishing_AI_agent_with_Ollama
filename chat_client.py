from langchain_ollama import OllamaLLM

# load local model
llm = OllamaLLM(model="qwen2:7b",
                base_url="http://127.0.0.1:11434",
                temperature=0.7   # creation[0, 1]
                )


def chat_interaction():
    while True:
        print("请输入你的问题（输入“exit”退出）:")
        question = input()

        if question == 'exit':
            break

        print("agent正在给出答案，请稍后......")
        answer = llm.invoke(question)
        print("agent已生成答案！")
        print(answer)
        print("---------------")


if __name__ == "__main__":
    chat_interaction()