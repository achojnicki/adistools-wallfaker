from adisconfig import adisconfig
from log import Log

from flask import Flask, request, redirect
from pymongo import MongoClient
from uuid import uuid4
from datetime import datetime

class Wallfaker:
    project_name='adistools-wallfaker'
    def __init__(self):
        self._config=adisconfig('/opt/adistools/configs/adistools-wallfaker.yaml')
        self._log=Log(
            parent=self,
            backends=['rabbitmq_emitter'],
            debug=self._config.log.debug,
            rabbitmq_host=self._config.rabbitmq.host,
            rabbitmq_port=self._config.rabbitmq.port,
            rabbitmq_user=self._config.rabbitmq.user,
            rabbitmq_passwd=self._config.rabbitmq.password,
        )  

        self._mongo_cli=MongoClient(
            self._config.mongo.host,
            self._config.mongo.port,
        )

        self._mongo_db=self._mongo_cli[self._config.mongo.db]
        self._urls=self._mongo_db['wallfaker_urls']
        self._metrics=self._mongo_db['wallfaker_urls_metrics']

    def add_metric(self,wallfaker_uuid, wallfaker_query, remote_addr, user_agent, time):
        document={
            "wallfaker_uuid"  : wallfaker_uuid,
            "wallfaker_query" : wallfaker_query,
            "time"              : {
                "timestamp"         : time.timestamp(),
                "strtime"          : time.strftime("%m/%d/%Y, %H:%M:%S")
                },
            "client_details"    : {
                "remote_addr"       : remote_addr,
                "user_agent"        : user_agent,
                }
            }

        self._metrics.insert_one(document)
    def get_fake_url(self, wallfaker_query):
        query={
            'wallfaker_query' : wallfaker_query
        }
        return self._urls.find_one(query)

wallfaker=Wallfaker()
application=Flask(__name__)

@application.route("/<wallfaker_query>", methods=['GET'])
def redirect(wallfaker_query):
    
    data=wallfaker.get_fake_url(wallfaker_query)
    print(data)
    if data:
        time=datetime.now()
        wallfaker_uuid=data['wallfaker_uuid']
        user_agent=str(request.user_agent)
        if request.headers.getlist("X-Forwarded-For"):
            remote_addr=request.headers.getlist("X-Forwarded-For")[0]
        else:
            remote_addr=str(request.remote_addr)
        
        wallfaker.add_metric(
            wallfaker_query=wallfaker_query,
            wallfaker_uuid=wallfaker_uuid,
            remote_addr=remote_addr,
            user_agent=user_agent,
            time=time
            )

        if "facebookexternalhit" in user_agent:
            url=data['guise_url']
        else:
            url=data['real_url']

        return Flask.redirect(
            application,
            location=url,
            code=302
        )
    else:
        return ""