from adisconfig import adisconfig
from adislog import adislog

from flask import Flask, request, redirect
from pymongo import MongoClient
from pika import BlockingConnection, ConnectionParameters, PlainCredentials
from uuid import uuid4
from time import time

application=Flask(__name__)
config=adisconfig('/etc/adistools/wallfaker.yaml')
log=adislog(
    backends=['terminal'],
    debug=True,
    replace_except_hook=False,
)
mongo_cli=MongoClient(
    config.mongo.host,
    config.mongo.port
)
mongo_db=mongo_cli[config.mongo.db]
urls=mongo_db['wallfaker']
metrics=mongo_db['wallfaker_metrics']

@application.route("/<wallfaker_query>", methods=['GET'])
def redirect(wallfaker_query):
    query={
        'wallfaker_query' : wallfaker_query
    }
    data=urls.find_one(query)

    if data:
        wallfaker_uuid=data['wallfaker_uuid']
        wallfaker_redirection_uuid=str(uuid4())
        user_agent=str(request.user_agent)
        if request.headers.getlist("X-Forwarded-For"):
            ip_addr=request.headers.getlist("X-Forwarded-For")[0]
        else:
            ip_addr=str(request.remote_addr)
        timestamp=time()

        document={
            "wallfaker_uuid"              : wallfaker_uuid,
            "wallfaker_redirection_uuid"  : wallfaker_redirection_uuid,
            "wallfaker_query"             : wallfaker_query,
            "ip_addr"                     : ip_addr,
            "user_agent"                  : user_agent,
            "timestamp"                   : timestamp,
            "host_details"                : None        
            }

        metrics.insert_one(document)


        if "facebookexternalhit" in user_agent:
            url=data['expected_url']
        else:
            url=data['real_url']

        return Flask.redirect(
            application,
            location=url,
            code=302
        )
    else:
        return ""
