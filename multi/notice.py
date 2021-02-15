import yagmail
from typing import TypeVar, List
import time
import json
import requests
import csv
import operator
import functools


def read_config() -> list:
    with open("config.json", encoding="utf-8") as f:
        config: dict = json.load(f)
    # 等待时间
    wait = 300
    _wait = config.get("wait")
    if _wait is not None:
        wait = int(wait)
    # 发送者邮件
    usr = config['usr']
    # 密码
    pwd = config['pwd']
    #
    receivers = config["receivers"]
    columns = ['代码', '名称', '估算涨跌幅', '估算时间']
    return [usr, pwd, receivers, wait, columns]


def get_time_now(fmt: str = '%Y-%m-%d %H:%M:%S'):
    '''
    获取时间
    '''
    ts = int(time.time())
    ta = time.localtime(ts)
    now = time.strftime(fmt, ta)
    return now


def to_csv(fname: str, column: list, rows: list) -> bool:
    '''
    写入 csv 文件
    '''
    with open(fname, 'w', encoding='utf-8-sig', newline="") as f:
        w = csv.writer(f)
        w.writerow(column)
        w.writerows(rows)
    return True


def get_intrease(codes: TypeVar('List[str], str)', List[str], str)) -> List[dict]:
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
    codes = list(set(codes))
    data = {
        'pageIndex': '1',
        'pageSize': '300',
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
        code = fund['FCODE']
        name = fund['SHORTNAME']
        try:
            rate = float(fund['GSZZL'])
        except:
            rate = 0
        gztime = fund['GZTIME']
        row = [code, name, rate, gztime]
        temp = dict(zip(columns, row))
        rows.append(temp.copy())
    return rows


def send_emails(usr: str, pwd: str, emails: str, contents: list) -> bool:
    yag = yagmail.SMTP(user=usr,
                       password=pwd,
                       host='smtp.qq.com')
    for email, content in zip(emails, contents):
        print('成功给',email, '发送邮件！')
        yag.send(email, '涨跌提醒', content)
    return True


def to_break() -> bool:
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


usr, pwd, receivers, wait, columns = read_config()
_codes = [list(recevier["codes"].keys()) for recevier in receivers]
codes = functools.reduce(operator.concat, _codes)
columns = ['代码', '名称', '估算涨跌幅', '估算时间']
while 1:
    gztime = None
    if to_break():
        print('不开市')
        break
    results = get_intrease(codes)
    today = get_time_now(fmt='%Y-%m-%d')
    contents = []
    emails = []
    for recevier in receivers:
        email = recevier["email"]
        rows = []
        for fund in results:
            code = fund['代码']
            name = fund['名称']
            rate = fund['估算涨跌幅']
            gztime = fund['估算时间']

            if not recevier["codes"].get(code):
                continue
            # 跌
            if rate < recevier["codes"][code][0]:
                recevier["codes"][code][0] -= 0.5
                rows.append(['\t'+code, name, rate, gztime])
            # 涨
            elif rate > recevier["codes"][code][1]:
                rows.append(['\t'+code, name, rate, gztime])
                recevier["codes"][code][1] += 0.5

        if len(rows) > 0:
            fname = email.split('@')[0]+'.csv'
            to_csv(fname, columns, rows)
            content = ['基金涨跌提醒', fname]
            contents.append(content)
            emails.append(email)
    if gztime is None:
        continue
    if today > gztime.split(' ')[0]:
        print('不开市')
        break
    
    if len(contents) > 0:
        print('正在发送邮件...')
        send_emails(usr, pwd, emails, contents)
        print("全部邮件成功！")
    print(f"暂停 {wait} 秒")

    time.sleep(wait)
print('结束')
