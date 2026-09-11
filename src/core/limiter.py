from slowapi import Limiter
from slowapi.util import get_remote_address

# 按客户端 IP 限流，进程内共享
limiter = Limiter(key_func=get_remote_address)