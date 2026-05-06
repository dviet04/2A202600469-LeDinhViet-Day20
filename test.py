import requests
print(requests.get("https://api.tavily.ai").status_code)
# import requests
# print(requests.get("https://google.com").status_code)

# save as no_sni.py and run: python no_sni.py
# import socket, ssl
# s = socket.create_connection(("api.tavily.ai", 443), timeout=10)
# ctx = ssl.create_default_context()
# # server_hostname=None để không gửi SNI
# ss = ctx.wrap_socket(s, server_hostname=None)
# ss.send(b"GET / HTTP/1.1\r\nHost: api.tavily.ai\r\nConnection: close\r\n\r\n")
# print(ss.recv(4096))
# ss.close()