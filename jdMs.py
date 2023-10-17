import concurrent
import datetime
from concurrent.futures import ProcessPoolExecutor
import json
import sys
import time
import requests
import jpype
import urllib3
from log import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
cookie_str = ''

sub_order_time = '2023-10-08 18:07:59.500'
skuId = 100012043978

# 创建一个Session对象
session = requests.session()

jump_url = 'https://un.m.jd.com/cgi-bin/app/appjmp'
token_body = '{"action":"to","to":"https://divide.jd.com/user_routing?skuId=%s"}' % skuId
token_function_id = ''
client = ''
clientVersion = ''
uuid = ''

params = {
    "tokenKey": 'AAEAMAje64z7n1vGvN0nq_FH_PgEBZMFBUlqW7rVS-_W2kNwPpykXwjaGg7QDHS7TzrFPQ1',
    "to": "https://divide.jd.com/user_routing?skuId=%s" % skuId
}

fp = ''
eid = ''
ep = ''
token_payload = {}

order_rul = 'https://marathon.jd.com/seckillnew/orderService/submitOrder.action?skuId=' + str(skuId)
data = {}

is_first_init_data = True

def make_reserve():
    """商品预约"""
    url = 'https://api.m.jd.com/client.action'
    body = '{"autoAddCart":"0","bsid":"","check":"0","ctext":"","isShowCode":"0","mad":"0","skuId":"%s","type":"4"}' % skuId
    payload = {}
    JDClass = jpype.JClass("com.jdsdk.jd_main")
    jd = JDClass()
    sing = jd.runJni(['appoint', body, uuid, client, clientVersion])
    sign = str(sing)
    data_array = sign.split('&')
    data_dict = {}
    # 遍历分割后的数组
    for item in data_array:
        key, value = item.split('=')
        data_dict[key] = value
    payload['st'] = data_dict['st']
    payload['sign'] = data_dict['sign']
    payload['sv'] = 111
    resp = session.post(url=url, params=payload)
    resp_json = parse_json(resp.text)
    print(resp_json)
    try:
        if resp_json['title'] == '您已成功预约，无需重复预约' or resp_json['title'] == '预约成功！':
            logger.info(resp_json['title'])
    except Exception as e:
        logger.error('预约失败正在重试...')


def sub_order():
    global is_first_init_data
    while True:
        """
            init.action 拿到生成订单的信息
            替换订单模版的某些信息
        """
        if is_first_init_data:
            order_init_url = 'https://marathon.jd.com/seckillnew/orderService/init.action'
            order_init_data = {
                'sku': skuId,
                'num': 1,
            }
            init_data = session.post(order_init_url, params=order_init_data)
            if init_data.text == 'null':
                print('init_data == null')
                continue
            try:
                init_data = parse_json(init_data.text)
                if init_data.get('islogin'):
                    print('islogin.no')
                    continue
            except Exception as e:
                logger.info('抢购失败，返回信息:{}'.format(init_data.text[0: 128]))
                continue
        """
            提交订单
        """

        for _ in range(1000):
            order_resp = session.post(url=order_rul, params=data)
            try:
                resp_json = parse_json(order_resp.text)
            except Exception as e:
                logger.info('抢购失败，返回信息:{}'.format(order_resp.text[0: 128]))
                continue
            if resp_json.get('success'):
                order_id = resp_json.get('orderId')
                total_money = resp_json.get('totalMoney')
                pay_url = 'https:' + resp_json.get('pcUrl')
                print('抢购成功，订单号:{}, 总价:{}, 电脑端付款链接:{}'.format(order_id, total_money, pay_url))
                logger.info('抢购成功，订单号:{}, 总价:{}, 电脑端付款链接:{}'.format(order_id, total_money, pay_url))
            else:
                logger.info('抢购失败，返回信息:{}'.format(resp_json))
                continue
            """
                休息10毫秒
            """
            time.sleep(0.01)


def kill_mt():
    global marathon_location
    """
        appjmp
        获取跳转Location
     """
    response = session.get(url=jump_url, params=params, allow_redirects=False, verify=False)
    location = response.headers.get('Location')
    """
        divide验证登陆信息
    """
    divide_response = session.get(location, allow_redirects=False, verify=False)
    if divide_response.headers.get('Location') == 'https://marathon.jd.com/mobile/koFail.html':
        print("第二步出错！！wskey过期")
        die()
    else:
        marathon_location = divide_response.headers.get('Location')
    """
        获取第三步跳转连接
        当活动开始的时候才会订单生成地址
        成功网址 = https://marathon.jd.com/seckillM/seckill.action?skuId=100012043978&num=1&rid=1621310648
        失败网址 = https://marathon.jd.com/mobile/koFail.html 非抢购时间都会失败
    """
    marathon = session.get(marathon_location, allow_redirects=False, verify=False)
    get_pay_location = marathon.headers.get('Location')
    """
        seckill.action
        在app上就是填写订单
        只有在抢购期间内才会请求成功，否则都是失败的
    """
    if get_pay_location == 'https://marathon.jd.com/mobile/koFail.html' or get_pay_location is None:
        die()
    session.get(get_pay_location, allow_redirects=False, verify=False)
    sub_order()


def parse_json(s):
    begin = s.find('{')
    end = s.rfind('}') + 1
    return json.loads(s[begin:end])


def die():
    sys.exit(1)

def getToken():
    logger.info('开始获取 token')
    JDClass = jpype.JClass("com.jdsdk.jd_main")
    jd = JDClass()
    sing = jd.runJni([token_function_id, token_body, uuid, client, clientVersion])
    sign = str(sing)
    data_array = sign.split('&')
    data_dict = {}
    # 遍历分割后的数组
    for item in data_array:
        key, value = item.split('=')
        data_dict[key] = value
    token_payload['st'] = data_dict['st']
    token_payload['sign'] = data_dict['sign']
    token_payload['sv'] = 111
    url = 'https://api.m.jd.com/client.action'
    token_resp = requests.post(url, params=token_payload)
    if token_resp.status_code != 200:
        print("请求出错！！！")
    json = parse_json(token_resp.text)
    if json.get('echo'):
        print("错误信息")
        print(json['echo'])
        die()
    params['tokenKey'] = json['tokenKey']
    logger.info('获取 token完毕')
    logger.info('获取到token:' + json['tokenKey'])


if __name__ == "__main__":
    # 添加Jar包到类路径
    jvmPath = jpype.getDefaultJVMPath()
    d = './out/artifacts/xxx_jar/xxx.jar'  # 对应jar地址
    jpype.startJVM(jvmPath, "-ea", "-Djava.class.path=" + d + "")
    make_reserve()
    getToken()
    kill_mt()
