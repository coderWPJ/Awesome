## <center> IAP 内购实现方案 (iOS+Server)


### 摘要：

此文是一篇 IAP 内购的技术实现方案概述，服务端用的是Python语言+Flask框架实现，相关代码仅作为客户端所需逻辑的补充。具体到实际开发中，后台开发人员可参考本方案的实现逻辑，而部分业务的具体实现请结合产品的整体规划来实现，如：订单列表、订单的生成、收据校验结果的判定、商品发放时机等。

### 一. 介绍
<b>IAP(In-App-Perchage)</b>  内购是Apple对于数字类型商品唯一支持的支付通道，有如下四种：

```
1. 消耗型项目      如：王者荣耀点券 

2. 非消耗型项目      如：王者荣耀永久英雄、永久皮肤

3. 自动续期订阅     如：腾讯视频会员，连续包月 

4. 非续期订阅       如：腾讯视频会员，单月、季度、年度
```

本文主要介绍内购的业务流程、代码实现、可能遇到的问题与解决方案，包含客户端与服务端。itunes Connect相关操作，及审核相关疑问可自行Google（或百度）。

### 二. 支付流程
![avatar](https://upload-images.jianshu.io/upload_images/4637097-adff9d69f82e7e5e.png?imageMogr2/auto-orient/strip|imageView2/2/w/876)

### 三. 实现
#### 3.1 商品展示
后台提供商品列表接口供App调用
#### 3.2 用户选择购买商品

##### 3.2.1 客户端查询商品（后台返回的商品列表）是否存在
```
// 发送商品查询请求
SKProductsRequest *request = [[SKProductsRequest alloc] initWithProductIdentifiers:[NSSet setWithObject:productIAPModel.productIdentifier]];
request.delegate = self;
[request start];
```

##### 3.2.2 商品存在，开始创建订单
客户端提交商品id，和用户信息至后台，后台根据对应内容生成订单，并返回订单信息给客户端，此时客户端可根据订单号发起支付，若生成订单失败则不能支付

```
// 在获取到请求结果时查询欲购商品是否存在，存在则创建订单
- (void)productsRequest:(SKProductsRequest *)request didReceiveResponse:(SKProductsResponse *)response{
    if (!self.curIAPModel) {
        return;
    }
    NSArray *product = response.products;
    NSLog(@"无效的productID:%@", response.invalidProductIdentifiers);
    if (((response.invalidProductIdentifiers.count > 0) &&
        ([response.invalidProductIdentifiers containsObject:self.curIAPModel.productIdentifier])) || (product.count==0)) {
        dispatch_async(dispatch_get_main_queue(), ^{
            [ZYToastView hideDotToastActivity];
            [ZYToastView makeZFilmCenterToast:@"购买的商品信息异常" view:self.view];
        });
        return;
    }
    
    SKProduct *targetProduct = nil;
    for (NSInteger idx = 0; idx < product.count; idx++) {
        SKProduct *pro = product[idx];
        NSDictionary *productInfo = @{@"localizedTitle":[pro localizedTitle],
                                      @"localizedDescription":[pro localizedDescription],
                                      @"price":[pro price],
                                      @"productIdentifier":[pro productIdentifier]};
        NSLog(@"产品信息  == %@", productInfo);
        if([pro.productIdentifier isEqualToString:self.curIAPModel.productIdentifier]){
            targetProduct = pro;
            break;
        }
    }
    if (targetProduct) {
    	/// 开始创建订单
    	......
    }
}

```
#### 3.3 用户支付订单
客户端根据商品唯一标识和订单信息发起支付

```
// 发起IAP支付
- (void)startIAPPay:(SKProduct *)targetProduct orderId:(NSString *)orderId{
    SKMutablePayment *payment = [SKMutablePayment paymentWithProduct:targetProduct];
    payment.applicationUsername = orderId;
    [[SKPaymentQueue defaultQueue] addPayment:payment];
}
```

```
// 监听购买结果
- (void)paymentQueue:(SKPaymentQueue *)queue updatedTransactions:(NSArray *)transaction{
   for(SKPaymentTransaction *tran in transaction){
      /**
       SKPaymentTransactionStatePurchasing,    // 交易正在被添加至支付队列
       SKPaymentTransactionStatePurchased,     // 交易完成
       SKPaymentTransactionStateFailed,        // 用户取消交易，或交易失败，未被添加至支付队列
       SKPaymentTransactionStateRestored,      // 已经购买过
       SKPaymentTransactionStateDeferred,      // 最终状态未确定
       */

      NSLog(@"交易信息有更新     == %ld", tran.transactionState);
      if (tran.transactionState == SKPaymentTransactionStatePurchasing) {
          continue;
      }
      if (tran.transactionState == SKPaymentTransactionStateFailed) {
          [[SKPaymentQueue defaultQueue] finishTransaction:tran];
		  // 处理支付失败的逻辑
		  ......
          return ;
      }
      if ((tran.transactionState == SKPaymentTransactionStatePurchased) ||
          (tran.transactionState == SKPaymentTransactionStateRestored)) {
            
          NSURL *receiptURL = [[NSBundle mainBundle] appStoreReceiptURL];
          NSData *receipt = [NSData dataWithContentsOfURL:receiptURL];
          if (receipt && (receipt.length > 0)) {
              if (tran.payment.applicationUsername.zy_isValuable) {
                   NSDictionary *requestDict = @{@"receipt-data": [receipt base64EncodedStringWithOptions:0],
                                                 @"sandbox":@"1",
                                                 @"orderId":tran.payment.applicationUsername,
                                                 @"productIdentifier":self.curIAPModel.productIdentifier,
                                                 @"userId":@""};
                   NSString *url = [ZYIAPServerHost stringByAppendingString:@"iap/verifyReceipt"];
                   // 此处提交校验收据给后台，得到支付结果，让后台去根据校验的支付结果来判定是否发放对应虚拟商品
                   .....
                   
                   
                   
                } else {
             NSLog(@"支付结果没有找到订单编号  %ld", tran.transactionState);
          }
        } else {
            // 交易凭证信息丢失，尝试请求一次交易凭证
            SKReceiptRefreshRequest *receiptRefreshRequest = [[SKReceiptRefreshRequest alloc] initWithReceiptProperties:nil];
            receiptRefreshRequest.delegate = self;
            [receiptRefreshRequest start];
        }
      }
   }
}
```

#### 3.4 校验收据
1. 校验渠道：App store server ，有生产系统（https://buy.itunes.apple.com/verifyReceipt）和sandbox（https://sandbox.itunes.apple.com/verifyReceipt）之分
2. 对于支付收据的校验，若无特殊的要求，安全起见请尽量将校验工作放在后台，即客户端提交订单信息与支付收据至后台，后台校验支付结果，根据结果判定是否发放对应虚拟商品。

> Notice1：Apple 官方建议的校验逻辑：先调用 <u><font color='#FF0000'>https://buy.itunes.apple.com/verifyReceipt</font></u> 接口来校验收据，当响应数据中 <font color='#0000FF'> status </font> 字段为 <font color='#0000FF'> 21007 </font> 时，再调用 <u><font color='#FF0000'>https://sandbox.itunes.apple.com/verifyReceipt</font></u> 去校验。
> 
> Notice2：App store server接口延时可能比较高，与此同时，后台请对收据做数据库存储，方便后续再次使用以查询订单的交易状态；

服务端校验收据代码示例

```
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
```

```
@app.route('/iap/verifyReceipt', methods=['POST'])
def iap_verify_receipt():
	"""
	校验收据接口
	"""
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
```

收据校验结果示例：

```
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
```
服务端完整 Python 代码地址：[Github地址](https://github.com/coderWPJ/Awesome/blob/master/IAP_Server.py)

### 四. 疑问
#### 4.1 漏单问题：
>漏单：用户已经支付了，但是未发放商品。
>
>分析可能出现漏单的情形：1.
>
>未完待续......

#### 4.2 用户付款后，自己联系 Apple 进行退款，要如何监测以停止授权（如停止其使用相关特权功能，或扣除金币等操作等）：
>待补充

#### 4.3 自动续期订阅的用户退订问题：
>Apple 服务器间通知

#### 4.4 自动续期订阅用户续订问题：
>订阅用户的续订问题，即是否在用户的一个订阅周期结束后，继续为用户发放下一周期的权限，而发放权限的则是依据用户的下一周期的支付结果。
>
>自动扣款时机：Apple 会在订阅到期之前的24小时内发起扣款，如果扣款失败，Apple 可能会进行长达60天的尝试，可通过收据中的 is_in_billing_retry_period 获得此状态，若为 false 标识 Apple 放弃扣款。
>

状态变更通知可收到如下状态变更（无续费支付成功、扣款失败导致过期通知）：
<table>
<thead>
<tr>
<th>NOTIFICATION_TYPE</th>
<th>描述</th>
</tr>
</thead>
<tbody>
<tr>
<td>INITIAL_BUY</td>
<td>首次订阅</td>
</tr>
<tr>
<td>CANCEL</td>
<td>Apple客户支持取消了订阅，或已联系 Apple 退款成功。检查Cancellation Date以了解订阅取消的日期和时间。</td>
</tr>
<tr>
<td>RENEWAL</td>
<td>扣款失败导致过期，但后续又扣款成功。检查Subscription Expiration Date以确定下一个续订日期和时间。</td>
</tr>
<tr>
<td>INTERACTIVE_RENEWAL</td>
<td>客户主动恢复订阅。</td>
</tr>
<tr>
<td>DID_CHANGE_RENEWAL_PREF</td>
<td>客户更改了在下次续订时生效的计划。当前的有效计划不受影响。</td>
</tr>
</tbody>
</table>
用户的支付结果主要有如下状态：

1. Apple 正常扣款 (Server轮询获取或客户端接收到扣款成功通知后);
- Apple 扣款失败（如：用户在 Apple ID 中移除了可用的付款方式，或绑定的付款账户余额不足等）;
- 用户不再订阅（权限使用期限在此订阅周期结束后停止）;
- 退款（可立刻停止发放其权限）.

状态获取目前已知有如下方式：

1. Server 通过收据校验接口查询；
2. 状态变更通知通知，详情请参考[Apple 服务器间通知](https://developer.apple.com/documentation/storekit/in-app_purchase/subscriptions_and_offers/enabling_server-to-server_notifications)

综上，IAP 自动续费处理方案：

1. 服务端可在当前订阅结束前一天内开始，轮询调用收据校验接口查询扣款状态，检测到扣款成功则停止<font color='#FF00'> （若已接收到用户退款、退订的则不需要）</font > ；
2. 客户端生命周期内始终开启 IAP 交易结果监听，在收到交易状态为 Restored（扣款成功） 时提交至后台检验；
3. 客户端每次查看用户特权状态（或用户信息）时，在所调用的接口逻辑触发校验
4. 服务端在收到状态变更通知后，更新对应用户特权状态。


Note：

- 对于续费成功的收据校验接口，可不提供用户信息（如userID），因为装有此App的 Apple 账户当前登录的手机可能登录的是其他用户的账号；
- 服务端自己处理一个 App 用户，同一时间段对于一款自动续费订阅产品只能购买一次的逻辑 (只需不能创建多个订单供客户端调用支付即可)，因为Apple 账户是支持多次购买。



## 参考

1. [Apple 内购](https://developer.apple.com/cn/documentation/storekit/in-app_purchase/)
2. [Apple 收据校验](https://developer.apple.com/documentation/storekit/in-app_purchase/validating_receipts_with_the_app_store)
3. [Apple 服务器间通知](https://developer.apple.com/documentation/storekit/in-app_purchase/subscriptions_and_offers/enabling_server-to-server_notifications)。可用于处理自动续期订阅的取消订阅等逻辑
