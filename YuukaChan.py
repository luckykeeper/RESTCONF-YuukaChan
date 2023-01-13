# Huawei USG Series RESTCONF Operator YuukaChan
# Powered By Luckykeeper <luckykeeper@luckykeeper.site | https://luckykeeper.site>

# basic
import time

#  CLI
import argparse

# EXCEL reader
import xlrd

# SSL / req
import ssl
import requests
from requests.adapters import HTTPAdapter, PoolManager
from requests.auth import HTTPBasicAuth
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

class MyAdapter(HTTPAdapter):
    # 重写init_poolmanager方法，使用tls1.2。
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       ssl_version=ssl.PROTOCOL_TLSv1_2)

# XML 内纯文本
def getText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

# 业务流程
def HayaseYuuka(debugYuuka):
    # XML Handler
    import xml.dom.minidom

    global interfacesInfo
    interfacesInfo = {}

    if debugYuuka:
        print("Debug 标记：", debugYuuka, "，以调试环境模式启动")
    else:
        # Debug
        print("Debug 标记：", debugYuuka, "，以生产环境模式启动")

    # 读取 EXCEL 基本信息表
    YuukaBook = xlrd.open_workbook('./YuukaChan.xls')
    if debugYuuka:
        print("xls文件加载状态：",YuukaBook.sheet_loaded(0))
        print("Sheet列表：",YuukaBook.sheet_names())
    basicInfoSheet = YuukaBook.sheet_by_name('设备信息')
    NATServerSheet = YuukaBook.sheet_by_name('基于接口IP的NATServer端口映射表')

    # 定时执行任务
    while True:
        try:
            # 获取基本信息
            # 行、列数均从 0 开始计
            YuukaDeviceIp=str(basicInfoSheet.row(4)[1].value)
            YuukaDeviceRestConfPort=str(basicInfoSheet.row_values(4)[2])
            YuukaDeviceApiAccount=str(basicInfoSheet.row_values(4)[3])
            YuukaDeviceApiPassword=str(basicInfoSheet.row_values(4)[4])
            YuukaDeviceCommProto=str(basicInfoSheet.row_values(4)[5])
            YuukaDeviceTlsProto=str(basicInfoSheet.row_values(4)[6])
            YuukaDeviceWANPorts=str(basicInfoSheet.row_values(4)[7])
            HayaseYuukaSleepTime=str(basicInfoSheet.row_values(4)[8])

            # 解析出接口名称
            YuukaDeviceWANPortList=YuukaDeviceWANPorts.split(",")

            if debugYuuka:
                print("设备信息")
                print("设备IP：",YuukaDeviceIp)
                print("RESTCONF端口号：",YuukaDeviceRestConfPort)
                print("API账户名：",YuukaDeviceApiAccount)
                print("API账户密码：",YuukaDeviceApiPassword)
                print("协议：",YuukaDeviceCommProto)
                print("tls版本：",YuukaDeviceTlsProto)
                print("出接口名称列表：",YuukaDeviceWANPortList)
                print("优香酱休息时间：",HayaseYuukaSleepTime,"分")

            # 请求接口信息
            # 构造设备 url
            YuukaDeviceUrl = "https://"+YuukaDeviceIp+":"+YuukaDeviceRestConfPort

            # 获取 interface 状态 RESTCONF
            YuukaDeviceInterfaceBaseUrl = "/restconf/data/ietf-interfaces:interfaces"

            YuukaDeviceInterfaceUrl=YuukaDeviceUrl+YuukaDeviceInterfaceBaseUrl

            YuukaDeviceRequestHeader = {  
                'Host': YuukaDeviceIp+":"+YuukaDeviceRestConfPort,  
                'Accept': '*/*'  
            }
            
            disable_warnings(InsecureRequestWarning) 

            # 定义登录账户密码
            YuukaDeviceBasicAuth = HTTPBasicAuth(YuukaDeviceApiAccount, YuukaDeviceApiPassword)  
            s = requests.Session()  

            # 获取 interface 信息
            # 调用重写的方法
            s.mount('https://', MyAdapter())  

            r = s.get(url=YuukaDeviceInterfaceUrl, headers=YuukaDeviceRequestHeader, auth=YuukaDeviceBasicAuth, verify=False)  

            if r.status_code!=200:
                # print('【USG RESTCONF 接口信息查询】信息失败')
                raise SystemExit('【USG RESTCONF 接口信息查询】信息失败:',r.status_code,r.text)

            if debugYuuka:
                # print(r.request.headers)
                print("【USG RESTCONF 接口信息查询】请求结果：200 OK！")
                # print(r.text)
            s.close()

            # 使用minidom解析器打开 XML 文档
            DOMTree = xml.dom.minidom.parseString(r.text)
            collection = DOMTree.documentElement

            interfaces = collection.getElementsByTagName("interface")

            for interface in interfaces:
                # if debugYuuka:
                #     print("正在解析的接口名称：",getText(interface.getElementsByTagName('name')[0].childNodes))
                
                interfaceName = getText(interface.getElementsByTagName('name')[0].childNodes)
                if interfaceName in YuukaDeviceWANPortList:
                    interfaceStatus=getText(interface.getElementsByTagName('enabled')[0].childNodes)

                    v4Info = interface.getElementsByTagName('ip:ipv4')
                    # IPV6 不需要端口映射
                    # v6Info = interface.getElementsByTagName('ip:ipv6')

                    # v4 缺省地址：8.8.8.8
                    v4Address="8.8.8.8"
                    # 需要判断是否有数据再进行操作
                    if len(v4Info)>0:
                        v4AddressList = v4Info[0].getElementsByTagName('ip:ip')
                        if len(v4AddressList)>0:
                            v4Address = v4AddressList[0].firstChild.data

                    # v6Address=""
                    # if len(v6Info)>0:
                    #     v6AddressList = v6Info[0].getElementsByTagName('ip:ip')
                    #     if len(v6AddressList)>0:
                    #         v6Address = v6AddressList[0].firstChild.data

                    if debugYuuka:
                        print("*****interface!*****")
                        print("接口名称：",interfaceName)
                        print("接口状态：",interfaceStatus)
                        if v4Address=="8.8.8.8":
                            print("IPV4：",v4Address,"(未获取到IPV4地址，使用缺省地址 8.8.8.8 占位)")
                        else:
                            print("IPV4：",v4Address)
                        # print("IPV6：",v6Address)
                        print("*****interface!*****")

                    # 写入接口数据
                    interfacesInfo[interfaceName]=v4Address

                    if debugYuuka:
                        print("接口的交换数据信息：",interfacesInfo)

            # 获取基于接口 IP 的 NAT Server 端口映射表设置
            YuukaNatServersSettings={}

            NATServerSheetTotalColCount=NATServerSheet.nrows-4

            for i in range(0,NATServerSheetTotalColCount):
                YuukaPolicyName=str(NATServerSheet.row(4+i)[1].value)
                YuukaDeviceVsysName=str(NATServerSheet.row_values(4+i)[2])
                YuukaServerIPv4=str(NATServerSheet.row_values(4+i)[3])
                YuukaServerProtocol=str(NATServerSheet.row_values(4+i)[4])
                YuukaServerOutBoundInterface=str(NATServerSheet.row_values(4+i)[5])
                YuukaPortIsContinuous=bool(NATServerSheet.row_values(4+i)[10])

                # 连续端口处理
                if YuukaPortIsContinuous:
                    YuukaWANPortStart=str(NATServerSheet.row_values(4+i)[6])
                    YuukaWANPortEnd=str(NATServerSheet.row_values(4+i)[7])
                    YuukaServerPortStart=str(NATServerSheet.row_values(4+i)[8])
                    YuukaServerPortEnd=str(NATServerSheet.row_values(4+i)[9])
                else:
                    YuukaWANPortStart=str(NATServerSheet.row_values(4+i)[6])
                    YuukaServerPortStart=str(NATServerSheet.row_values(4+i)[8])

                    YuukaWANPortEnd=""
                    YuukaServerPortEnd=""

                YuukaServerNorev=str(NATServerSheet.row_values(4+i)[11])

                if debugYuuka:
                    print("基于接口IP的NATServer端口映射表")
                    print("策略名称：",YuukaPolicyName)
                    print("策略生效vsys名称：",YuukaDeviceVsysName)
                    print("服务器地址：",YuukaServerIPv4)
                    if YuukaServerProtocol == "6":
                        print("协议类型：TCP")
                    elif YuukaServerProtocol == "17":
                        print("协议类型：UDP")
                    else:
                        print("协议类型：",YuukaServerProtocol)

                    print("公网接口：",YuukaServerOutBoundInterface)

                    if YuukaPortIsContinuous:
                        print("公网起始端口：",YuukaWANPortStart)
                        print("公网结束端口：",YuukaWANPortEnd)
                        print("服务器起始接口：",YuukaServerPortStart)
                        print("服务器结束接口：",YuukaServerPortEnd)

                    else:
                        print("公网端口：",YuukaWANPortStart)
                        print("服务器接口：",YuukaServerPortStart)
                    print("禁止反向访问",YuukaServerNorev)

                YuukaNatServerSetting={}
                YuukaNatServerSetting["YuukaDeviceVsysName"]=YuukaDeviceVsysName
                YuukaNatServerSetting["YuukaServerIPv4"]=YuukaServerIPv4
                YuukaNatServerSetting["YuukaServerProtocol"]=YuukaServerProtocol
                YuukaNatServerSetting["YuukaServerOutBoundInterface"]=YuukaServerOutBoundInterface
                YuukaNatServerSetting["YuukaPortIsContinuous"]=YuukaPortIsContinuous
                YuukaNatServerSetting["YuukaWANPortStart"]=YuukaWANPortStart
                YuukaNatServerSetting["YuukaWANPortEnd"]=YuukaWANPortEnd
                YuukaNatServerSetting["YuukaServerPortStart"]=YuukaServerPortStart
                YuukaNatServerSetting["YuukaServerPortEnd"]=YuukaServerPortEnd
                YuukaNatServerSetting["YuukaServerNorev"]=YuukaServerNorev
                YuukaNatServerSetting["needCreate"]=True

                YuukaNatServersSettings[YuukaPolicyName]=YuukaNatServerSetting

            if debugYuuka:
                print("基于接口 IP 的 NAT Server 端口映射表设置交换信息：",YuukaNatServersSettings)



            # 查询、比对 NAT 映射信息
            YuukaDeviceNatServerInfoBaseUrl = "/restconf/data/huawei-nat-server:nat-server"
            YuukaDeviceNatServerInfoUrl = YuukaDeviceUrl+YuukaDeviceNatServerInfoBaseUrl

            s = requests.Session()  

            # 获取 NAT Server 映射信息
            # 调用重写的方法
            s.mount('https://', MyAdapter())  

            r = s.get(url=YuukaDeviceNatServerInfoUrl, headers=YuukaDeviceRequestHeader, auth=YuukaDeviceBasicAuth, verify=False)  

            if r.status_code!=200:
                # print('【USG RESTCONF NAT Server 映射查询】信息失败')
                raise SystemExit('【USG RESTCONF NAT Server 映射查询】信息失败:',r.status_code,r.text)

            if debugYuuka:
                # print(r.request.headers)
                print("【USG RESTCONF NAT Server 映射查询】请求结果：200 OK！")
                # print(r.text)
            s.close()

            # 使用minidom解析器打开 XML 文档
            DOMTree = xml.dom.minidom.parseString(r.text)
            collection = DOMTree.documentElement

            serverMappings = collection.getElementsByTagName("server-mapping")

            # 初始化需要更新的策略
            policyNeedModify=[]

            for serverMapping in serverMappings:
                # if debugYuuka:
                #     print("正在解析的服务器映射名称：",getText(serverMapping.getElementsByTagName('name')[0].childNodes))
                if getText(serverMapping.getElementsByTagName('name')[0].childNodes) in YuukaNatServersSettings:
                    YuukaNatServersSettings[getText(serverMapping.getElementsByTagName('name')[0].childNodes)]["needCreate"]=False
                    serverMappingName = getText(serverMapping.getElementsByTagName('name')[0].childNodes)
                    serverMappingVsys = getText(serverMapping.getElementsByTagName('vsys')[0].childNodes)
                    serverMappingProtocol = getText(serverMapping.getElementsByTagName('protocol')[0].childNodes)
                    serverMappingNorev = getText(serverMapping.getElementsByTagName('no-reverse')[0].childNodes)
                
                    # 预定义数据
                    WANIPv4Data="" 
                    WANPortStartData=""
                    WANPortEndData=""
                    ServerIPv4Data=""
                    ServerPortStartData=""
                    ServerPortEndData=""

                    # 不能直接获取的
                    WANInfo = serverMapping.getElementsByTagName('global')
                    WANPort = serverMapping.getElementsByTagName('global-port')
                    ServerInfo = serverMapping.getElementsByTagName('inside')
                    ServerPort = serverMapping.getElementsByTagName('inside-port')

                    if len(WANInfo)>0:
                        WANIPv4 = WANInfo[0].getElementsByTagName('start-ip')
                        if len(WANIPv4)>0:
                                WANIPv4Data = WANIPv4[0].firstChild.data

                    # if len(v4Info)>0:
                    #     v4AddressList = v4Info[0].getElementsByTagName('ip:ip')
                    #     if len(v4AddressList)>0:
                    #         v4Address = v4AddressList[0].firstChild.data

                    if len(WANPort)>0:
                        WANPortStart = WANPort[0].getElementsByTagName('start-port')
                        WANPortEnd = WANPort[0].getElementsByTagName('end-port')
                        if len(WANPortStart)>0:
                                WANPortStartData = WANPortStart[0].firstChild.data
                        if len(WANPortEnd)>0:
                                WANPortEndData = WANPortEnd[0].firstChild.data

                    if len(ServerInfo)>0:
                        ServerIPv4 = ServerInfo[0].getElementsByTagName('start-ip')
                        if len(WANPortStart)>0:
                                ServerIPv4Data = ServerIPv4[0].firstChild.data

                    if len(ServerPort)>0:
                        ServerPortStart = ServerPort[0].getElementsByTagName('start-port')
                        ServerPortEnd = ServerPort[0].getElementsByTagName('end-port')
                        if len(ServerPortStart)>0:
                            ServerPortStartData = ServerPortStart[0].firstChild.data
                        if len(ServerPortEnd)>0:
                            ServerPortEndData = ServerPortEnd[0].firstChild.data

                    # 判断指定名称策略与用户想要设定的各参数是否相同
                    if YuukaNatServersSettings[serverMappingName]["YuukaDeviceVsysName"]==serverMappingVsys \
                        and YuukaNatServersSettings[serverMappingName]["YuukaServerIPv4"]==ServerIPv4Data \
                        and YuukaNatServersSettings[serverMappingName]["YuukaServerProtocol"]==serverMappingProtocol \
                        and YuukaNatServersSettings[serverMappingName]["YuukaWANPortStart"]==WANPortStartData \
                        and YuukaNatServersSettings[serverMappingName]["YuukaServerPortStart"]==ServerPortStartData \
                        and YuukaNatServersSettings[serverMappingName]["YuukaServerNorev"]==serverMappingNorev\
                        and interfacesInfo[YuukaNatServersSettings[serverMappingName]["YuukaServerOutBoundInterface"]]==WANIPv4Data: # 其它参数都相同，还需要检查公网IP的情况
                        if YuukaNatServersSettings[serverMappingName]["YuukaPortIsContinuous"]:
                            if YuukaNatServersSettings[serverMappingName]["YuukaWANPortEnd"]!=WANPortEndData \
                                or YuukaNatServersSettings[serverMappingName]["YuukaServerPortEnd"]!=ServerPortEndData:
                                    if debugYuuka:
                                        print("*****NAT Server Need Update Info!*****")
                                        print("策略名称：",serverMappingName)
                                        print("所在vsys：",serverMappingVsys)
                                        print("使用协议：",serverMappingProtocol)
                                        print("公网地址：",WANIPv4Data)
                                        print("公网开始端口：",WANPortStartData)
                                        print("公网结束端口：",WANPortEndData)
                                        print("服务器地址：",ServerIPv4Data)
                                        print("服务器开始端口：",ServerPortStartData)
                                        print("服务器结束端口：",ServerPortEndData)
                                        print("不允许服务器使用公网地址上网（反向访问）：",serverMappingNorev)
                                        print("*****NAT Server Need Update Info!*****")
                                    policyNeedModify.append(serverMappingName)

                    else:
                        if debugYuuka:
                            print("*****NAT Server Need Update Info!*****")
                            print("策略名称：",serverMappingName)
                            print("所在vsys：",serverMappingVsys)
                            print("使用协议：",serverMappingProtocol)
                            print("公网地址：",WANIPv4Data)
                            print("公网开始端口：",WANPortStartData)
                            print("公网结束端口：",WANPortEndData)
                            print("服务器地址：",ServerIPv4Data)
                            print("服务器开始端口：",ServerPortStartData)
                            print("服务器结束端口：",ServerPortEndData)
                            print("不允许服务器使用公网地址上网（反向访问）：",serverMappingNorev)
                            print("*****NAT Server Need Update Info!*****")

                        policyNeedModify.append(serverMappingName)

            # 获取需要新建的策略
            for key,values in YuukaNatServersSettings.items():
                currentPolicyName=key
                values=dict(values)
                if values.get('needCreate'):
                    policyNeedModify.append(currentPolicyName)
            
            if debugYuuka:
                print("需要新建/修改的策略：",policyNeedModify)

            if len(policyNeedModify)>0:
                # 新建/修改 RESTCONF 基础地址
                YuukaDeviceModifyNatServerBaseUrl = "/restconf/data/huawei-nat-server:nat-server/server-mapping="
                for policy in policyNeedModify:
                    # 执行新建/修改 NAT 映射信息
                    YuukaDeviceModifyNatServerUrl = YuukaDeviceUrl+YuukaDeviceModifyNatServerBaseUrl+policy+","+YuukaNatServersSettings[policy]["YuukaDeviceVsysName"]

                    # 根据是否连续开放端口号构造内外映射 ”IP-端口“ 部分 Payload
                    if YuukaNatServersSettings[policy]["YuukaPortIsContinuous"]:
                        YuukaNatServerAndPortInPayLoad="\
                        <global>\
                            <start-ip>"+interfacesInfo[YuukaNatServersSettings[policy]["YuukaServerOutBoundInterface"]]+"</start-ip>\
                        </global>\
                        <global-port>\
                            <start-port>"+YuukaNatServersSettings[policy]["YuukaWANPortStart"]+"</start-port>\
                            <end-port>"+YuukaNatServersSettings[policy]["YuukaWANPortEnd"]+"</end-port>\
                        </global-port>\
                        <inside>\
                        <start-ip>"+YuukaNatServersSettings[policy]["YuukaServerIPv4"]+"</start-ip>\
                        </inside>\
                        <inside-port>\
                            <start-port>"+YuukaNatServersSettings[policy]["YuukaServerPortStart"]+"</start-port>\
                            <end-port>"+YuukaNatServersSettings[policy]["YuukaServerPortEnd"]+"</end-port>\
                        </inside-port>\
                        "

                    else:
                        YuukaNatServerAndPortInPayLoad="\
                        <global>\
                            <start-ip>"+interfacesInfo[YuukaNatServersSettings[policy]["YuukaServerOutBoundInterface"]]+"</start-ip>\
                        </global>\
                        <global-port>\
                            <start-port>"+YuukaNatServersSettings[policy]["YuukaWANPortStart"]+"</start-port>\
                        </global-port>\
                        <inside>\
                        <start-ip>"+YuukaNatServersSettings[policy]["YuukaServerIPv4"]+"</start-ip>\
                        </inside>\
                        <inside-port>\
                            <start-port>"+YuukaNatServersSettings[policy]["YuukaServerPortStart"]+"</start-port>\
                        </inside-port>\
                        "

                    # 构造 Payload 整体
                    YuukaPayload="\
                    <server-mapping>\
                        <name>"+policy+"</name>\
                        <vsys>"+YuukaNatServersSettings[policy]["YuukaDeviceVsysName"]+"</vsys>\
                        <protocol>"+YuukaNatServersSettings[policy]["YuukaServerProtocol"]+"</protocol>"\
                        +YuukaNatServerAndPortInPayLoad+\
                        "<no-reverse>"+YuukaNatServersSettings[policy]["YuukaServerNorev"]+"</no-reverse>\
                    </server-mapping>\
                    "

                    if debugYuuka:
                        print("当前执行策略：",policy)
                        print("将被 PUT 的 URL：",YuukaDeviceModifyNatServerUrl)
                        print("构造的 Payload：",YuukaPayload)


                    s = requests.Session()  

                    # 获取 NAT Server 映射信息
                    # 调用重写的方法
                    s.mount('https://', MyAdapter())  

                    r = s.put(url=YuukaDeviceModifyNatServerUrl,data=YuukaPayload, headers=YuukaDeviceRequestHeader, auth=YuukaDeviceBasicAuth, verify=False)  

                    if r.status_code!=200 and r.status_code!=204 :
                        # print('【USG RESTCONF NAT Server 新建/修改",policy,"】执行失败:',r.status_code)
                        raise SystemExit("【USG RESTCONF NAT Server 新建/修改策略：",policy,"】执行失败:",r.status_code,r.text)

                    if debugYuuka:
                        # print(r.request.headers)
                        print("【USG RESTCONF NAT Server 新建/修改策略：",policy,"】请求结果：204 Not Content（成功）！")
                        # print(r.text)
                    s.close()

                # 设置被修改，需要执行一次保存
                YuukaDeviceSaveConfigBaseUrl = "/restconf/operations/huawei-system:save"
                YuukaDeviceSaveConfigUrl=YuukaDeviceUrl+YuukaDeviceSaveConfigBaseUrl

                SaveYuukaConig="<save><save></save></save>"

                s = requests.Session()  

                # 调用重写的方法
                s.mount('https://', MyAdapter())  

                r = s.post(url=YuukaDeviceSaveConfigUrl,data=SaveYuukaConig, headers=YuukaDeviceRequestHeader, auth=YuukaDeviceBasicAuth, verify=False)  

                if r.status_code!=200 and r.status_code!=204 :
                    raise SystemExit("【USG RESTCONF 保存设备当前设置】执行失败:",r.status_code,r.text)

                if debugYuuka:
                    # print(r.request.headers)
                    print("【USG RESTCONF 保存设备当前设置】请求结果：204 Not Content（成功）！")
                    # print(r.text)

            else:
                print("没有需要新建/修改的 NAT Server 策略~")


            nowTime = time.asctime( time.localtime(time.time()) )
            print ("当前时间 :", nowTime,"本周期任务运行顺利结束！")
            print ("————————————————————————————————————————")
            time.sleep(int(HayaseYuukaSleepTime)*60)
        except:
            print("如果需要退出程序，请再次按下 Ctrl+C ")
            print("程序出错，可能是 USG 连接失败，等待 120 秒后重试")
            time.sleep(120)
            print("开始重试")

# # 获取基础信息示例
# def queryBasicInfo():
    
#     # 查询健康检测的状态
#     url = 'ip:port/restconf/data/ietf-interfaces:interfaces'
#     header = {  
#        'Host': 'ip:port',  
#         'Accept': '*/*'  
#     }

#     disable_warnings(InsecureRequestWarning) 

#     # 定义登录账户密码
#     basic = HTTPBasicAuth('apiUserName', 'apiPassword')  
#     s = requests.Session()  

#     # 调用重写的方法
#     s.mount('https://', MyAdapter())  

#     r = s.get(url=url, headers=header, auth=basic, verify=False)  

#     print(r.request.headers)  
#     print(r.status_code)  
#     print(r.text)  
#     s.close()

# CLI
def cli():
    parser = argparse.ArgumentParser(description="RESTCONF@YuukaChan ——"+
            " 让可爱的优香酱使用北向接口管理 USG 系列设备")
    subparsers = parser.add_subparsers(metavar='subCommand')

    # 启动服务（生产环境）
    runProd_parser = subparsers.add_parser('runProd', help='启动服务（生产环境）')
    runProd_parser.set_defaults(handle=handle_runProd)
    # 启动服务（调试环境）
    runDebug_parser = subparsers.add_parser('runDebug', help='启动服务（调试环境）')
    runDebug_parser.set_defaults(handle=handle_runDebug)
    # # 调试功能
    # debug_parser = subparsers.add_parser('info', help='编程中调试功能')
    # debug_parser.set_defaults(handle=handle_info)
    # 解析命令
    args = parser.parse_args()
    # 1.第一个命令会解析成handle，使用args.handle()就能够调用
    if hasattr(args, 'handle'):
        args.handle(args)
    # 2.如果没有handle属性，则表示未输入子命令，则打印帮助信息
    else:
        parser.print_help()

def handle_runProd(args):
    HayaseYuuka(False)

def handle_runDebug(args):
    HayaseYuuka(True)

# def handle_info(args):
#     queryBasicInfo()

if __name__ == '__main__':
    print("欢迎使用优香酱华为 USG 系列设备北向管理小工具~")
    print("目前支持功能：【NAT Server 根据接口 IP 动态配置服务器映射列表设置】")
    print("Powered By Luckykeeper <luckykeeper@luckykeeper.site | https://luckykeeper.site>")
    print("RESTCONF@YuukaChan Ver1.0.0_20230113")
    print("HayaseYuuka：“如我所算，完美~♪”")
    print("————————————————————————————————————————")
    print("————————⚠警告信息⚠————————")
    print("注意调用本工具会对设备上的当前设定信息做保存(save)操作！！！")
    print("如果你不希望保存当前设定信息，请立刻多次按下“Ctrl+C”取消运行！！！")
    print("小工具将在 5s 后开始运行！！！")
    print("————————⚠警告信息⚠————————")
    time.sleep(5)

    cli()