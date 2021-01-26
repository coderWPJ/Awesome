
# 苹果设备间近场+局域网通讯实践(ZYRemote核心技术).md

## 前言
> 公司项目 ZYRemote App 其中一个需求是接收来自 ZYCami App 内相机采集到的 CVPixelBufferRef，以此相关联需要实现的功能有：设备扫描、连接、指令交互以及实时图像传输等。目前市场上有此业务需求（通过近场通讯或局域网来实现实时视频传输）的 App 不算常见。经过一番探索与总结，结合苹果自带框架 MultipeerConnectivity （类似于 Wi-Fi Direct 标准，后面简称 multiPeer），最终实现了一套兼容 multiPeer 与UDP协议的方案。

## 1. UI交互流程 
简述：remote打开扫描页面，cami打开设备共享开关，在remote中选中欲连接的设备，cami同意即连接成功，可以开始图传、或其他指令传输。

## 2. 关键词解释

### 2.1 UDP 广播/组播：(注：UDP支持广播/组播，TCP不支持) </br>
 
> 广播: 向子网内所有主机发送数据</br>
> 多播: 向加入多播群组的设备发送数据

### 2.2 视频编解码： 
略

### 2.3 UDP 分包/组包：
略

### 2.4 MultipeerConnectivity
> The Multipeer Connectivity framework supports the discovery of services provided by nearby devices and supports communicating with those services through message-based data, streaming data, and resources (such as files). In iOS, the framework uses infrastructure Wi-Fi networks, peer-to-peer Wi-Fi, and Bluetooth personal area networks for the underlying transport. In macOS and tvOS, it uses infrastructure Wi-Fi, peer-to-peer Wi-Fi, and Ethernet.  

来源：[苹果官方](https://developer.apple.com/documentation/multipeerconnectivity)

## 3. UDP 与 multiPeer比较
- 基于 UDP 协议实现的扫描、连接、通讯都是基于局域网内的，在无网环境下需要自建网络来建立通讯；
- multiPeer 仅需要通讯双方均打开 Wi-Fi 开关且允许访问本地网络（iOS 14 才有）；

### 3.1 发现：
- UDP: ZYCami 在打开共享期间定时发送组播/广播（未连接时），ZYRemote定时接收组播/广播（未连接时）
- multiPeer：ZYCami 启动 advertiser 进行设备广播，ZYRemote 在进入扫描页面后用 browser 开启扫描advertiser
- iOS 设备中，在同时开启UDP与multiPeer后，multiPeer接收快于UDP，且能通过UDP收到设备源时可正常收到multiPeer，可用设备UUID来选择性保留某一方。

### 3.2 连接：
- UDP: 2步连接，remote 端发送一条连接指令至 cami 端，cami端根据用户的选择返回同意连接或拒绝连接的指令
- multiPeer：框架支持略
- 对于通过 multiPeer 扫描到的设备，若设备处于同一局域网环境内，则无需通过 UDP 搜索到设备（multiPeer搜索快于）亦可通过UDP连接。

### 3.3 传输：
- 采用 UDP 传输
- multiPeer：采用框架支持的字节流或者以二进制数据形式传输
## 4. 结构
> ZYPeersNetworkInspector &nbsp;&nbsp; 监察器处理消息收发队列
>
> ZYPeersStation &nbsp;&nbsp;&nbsp;&nbsp; 核心，供外部调用，处理扫描、连接、数据传输等所有逻辑
>
> ZYPeersStationDelegate&nbsp;&nbsp;&nbsp;&nbsp;station专用代理，用途：回调扫描、连接、数据收发、协议封装&解析等
>
> Encoder&Decoder &nbsp;&nbsp;&nbsp;&nbsp; 编解码
>>
>> ZYPeersVideoDecoder  &nbsp;&nbsp;&nbsp;&nbsp; 编码
>>
>> ZYPeersVideoEncoder  &nbsp;&nbsp;&nbsp;&nbsp; 解码
>
> Model  &nbsp;&nbsp;&nbsp;&nbsp; 模型
>>
>> ZYPeersBufferPacket &nbsp;&nbsp;&nbsp;&nbsp; 自定义协议类（已废弃）
>>
>> ZYPeersDevice  &nbsp;&nbsp;&nbsp;&nbsp; 设备抽象类
>>
>> ZYPeersRTTransMonitorParamSet  &nbsp;&nbsp;&nbsp;&nbsp; 性能监测，用于实时反应传输的包编号、大小、视频传输帧数等
>>
>> ZYPeersVideoEncodePreset  &nbsp;&nbsp;&nbsp;&nbsp; 编码预设类
>
> Transceiver  &nbsp;&nbsp;&nbsp;&nbsp; 数据收发
>> 
>> UDP 
>>> ZYPeersUDPSocket
>> 
>> MultiPeer 
>>> ZYPeersMultiConnectivity

## 5. 交互流程

### 5.1 扫描+连接

### 5.2 指令

### 5.3 图传

## 6. Q&A

### 6.1 需要同时打开 Wi-Fi 和蓝牙么？
结论：Wi-Fi 必须打开，蓝牙可以不打开。</br>
对于蓝牙，从2.4 MultipeerConnectivity 中可知苹果官方文档提到iOS设备间有用到蓝牙通讯方式，猜测用途，
### 6.2 双频路由器频段对 UDP 传输是否有影响，如连接在同一个路由下建立连接的双方一个使用2.4g频段，一个使用5g频段？
尚未实践，可能会造成无法扫描到，无法跨频段转发
### 6.3 udp 连接和 multipeer 如何选择？
- 连接双方均支持 multipeer 时，默认使用 multipeer 方式进行连接与传输，否则采用 UDP 方式进行连接与传输。
### 6.4 如何选择编解码（H264还是H265）？
- 连接双方均知道对方支持的编解码类型，根据性能和压缩比自动选择，暂未提供设置方法给上层
### 6.5 选择UDP不选择TCP的原因？
- TCP提供的是可靠连接，自带重传、拥塞控制、滑动窗口等特性并保证可靠交付，而图传需求对于实时性要求较高，可容忍部分丢包。
### 6.6 本地网络访问权限如何获取？
- 苹果官方暂无APi获取，可通过开启 NWBrowser 来获取转换状态是否为 ready 来判断，iOS14及以上系统才有授权弹窗。
