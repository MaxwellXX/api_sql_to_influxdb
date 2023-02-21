import psycopg2
from com.mhttp import Request
import json
from datetime import datetime

conn = psycopg2.connect(database="appservice", user="photo_monitor", password="xxx", host="xxx.rds.cn-north-1.amazonaws.com.cn", port="5432")

request = Request()
cur = conn.cursor()

cur.execute('''SELECT table1.id    AS table1_id,
       table1.photo_album_id AS table1_photo_album_id,
       table1.photo_name AS table1_photo_name,
       table1.update_time    AS table1_update_time
FROM table1
         LEFT OUTER JOIN table2
                         ON table1.photo_album_id = table2.photo_album_id AND
                            table1.photo_name = table2.photo_name
WHERE table1.photo_name IS NOT NULL
  AND table2.status IS NULL
ORDER BY table1.update_time DESC;''')

rows = cur.fetchall()


request.post('https://hooks.slack.com/services/xxx/xxx/xxx',
                     headers={'Content-Type': 'application/json'},
                     data=json.dumps({'message': 'photo',
                                      'username': 'PUBLISHED_PHOTO',
                                      'text': str(datetime.now())+ ' ：统计结果\n'+'photo count: '+ str(len(rows) if rows else 0)}))