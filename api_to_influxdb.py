# coding:utf-8
import pytest
import json
import logging
from com.log import Logger
from com.mhttp import Request
from com.config import Config
from com.util import read_yaml
from com.util import json_value_from_dic
from datetime import datetime
from influxdb import InfluxDBClient
from com.util import decrype
import hashlib
import hmac
from com.my_redis import Redi

redi = Redi()
request = Request()
log = Logger(__name__, CmdLevel=logging.INFO, FileLevel=logging.INFO)
c = Config()


def login():
    login = dict()
    log.logger.info('log into system at the beginning of test, test_user: "{}"'.format(c.get_env()['user']))
    url = c.get_env()['host'] + '/login'
    # print(url)
    r = request.post(url,
                     headers={'Content-Type': 'application/json'},
                     data=json.dumps({"username": c.get_env()['user'], "password": c.get_env()['pwd']}),
                     verify=False)
    if r.status_code == 200:
        log.logger.info('the test user log into system successfully! ')
        login['apikey'] = r.json()['token']
        login['secrets'] = r.json()['secrets']
        login['login_time'] = int(datetime.now().timestamp())
        login['id'] = r.json()['id']

        log.logger.info('setting token and secret to redis! ')

        redi.set('apikey', login['apikey'])
        redi.set('secrets', login['secrets'])
        redi.set('login_time', login['login_time'])
        redi.set('id', r.json()['id'])


def get_signature(method, url, current_time):
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json, text/plain, */*',
              'Authorization': None,
              'API-Timestamp': None,
              'API-Content-Sig': None
              }
    payload = '{} {} {}'.format(method, url, current_time)
    signature = hmac.new(redi.get('secrets'), payload.encode('ascii'), digestmod=hashlib.sha256).hexdigest()

    header["Authorization"] = "Bearer " + redi.get('apikey').decode('utf8')
    header["API-Timestamp"] = current_time
    header["API-Content-Sig"] = signature
    header["X-disable-encrypt"] = 'true'
    return header


def call_api():
    login()
    test_data = read_yaml('api_to_influxdb.yaml')
    debug = c.get_config('DEFAULT', 'DEBUG')  # setting to DEV if debug is True
    result = []
    for data in test_data:
        header = get_signature(data['method'], data['url'], str(int(datetime.now().timestamp())))
        url = c.get_env()['host'] + data['url']
        body = None
        log.logger.info('{}ing URL: {} '.format(data['method'], data['url']))
        r = request.post(url, headers=header, data=json.dumps(data['data'])) # yml文件里的data
        # print(r.status_code)

        if r.status_code == 200:
            log.logger.info('{}ing success '.format(data['method']))
            if json.loads(debug.lower()) is False:  # you cannot use ==, !=, is for a str boolean
                body = json.loads(decrype(r))  # for prod, decrypt api first

            else:
                body = r.json()

            log.logger.info('calculating totals')
            total = json_value_from_dic(body, data['base_assertion_path']) # yml文件里的base_assertion_path
            log.logger.info('append totals to result')
            result.append({'layer': data['layer'], 'total': total})
        else:
            log.logger.info('calling failed')
            continue
    return result


def format_body_influx(raw):
    '''
    [
    {
    "measurement": "cpu_load_short",
    "tags": {
      "region": "us-west"
    },
    "time": "2009-11-10T23:00:00Z",
    "fields": {
      "value": 0.64
    }
    }
   ]
    :return:
    '''
    jsonbody = []
    current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    # raw = call_api()
    debug = c.get_config('DEFAULT', 'DEBUG')
    ''' 
    print(json.loads(debug.lower())) right
    print(debug)
    print(debug is True) wrong
    print(debug is False) wrong
    print(debug == True) wrong
    print(debug == False) wrong
    print(debug == 'True') right
    print(debug == 'False') right
    '''
    for r in raw:
        t = dict()
        t['measurement'] = 'es_count'
        t['tags'] = {}
        t['tags']['dtype'] = r['layer']
        t['tags']['env'] = 'DEV' if json.loads(debug.lower()) else 'PRD'
        t['time'] = current_time
        t['fields'] = {}
        t['fields']['total'] = r['total']
        jsonbody.append(t)
    # return json.dumps(jsonbody)
    log.logger.info('formating result save to influxDB, result: {} '.format(jsonbody))
    return jsonbody  # return dict as influxDB accepts dict


def format_body_slack(raw):
    debug = c.get_config('DEFAULT', 'DEBUG')
    jsonbody = dict()
    jsonbody['message'] = 'Hooray'
    jsonbody['username'] = 'ES_COUNTS'
    print(jsonbody)
    jsonbody['text'] = 'ENV: {}, TIME: {} \n'.format('DEV' if json.loads(debug.lower()) else 'PRD', datetime.now())
    #jsonbody['text']['ENV'] = 'DEV' if json.loads(debug.lower()) else 'PRD'
    for r in raw:
        jsonbody['text'] += r['layer'] + ': ' + str(r['total']) + ', \n'
    jsonbody['text'] += 'All totals are OK! For more details and histories, please visit: http://your_grafana_server:3000/d/xxx/prd-es?orgId=1&from=now-7d&to=now&refresh=1d' # your grafana url
    log.logger.info('formating result send to slack, result: {} '.format(jsonbody))
    return json.dumps(jsonbody)
    # print(jsonbody['text'])
    # return jsonbody


def insert_influx(jsondata):
    client = InfluxDBClient('influxdb', 8086, 'root', 'root', 'es')
    indb = client.get_list_database()
    exists = False
    for i in indb:
        if i['name'] == 'es':
            exists = True
            continue
    if not exists:
        client.create_database('es')
    client.write_points(jsondata)

    # print(client.get_list_database())  # 显示所有数据库名称


if __name__ == '__main__':
    # print(datetime.now().timestamp())
    # print(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))
    # call_api()
    # data = json.loads(format_body())
    # insert_influx(data)
    raw = call_api()
    #raw = ['a']
    body = None
    print(raw)
    if len(raw) != 8:
        body = json.dumps({'message': 'Oh, No', 'username': 'SYS_STATUS', 'text':
                     'Unable to generate report. some errors happen when calling API. please check log!'})
    else:
        print(format_body_slack(raw))
        insert_influx(format_body_influx(raw))
        body = format_body_slack(raw)

    request.post('https://hooks.slack.com/services/xxx/xxx/xxxx',
    headers = {'Content-Type': 'application/json'},
    data = body)

    CorpID = 'xxx'
    Secret = 'xxxxx'
    res = request.get('https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid='+CorpID+'&corpsecret='+Secret)

    if res.status_code == 200:
        access_token = res.json().get('access_token')
        log.logger.info('get wecom access_token successfully, token: {}'.format(access_token))
        payload = {'touser': 'xx', 'agentid' : 0001, 'msgtype': 'text', 'text' : {'content' : None}}
        payload['text']['content'] = body
        payload = json.dumps(payload)
        log.logger.info('get  payload successfully, payload: {}'.format(payload))
        r= request.post('https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token='+access_token,
                     data = payload)
        if r.status_code == 200:
            log.logger.info('send to wecom Leap agentid successfully, detail: {}'.format(r.json()))
        else:
            log.logger.info('there might be some wrong sending message to wecom, detail: {}'.format(r.json()))