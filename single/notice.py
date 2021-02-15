import yagmail
from typing import TypeVar, List
import time
import json
import requests
import csv


def get_time_now(fmt: str = '%Y-%m-%d %H:%M:%S'):
    '''
    获取当前时间
    '''
    ts = int(time.time())
    ta = time.localtime(ts)
    now = time.strftime(fmt, ta)
    return now


def to_csv(fname: str, column: list, rows: list) -> bool:
    '''
    存储数据到 csv 文件里面
    '''
    with open(fname, 'w', encoding='utf-8-sig', newline="") as f:
        w = csv.writer(f)
        w.writerow(column)
        w.writerows(rows)
    return True


def get_increase(codes: TypeVar('List[str]|str', List[str], str)) -> List[dict]:
    '''
    调用天天基金估值API
    '''
    headers = {
        'User-Agent': 'EMProjJijin/6.2.8 (iPhone; iOS 13.6; Scale/2.00)',
        'GTOKEN': '98B423068C1F4DEF9842F82ADF08C5db',
        'clientInfo': 'ttjj-iPhone10,1-iOS-iOS13.6',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Host': 'fundmobapi.eastmoney.com',
        'Referer': 'https://mpservice.com/516939c37bdb4ba2b1138c50cf69a2e1/release/pages/FundHistoryNetWorth',
    }

    '''获取基金实时预期涨跌幅度'''
    if not isinstance(codes, list):
        codes = [codes]
    data = {
        'pageIndex': '1',
        'pageSize': '30000',
        'Sort': '',
        'Fcodes': ",".join(codes),
        'SortColumn': '',
        'IsShowSE': 'false',
        'P': 'F',
        'deviceid': '3EA024C2-7F22-408B-95E4-383D38160FB3',
        'plat': 'Iphone',
        'product': 'EFund',
        'version': '6.2.8',
    }

    json_response = requests.get(
        'https://fundmobapi.eastmoney.com/FundMNewApi/FundMNFInfo', headers=headers, data=data).json()
    data_list = json_response['Datas']

    columns = ['代码', '名称', '估算涨跌幅', '估算时间']
    rows = []
    for fund in data_list:
        # 基金代码
        code = fund['FCODE']
        # 基金名称
        name = fund['SHORTNAME']
        # 涨跌幅
        try:
            rate = float(fund['GSZZL'])
        except:
            rate = 0
        # 估算时间
        gztime = fund['GZTIME']
        row = [code, name, rate, gztime]
        temp = dict(zip(columns, row))
        rows.append(temp.copy())
    return rows


def send_email(usr: str, pwd: str, receiver: str, contents: list) -> bool:
    '''
    发送邮件
    '''
    yag = yagmail.SMTP(user=usr,
                       password=pwd,
                       host='smtp.qq.com')
    yag.send(receiver, '涨跌提醒', contents)
    return True


def to_break() -> bool:
    '''
    判断是否要终止程序
    '''
    ts = time.time()
    t = time.localtime(ts)

    tt = time.strftime("%H:%M:%S", t)
    dayofweek = t.tm_wday
    # 周六周日不交易
    if dayofweek > 4:
        return True
    # 处于交易时间段
    if "09:25:00" < tt < "15:00:00":
        return False

    return True

# 读取配置文件
with open("config.json", encoding="utf-8") as f:
    config: dict = json.load(f)
# 间歇时间 300 秒
wait = 300
_wait = config.get("wait")
if _wait is not None:
    wait = int(wait)
# 发送者邮箱
usr: str = config['usr']
# 发送者邮箱SMTP凭证
pwd: str = config['pwd']
# 接收者邮箱，可于发送者邮箱一致
receiver: str = config["receiver"]
# 接收者关注的全部基金代码列表
codes = list(config["codes"].keys())
# 临时表格文件名
fname: str = receiver.split('@')[0]+'.csv'
# 存储基金涨跌状态的字典，用于更新阈值
funds = config["codes"]
# 表头名称
columns = ['代码', '名称', '估算涨跌幅', '估算时间']
# 持续间歇爬取，直到处于非开市时间段
while 1:
    if to_break():
        print('未开市')
        break
    gztime = None
    # 调用涨跌数据获取函数
    results = get_increase(codes)
    # 当天日期
    today = get_time_now(fmt='%Y-%m-%d')

    rows = []
    for fund in results:
        code = fund['代码']
        name = fund['名称']
        rate = fund['估算涨跌幅']
        gztime = fund['估算时间']
        # 涨跌幅达到阈值则添加到 rows 里面
        if rate < funds[code][0]:
            funds[code][0] -= 0.5
            rows.append(['\t'+code, name, rate, gztime])
        elif rate > funds[code][1]:
            rows.append(['\t'+code, name, rate, gztime])
            funds[code][0] += 0.5
    if gztime is None:
        continue
    if today > gztime:
        print('未开市')
        break
    if len(rows) > 0:
        # 保存数据到表格里面
        to_csv(fname, columns, rows)
        contents = ['基金涨跌提醒', fname]
        print(f'给 {receiver} 发送邮件中......')
        # 给接收者发送附件及文本
        send_email(usr, pwd, receiver, contents)
        print('邮件发送成功!')

    print(f"暂停{wait}秒")
    time.sleep(wait)
print('程序运行结束')
