## AI_agent
基于 Ollama + LangChain 搭建本地AI Agent学习项目

# 快速开始

## 环境安装
请在 https://ollama.com/download 中下载ollama客户端

在cmd中使用 ollama pull qwen2:7b 下载qwen2:7b模型

使用ollama pull nomic-embed-text 下载nomic-embed-text模型

运行前请使用 pip install -r requirements.txt 命令安装代码必要的依赖模块

## 初次运行
打开start_server.py文件，使用Pycharm等IDE直接运行，运行成功时会自动弹出两个页面，一个Swagger UI页面作为账号登录，SSE RAG测试页面作为垂钓QA使用。

在Swagger UI页面进行账号登录时，请先点击右上角的Authorize，输出username和password即可，client不需要输入，如果登录成功，则会显示Authorized。

登录成功之后，点击default中的GET /me Get Profile，再点击Try it out，最后选择Execute，成功状态下会输出Response Code 200，可以在curl中最后一行Authorization: Bearer中找到自己的token，也就是Bearer后面的一大串字符串。

最后将这串token粘贴在SSE RAG测试页面的token处即可使用垂钓Agent聊天功能。

# 版本更新记录

## 版本v0.1
终端交互对话程序，使用qwen2:7b模型 - 2026.08.15：

## 版本v0.2
### v0.2.0
终端交互对话程序，使用qwen2:7b模型

添加流式输出和上下文记忆功能 - 2026.08.15

### v0.2.1
添加上下文记忆清理功能 - 2026.08.15

## 版本v0.3
新增钓鱼RAG向量知识库，使用nomic-embed-text模型 - 2026.08.20

## 版本v0.4
重构代码，将I/O与业务分层 - 2026.08.20

## 版本v0.5
### v0.5.0
添加账密系统，账户会连入数据库 - 2026.08.21

### v0.5.1
优化Agent参数，解决了部分回答不准确的问题 - 2026.08.22

## 版本v0.6
### v0.6.0
添加jwt鉴权功能，生成access token - 2026.08.24

### v0.6.1
添加Swagger UI页面测试文件，作为账号登录测试 - 2026.08.25

### v0.6.2
优化Agent参数，解决了部分回答不准确的问题
添加SSE RAG测试页面作为垂钓聊天简易UI - 2026.08.25

### v0.6.3
重构代码，隔离了测试层和功能层 - 2026.08.25

### v0.6.4
重构代码，添加了一些异常处理 - 2026.09.01

## 版本v0.7
将上下文历史对话移动到数据库中，最多保存6条最近的记录 - 2026.09.02


