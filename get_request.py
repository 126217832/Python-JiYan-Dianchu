#coding=utf-8

"""
获取验证图片
"""
from PIL import Image
import os
import json
from io import BytesIO

#  开启命令：mitmdump --mode upstream:http://default-upstream-proxy.local:8080/ -s xxx.py
# def request(flow):
#     # 这里配置二级代理的ip地址和端口
#     if flow.live:
#         proxy = ("110.52.235.54", 9999)
#         flow.live.change_upstream_proxy_server(proxy)

def response(flow):
    # 通过抓包软包软件获取请求的接口
    #http://resources.geetest.com/nerualpic/phrase_l1_zh_2018.10.9/cubism6/b24812538492b5ad23e90d7f3ca8c340.jpg?challenge=a58e39df7a0c00acaf17b24408c26514
    #抓取请求的信息，第一次请求图片url信息
    if '.jpg?' in flow.request.url: #图片请求
        try:
            os.mkdir('captcha')
        except:
            pass
        dirname = 'captcha/%s/'%flow.request.url.split('?')[0].split('/')[-1].split('.')[0]
        filename = flow.request.url.split('?')[0].split('/')[-1]
        image = Image.open(BytesIO(flow.response.content))
        image2 = image.resize((305, 344))
        try:
            os.mkdir(dirname)
        except:
            pass
        image.save(dirname + 'original_'+filename)
        image2.save(dirname+filename)
        with open('./captcha/request.txt', 'w') as f:
            f.write(filename)
