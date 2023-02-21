# coding:utf-8
import sys
import psycopg2
import traceback
from sshtunnel import SSHTunnelForwarder 
from sqlalchemy.orm import sessionmaker  # Run pip install sqlalchemy
from com.config import Config
from com.log import Logger
from influxdb import InfluxDBClient
import logging
import json
from datetime import datetime, timedelta
from com.mhttp import Request
from time import sleep

log = Logger(__name__, CmdLevel=logging.INFO, FileLevel=logging.INFO)
c = Config()
request = Request()
DB_SERVER = c.get_config('REPO', 'STG') if c.get_config('DEFAULT', 'DEBUG') == 'True' else c.get_config('REPO', 'SVR')
KEY_PATH = c.get_config('SEC_KEY', 'PRD') if c.get_config('DEFAULT', 'DEBUG') == 'False' else c.get_config('SEC_KEY','DEV')
datas = [{'source': 'table_a', 'type': 'total', 'key': 'All'},
             {'source': 'table_a', 'type': 'total', 'key': 'col_country'},
             {'source': 'table_a', 'type': 'total', 'key': 'col_sku'},
             {'source': 'table_a', 'type': 'daily', 'key': 'All'},
             {'source': 'table_a', 'type': 'daily', 'key': 'fs_operator'},
             {'source': 'table_a', 'type': 'daily', 'key': 'col_country'},
             {'source': 'table_a', 'type': 'daily', 'key': 'col_sku'},

             {'source': 'table_b', 'type': 'total', 'key': 'All'},
             {'source': 'table_b', 'type': 'total', 'key': 'col_country'},
             {'source': 'table_b', 'type': 'total', 'key': 'col_sku'},
             {'source': 'table_b', 'type': 'daily', 'key': 'All'},
             {'source': 'table_b', 'type': 'daily', 'key': 'fs_operator'},
             {'source': 'table_b', 'type': 'daily', 'key': 'col_country'},
             {'source': 'table_b', 'type': 'daily', 'key': 'col_sku'},

             {'source': 'table_c', 'type': 'total', 'key': 'All'},
             {'source': 'table_c', 'type': 'total', 'key': 'col_country'},
             {'source': 'table_c', 'type': 'daily', 'key': 'All'},
             {'source': 'table_c', 'type': 'daily', 'key': 'fs_operator'},
             {'source': 'table_c', 'type': 'daily', 'key': 'col_country'},

             {'source': 'table_d', 'type': 'total', 'key': 'All'},
             {'source': 'table_d', 'type': 'total', 'key': 'col_country'},
             {'source': 'table_d', 'type': 'daily', 'key': 'All'}]
            # {'source': 'table_d', 'type': 'daily', 'key': 'fs_operator'},
            # {'source': 'table_d', 'type': 'daily', 'key': 'col_country'}]

datas1 = [{'source': 'table_c', 'type': 'total', 'key': 'All'},
             {'source': 'table_c', 'type': 'total', 'key': 'col_country'},
             {'source': 'table_c', 'type': 'daily', 'key': 'All'},
             {'source': 'table_c', 'type': 'daily', 'key': 'fs_operator'},
             {'source': 'table_c', 'type': 'daily', 'key': 'col_country'}]

def bind_sql_query(data):
    # 生成sql查询语句
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    day_before_yesterday = now - timedelta(days=2)
    upper = yesterday.strftime('%Y-%m-%d') + ' 16:00:00'
    lower = day_before_yesterday.strftime('%Y-%m-%d') + ' 16:00:00'

    key = "'All'" if data['key'] == 'All' else data['key']
    select = "select '" + data['source'] + "' as source, '" + data['type'] + "' as type, "+ "'"+data['key'] + "' as key," + key \
                 + " as value, count(*) as total, min(valid_from) + interval '8 hours' as min_update_time, " + \
                 "max(valid_from) + interval '8 hours' as max_update_time from " + data['source'] + ' '
    where = ' ' if data['type'] == 'total' else "where valid_from < '" + upper + "' and valid_from > '" + lower + "' "
    groupby = ' ' if data['key'] == 'All' else 'group by ' + data['key'] + ' '
    orderby = 'order by count(*) desc ' if (data['key'] == 'col_sku' or data['key'] == 'fs_operator') else ' '
    limit = 'limit 20;'
    return select + where + groupby + orderby + limit

def get_totals_from_sql_db():
    # 用证书建立ssh连接后，连接postgresql5432端口
    db_results = list()
    now = datetime.now()
    print('KEY_PATH: ',KEY_PATH)
    print('DB_SERVER: ',DB_SERVER)
    from sqlalchemy import create_engine, text

    '''
    https://stackoverflow.com/questions/2083987/how-to-retry-after-exception/7663441
    for i in range(100):
    for attempt in range(10):
    try:
      # do thing
    except:
      # perhaps reconnect, etc.
    else:
      break
    else:
    # we failed all the attempts - deal with the consequences.
    
    retry 10 times with interval of 10 seconds 
    '''
    for i in range(10):
        try:
            server = SSHTunnelForwarder(
                (DB_SERVER, 22),
                ssh_private_key=KEY_PATH,
                # in my case, I used a password instead of a private key
                ssh_username="user",
                # ssh_password="<mypasswd>",
                remote_bind_address=('127.0.0.1', 5432)
                # logger=create_logger(loglevel=1)
            )
            server.daemon_forward_servers = True

            with server:
                log.logger.info('create ssh server success ')
                server.start()
                # print(server.local_bind_port)  # show assigned local port
                local_port = str(server.local_bind_port)  # local port might change
                engine = create_engine('postgresql://anna:philips_monitor@127.0.0.1:' + local_port + '/lg-geofs1')
                Session = sessionmaker(bind=engine, autocommit=True)
                session = Session()
                log.logger.info('create postgresql session success ')

                for data in datas:
                    sql_query = bind_sql_query(data)
                    log.logger.info('executing sql: {} '.format(sql_query))
                    print(sql_query)
                    db_result = session.execute(text(sql_query))
                    log.logger.info('get db result ')
                    # print(db_result,'=====')
                    for row in db_result:
                        # print('row: ', row)
                        db_results.append(row)
                session.close()
                print('session closed')
        except (Exception, psycopg2.Error) as error:
            _, _, tb = sys.exc_info()
            traceback.print_tb(tb)  # Fixed format
            tb_info = traceback.extract_tb(tb)
            filename, line, func, text = tb_info[-1]
            log.logger.info('An error occurred on line {} in statement {}'.format(line, text))
            log.logger.info('failed to connect server, will retry after 10 seconds')
            sleep(10)
            log.logger.info('retrying, retrying  the {} time'.format(i+1))
            print("Error while connecting to PostgreSQL: {}, retry {}".format(error, i+1))
            continue
        else:
            server.stop()
            log.logger.info('server stopped ')
            print('server closed')
            return db_results
            break
    else:
        log.logger.info('failed to connect after max retry, exit')
        body = json.dumps({'username': 'REPO_COUNTS', 'message': 'Ooops!', 'text': 'Ooops, failed to connect to REPO after max retry(10), please execute script manually!'})
        request.post('https://hooks.slack.com/services/xxx/xxx/xxxx',
                     headers={'Content-Type': 'application/json'},
                     data=body)
        sys.exit()

def format_body_influx(raw):
    # 插入influxdb之前格式化一下
    jsonbody = []
    current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    debug = c.get_config('DEFAULT', 'DEBUG')

    for r in raw:
        t = dict()
        t['measurement'] = r['source']
        t['tags'] = {}
        t['tags']['env'] = 'DEV' if debug == 'True' else 'PRD'
        t['tags']['type'] = r['type']
        t['tags']['key'] = r['key']
        t['tags']['value'] = r['value']
        t['time'] = current_time
        t['fields'] = {}
        t['fields']['total'] = r['total']
        t['fields']['min_update_time'] = r['min_update_time'].strftime('%Y-%m-%d %H:%M:%S') if r['min_update_time'] else '1970-01-01 00:00:00'
        t['fields']['max_update_time'] = r['max_update_time'].strftime('%Y-%m-%d %H:%M:%S') if r['min_update_time'] else '1970-01-01 00:00:00'
        jsonbody.append(t)
    log.logger.info('formating result be saved to influxDB, result: {} '.format(jsonbody))
    return jsonbody  # return dict as influxDB accepts dict

def insert_influx(jsondata):
    # 插入influxdb
    log.logger.info("inserting into inFluxDB")
    client = InfluxDBClient('influxdb', 8086, 'root', 'root', 'repo') # should be localhost when running in local
    indb = client.get_list_database()
    exists = False
    for i in indb:
        if i['name'] == 'repo':
            exists = True
            continue
    if not exists:
        client.create_database('repo')
    client.write_points(jsondata)
    log.logger.info('data inserted to influxdb')


def format_body_slack():
    debug = c.get_config('DEFAULT', 'DEBUG')
    jsonbody = dict()
    jsonbody['message'] = 'Hooray'
    jsonbody['username'] = 'REPO_COUNTS'
    print(jsonbody)
    jsonbody['text'] = '环境: {},   时间: {} \n'.format('Dev: stg1s' if debug == 'True' else 'Prd: prd1s', datetime.now())

    jsonbody['text'] += 'DB总数统计完了，戳此链接看详情: http://your_web_server:3000/d/oH0sXEvGk/reposhu-liang-jian-kong?orgId=1&refresh=1d'
    log.logger.info('formating result send to slack, result: {} '.format(jsonbody))
    return json.dumps(jsonbody)




if __name__ == '__main__':
    db_result = get_totals_from_sql_db()
    if db_result:
        jbody = format_body_influx(db_result)
    #print(jbody)
        insert_influx(jbody)
        print('insert influx OK')

        request.post('https://hooks.slack.com/services/xxx/xxx/xxxx',
        headers={'Content-Type': 'application/json'},
        data=format_body_slack())

    else:
        log.logger.info('failed to get result from REPO db, please see details in log')
        print('failed to get result from REPO db, please see details in log')




