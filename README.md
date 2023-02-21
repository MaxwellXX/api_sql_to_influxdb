这是个从postgresql数据库表中读取数据，再插入influxdb以在grafana看板展示数据的小脚本。

# 有如下功能：

1. 生成sql查询语句
2. 用ssh证书连接远程sql数据库后，再向数据库端口5432发送查询语句，返回查询结果的字典
3. 格式化插入influxdb的数据后插入influxdb
4. 插入成功后给slack发送通知

# 如何运行
直接在目录下运行 `python sql_to_influxdb.py`。也可以在crontab添加定时作业。
```
#every day 7:10
#10 07 * * * bash -c 'PYTHONPATH=. python sql_to_influxdb.py'
```