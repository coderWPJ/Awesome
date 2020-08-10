#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'wupengju'


import time
import random
import json
import requests as rq
from flask import Flask, request, jsonify, render_template
app = Flask(__name__, template_folder='templates', static_folder='statics')


@app.route('/')
def hello_world():
    return render_template('new_index.html')


person_list = [{'name': 'Jams',
                'age': 23,
                'address': 'Cleverland'},
               {'name': 'Kobe',
                'age': 30,
                'address': 'Los angles'}]


@app.route('/person_list', methods=['GET'])
def get_person_list():
    return jsonify({'list': person_list})


def products_for_classfiy(classfiy):
    """
    name 商品名称
    id 商品数据库id
    iapProjectClassify    App内购买项目类型， 1(消耗型项目)      如：王者荣耀点券
                                            2(非消耗型项目)    如：王者荣耀英雄、皮肤
                                            3(自动续期订阅)    如：腾讯视频会员，连续包月
                                            4(非续期订阅)      如：腾讯视频会员，单月
    price_sale  商品当前售价
    platform 投放平台
    productIdentifier  商品唯一标识
    """
    if classfiy == 1:
        iap_list_comsume = [{'name': '60金币',
                             'id': 6,
                             'iapProjectClassify': 1,
                             'price_sale': 6,
                             'productIdentifier': 'com.zhiyun.ZYFilmic_A_goldcoin_60',
                             'platform': 'ZY Cami'}]
        return iap_list_comsume
    elif classfiy == 3:
        iap_list_subscribe = [{'name': '会员连续包月',
                               'id': 1001,
                               'iapProjectClassify': 3,
                               'price_sale': 15,
                               'productIdentifier': 'com.zhiyun.ZYFilmic_C_PrimeVIP_M',
                               'platform': 'ZY Cami'},
                              {'name': '会员1个月',
                               'id': 1002,
                               'iapProjectClassify': 4,
                               'price_sale': 15,
                               'productIdentifier': 'com.zhiyun.ZYFilmic_D_PrimeVIP_M',
                               'platform': 'ZY Cami'}]
        return iap_list_subscribe
    return None


def all_products():
    ret_arr = []
    for classfiy in range(0, 4):
        products_arr = products_for_classfiy(classfiy)
        if products_arr:
            ret_arr = ret_arr + products_arr
    return ret_arr


@app.route('/iap/list', methods=['GET'])
def get_iap_list():
    params = request.args
    classfiy_obj = params.get('classfiy')
    if classfiy_obj:
        classfiy_value = int(classfiy_obj)
        products = products_for_classfiy(classfiy_value)
        return response_request({'list': products})
    products = all_products()
    return response_request({'list': products})


@app.route('/iap/createOrder', methods=['POST'])
def create_iap_order():
    params = request.form
    product_id = params.get('productIdentifier')
    user_id = params.get('userId')
    print('创建了订单, 用户id：', user_id, '产品id：', product_id)

    # 此处订单号生成比较简单，实际开发中请结合公司项目逻辑来生成，并插入数据库
    random_value = random.randint(0, 100000)
    local_time = time.localtime(time.time())
    order_id_str = time.strftime('%Y%m%d%_H:%M:%S', local_time) + '_' + str(random_value)
    return response_request({'orderId': order_id_str})


def request_verify_receipt_data(receipt_data, sandbox=False):
    """请求校验收据结果

    {
      "receipt-data":"", 		// 必选参数，客户端上行的收据base64加密过
      "password":"", 		    // 可选参数，App 专用共享密钥在App Store Connect上获取（自动续费订阅必须有）
      "exclude-old-transactions":false // 可选参数，仅和 iOS7样式的订阅类小票相关。 如果为 true，结果只包括所有订阅的最新续期交易
    }
    """
    apple_verify_url = 'https://buy.itunes.apple.com/verifyReceipt' if sandbox == False else 'https://sandbox.itunes.apple.com/verifyReceipt'
    post_params = {'receipt-data': receipt_data}
    header_info = {'content-type': 'application/json'}  # 一种请求头，需要携带
    result = rq.post(apple_verify_url, data=json.dumps(post_params), headers=header_info)
    return result.json()


def verify_receipt_data_from_apple_server(receipt_data):
    """获取校验收据信息，先从生产获取，若验证是沙盒数据，再从沙盒环境请求"""
    result_dict = request_verify_receipt_data(receipt_data)
    status_value = result_dict.get('status', -1)
    if status_value == 21007:
        print('验证了是沙盒环境的收据，去沙盒环境再次校验')
        result_dict = request_verify_receipt_data(receipt_data, True)
    return result_dict


@app.route('/iap/verifyReceipt', methods=['POST'])
def iap_verify_receipt():
    params = request.form
    user_id = params.get('userId')
    order_id = params.get('orderId')
    product_identifier = params.get('productIdentifier')
    is_sandbox = bool(params.get('sandbox'))
    receipt_data = params.get('receipt-data')
    print('开始验证订单支付结果, 用户id：', user_id, 'order_id: ', order_id)


    if receipt_data is None:
        ret_info = {'status': 0, 'errCode': 105, 'errDes': '订单校验信息异常'}
        return jsonify(ret_info)

    """
    注意：
    服务器需要存储客户端发来的支付收据信息，和订单信息绑定，方便后续使用

    
    Apple 请求返回大数据示例：
    示例1： 消耗品
    {
        'receipt': {
            'receipt_type': 'ProductionSandbox',
            'adam_id': 0,
            'app_item_id': 0,
            'bundle_id': 'com.zhiyun.ZYFilmic',
            'application_version': '17',
            'download_id': 0,
            'version_external_identifier': 0,
            'receipt_creation_date': '2020-08-07 03:30:03 Etc/GMT',
            'receipt_creation_date_ms': '1596771003000',
            'receipt_creation_date_pst': '2020-08-06 20:30:03 America/Los_Angeles',
            'request_date': '2020-08-07 03:30:09 Etc/GMT',
            'request_date_ms': '1596771009605',
            'request_date_pst': '2020-08-06 20:30:09 America/Los_Angeles',
            'original_purchase_date': '2013-08-01 07:00:00 Etc/GMT',
            'original_purchase_date_ms': '1375340400000',
            'original_purchase_date_pst': '2013-08-01 00:00:00 America/Los_Angeles',
            'original_application_version': '1.0',
            'in_app': [{
                'quantity': '1',
                'product_id': 'com.zhiyun.ZYFilmic_6',
                'transaction_id': '1000000703242829',
                'original_transaction_id': '1000000703242829',
                'purchase_date': '2020-08-07 03:30:03 Etc/GMT',
                'purchase_date_ms': '1596771003000',
                'purchase_date_pst': '2020-08-06 20:30:03 America/Los_Angeles',
                'original_purchase_date': '2020-08-07 03:30:03 Etc/GMT',
                'original_purchase_date_ms': '1596771003000',
                'original_purchase_date_pst': '2020-08-06 20:30:03 America/Los_Angeles',
                'is_trial_period': 'false'
            }]
        },
        'status': 0,
        'environment': 'Sandbox'
    }    
    
    status
    0 校验成功
    21000 对App Store的请求不是使用HTTP POST request方法发出的。
    21001 应用商店不再发送此状态代码。
    21002 收据数据属性中的数据格式不正确或服务遇到临时问题。再试一次。
    21003 无法验证收据。
    21004 您提供的共享机密与您帐户的存档共享机密不匹配。
    21005 回执服务器暂时无法提供回执。再试一次。
    21006 此收据有效，但订阅已过期。当此状态码返回到服务器时，接收数据也会被解码并作为响应的一部分返回。仅为自动续订订阅的iOS 6样式事务处理收据返回。
    21007 此收据来自测试环境，但已发送到生产环境进行验证。
    21008 此收据来自生产环境，但已发送到测试环境进行验证。
    21009 内部数据访问错误。请稍后再试。
    21010 找不到用户帐户或已删除。
    21100~21199是各种内部数据访问错误。
    """

    result_dict = verify_receipt_data_from_apple_server(receipt_data)
    print('Apple server 验证收据结果：', result_dict)
    response_info = {'orderId': order_id, 'paymentStatus': -1, 'isYES': True, 'isNo': False}
    error_code = 0
    try:
        # environment = result_dict.get('environment')
        receipt_dict = result_dict.get('receipt')
        in_app_array = receipt_dict.get('in_app')
        if in_app_array is None or len(in_app_array) == 0:
            return response_request_with_error('', 90002)
        product_found = False
        for product_info in in_app_array:
            product_info = in_app_array[0]
            product_iden = product_info.get('product_id')
            if product_iden == product_identifier:
                transaction_id = product_info.get('transaction_id')
                purchase_date_s_value = float(receipt_dict.get('request_date_ms')) / 1000
                purchase_time_local = time.localtime(purchase_date_s_value)
                purchase_time_local_str = time.strftime('%Y-%m-%d %H:%M:%S', purchase_time_local)
                print('支付校验通过了：', product_iden, '交易id：', transaction_id, '交易时间：', purchase_time_local_str)
                append_dict = {'purchase_time': purchase_date_s_value, 'productIdentifier': product_iden, 'sandbox': is_sandbox}
                response_info.update(append_dict)
                response_info['paymentStatus'] = True
                product_found = True
        if not product_found:
            error_code = 90002
    except Exception as e:
        error_code = 90001

    return response_request_with_error(response_info, error_code)

def response_request_with_error(info, error):
    err_des = '请求失败' if error > 0 else ''
    all_error_dict = all_error_info()
    err_des = all_error_dict.get(error, "请求失败")
    ret_info = {'errCode': error, 'errDes': err_des}
    ret_info.update(info)
    return jsonify(ret_info)


def response_request(info):
    ret_info = {'errCode': 0, 'errDes': None}
    ret_info.update(info)
    return jsonify(ret_info)
    # return jsonify(dict(ret_info, **info))


@app.route('/index')
def file_list():
    return render_template('index.html')


def all_error_info():
    err_dict_success = {'errCode': 0,
                        'errDes': None}
    return [err_dict_success]


def all_error_info():
    error_dict = {90001: '商品支付信息验证失败',
                  90002: '支付的商品信息异常',
                  90009: '找不到商品信息'}
    return error_dict


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='8888')
