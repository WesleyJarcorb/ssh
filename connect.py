import paramiko
from sshtunnel import SSHTunnelForwarder
import pandas as pd
import requests
import re
import time
import warnings
from multiprocessing import Process
warnings.filterwarnings("ignore")


# 字典：{dut编号：[监控室装置ip，[控制柜装置端口号]]}
name1 = {'54043846': ['', [9, 3, 10, 6, 5, 2, 4, 8, 7, 11, 12]]}     # 同济大学
name2 = {'54041654': ['', [5, 16, 3, 20, 8, 18, 4, 6, 1, 19, 2]]}    # 马桥万达
name3 = {'54040085': ['', [1, 78, 77, 76, 66, 65, 80, 79, 81, 82, 68, 67, 73, 72, 75, 74, 69, 4, 71, 70, 63, 64, 61,
                           62, 59, 60, 57, 58, 6, 7]]}               # 杨浦湾谷
name4 = {'54041375': ['', [6]]}  # 技术中心
name5 = {'54040004': ['', [1]]}  # 南方商城
name6 = {'54041304': ['', [4]]}  # 汇银广场


dtu_dict = {
    '同济大学': name1,
    '马桥万达': name2,
    '杨浦湾谷': name3,
    '技术中心': name4,
    '南方商城': name5,
    '汇银广场': name6
}


# 查询dtu对应ip地址
def dtu_web_init():
    s1 = requests.session()
    url_login1 = "http://192.9.250.190:8080/slnms_all/logins/login.action"
    data_login1 = {"parameter['username']": 'u3639', "parameter['password']": 'u3639', 'x': 28, 'y': 17}
    r_login1 = s1.post(url_login1, data=data_login1, timeout=10)
    return s1


def get_dtu_ip(dtuno, s):
    r = s.get(
        "http://192.9.250.190:8080/slnms_all/device/deviceAction-statePage.action?isStatSearch=0&unicode=%d" % int(
            dtuno))
    ip = ''
    if 'PPPIP' in r.text:
        m = re.findall('name="PPPIP" value="(.*?)"', r.text)
        ip = m[0]

    return ip


def run(pro, name):
    ip = list(name.values())[0][0]  # 取出监控室装置ip
    port_list = list(name.values())[0][1]  # 取出控制柜装置端口列表
    total_num = len(port_list)
    seq = 0
    for port in port_list:
        seq += 1
        try:
            with SSHTunnelForwarder(
                    (ip, 22),  # 跳板机（监控室装置）ip地址，端口号：22
                    ssh_username='root',  # 跳板机（监控室装置）用户名
                    ssh_password='Smec3030',  # 跳板机（监控室装置）密码
                    remote_bind_address=('3.3.3.' + str(port), 22),  # 远程服务器（控制柜装置）ip，端口号
                    remote_bind_addresses=(),
                    local_bind_address=('127.0.0.1', 22)  # 客户端（自己本机）ip，端口号
            ) as server:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
                client.connect('127.0.0.1', 22, 'root', 'Smec3030')  # 客户端（自己本机）ip，端口号；远程服务器（控制柜装置）用户名、密码
                stdin, stdout, stderr = client.exec_command('ping 192.168.4.5 -w 2')
                result = stdout.read().decode()  # ping 命令执行结果
                if "time=" not in result:
                    print("[%s total_num:%2d  seq:%2d port:%2d] ping vib_sensor --> comm failed! \n" % (pro, total_num, seq, port))
                else:
                    out = result.split()[20]  # 取第二次ping包的time用时
                    timeout = float(out[5:])
                    if 0 < timeout < 100:
                        print("[%s total_num:%2d  seq:%2d port:%2d] ping vib_sensor %12s ms --> comm succeed! \n" % (pro, total_num, seq, port, out))
                client.close()
        except:
            print("[%s ip:%s total_num:%2d  seq:%d port:%2d] ssh connected failed! \n" % (pro, ip, total_num, seq, port))


if __name__ == '__main__':

    start = time.clock()
    s = dtu_web_init()                           # 登录网址查询dtu对应监控室ip地址

    for prj, name in dtu_dict.items():
        dtuno = list(name.keys())                # 取出dtu编号
        ip = get_dtu_ip(dtuno[0], s)             # 根据dtu编号，查询监控室装置ip
        list(dtu_dict[prj].values())[0][0] = ip  # 填充dtu_dict的ip

    print(dtu_dict)

    na = []
    for pro, name in dtu_dict.items():
        p = Process(target=run, args=(pro, name, ))
        na.append(p)

    # for i in na:
    #     i.start()
    na[2].start()

    end = time.clock()
    print('Running time: %s Seconds' % (end - start))
