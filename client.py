#!/usr/bin/python
# -*- coding: utf-8 -*-

import gevent.server, gevent.pool, gevent.monkey
gevent.monkey.patch_all()

import socket, time, sys
import urllib, urllib2
import pprint, logging
import functools
from datetime import datetime

from dnstool import DnsTool

#logging.basicConfig(level = logging.CRITICAL)
logging.basicConfig(level = logging.DEBUG)

host = 'ul2test001.appspot.com'
#server_info = DnsTool.get_google_iplist(host)
server_info = [('127.0.0.1', 1)]
http_mode = 'http'
http_port = '8080'

class Client(object):
    MAX_READ_BYTES = 800000  # 800K Bytes

    def __init__(self, host, port, callback):
        self.callback = callback
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        self.stop = False

    def stop(self):
        self.stop = True

    def start(self):
        while not self.stop:
            data = self.socket.recv(Client.MAX_READ_BYTES)
            self.callback(data)
        self.socket.close()

class Server(object):
    MAX_CLIENT_NUM = 5
    MAX_READ_BYTES = 800000  # 800K Bytes
    
    def __init__(self, host, port, callback):
        self.logger = logging.getLogger('TcpServer')
        self.logger.setLevel(logging.DEBUG)
        self.callback = callback
        self.pool = gevent.pool.Pool(Server.MAX_CLIENT_NUM)
        self.server = gevent.server.StreamServer((host, port), self.handler, spawn = self.pool)
        self.logger.info('server listen at %s', (host, port))
        self.server.serve_forever()
        
    def handler(self, socket, address):
        self.logger.info('new connection accepted from %s', address)
        while True:
            try:
                data = socket.recv(Server.MAX_READ_BYTES)
                if data:
                    self.logger.debug('[%s]received data: %s', address, data)
                    self.callback(payload = data)
            except:
                break
        self.logger.info('connection %s close', address)

class NodeProxy(object):
    logger_level = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning': logging.WARNING, 'error': logging.ERROR, 'critical': logging.CRITICAL}

    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger('NodeProxy')
        self.set_log_level('debug')

    def set_log_level(self, level):
        self.logger.setLevel(self.logger_level[level])

    def print_(self, data):
        now = datetime.now()
        print now
        #pprint.pprint(data)
        print data

    def _get_ip(self, server_info):
        return (host, server_info[0][0])

    def send_to(self, node, channel, cmd, payload):
        try:
            host, ip = self._get_ip(server_info)
            enc_data = urllib.urlencode({'node': node, 'channel': channel, 'cmd': cmd, 'payload': payload})
            url = '%s://%s:%s/node' % (http_mode, ip, http_port)
            self.logger.info('[POST %s]%s, %s', host, url, enc_data)
            
            request = urllib2.Request(url, headers={'Host': host})
            response = urllib2.urlopen(request, enc_data)       # post
            page = response.read()
            self.print_(page)
        except Exception as e:
            self.print_('send fail: %s' % e)

    def receive(self):
        try:
            host, ip = self._get_ip(server_info)
            enc_data = urllib.urlencode({'node': self.name})
            url = '%s://%s:%s/node?%s' % (http_mode, ip, http_port, enc_data)
            self.logger.info('[GET %s]%s', host, url)

            request = urllib2.Request(url, headers={'Host': host})
            response = urllib2.urlopen(request)     # get
            page = response.read()
            self.print_(page)
        except Exception as e:
            self.print_('receive fail: %s' % e)
            



if __name__ == '__main__':
    client_proxy = NodeProxy('home')
    #client_proxy.set_log_level('debug')
    #client_proxy.send_to('home', 1, 'connect', 'hello')
    #client_proxy.send_to('home', 2, 'test', 'hello22222')
    #client_proxy.send_to('company', 3, 'test3', 'hello3333')
    #client_proxy.receive()
    if sys.argv[1] == '1':
        client_proxy.receive()
    elif sys.argv[1] == '2':
        #rev = gevent.spawn(client_proxy.receive)
        #time.sleep(5)
        send1 = gevent.spawn(client_proxy.send_to, 'home', 1, 'connect', '1-%s' % datetime.now())
        send2 = gevent.spawn(client_proxy.send_to, 'home', 2, 'test', '2-%s' % datetime.now())
        send3 = gevent.spawn(client_proxy.send_to, 'company', 3, 'haha', '3-%s' % datetime.now())
        gevent.joinall([send1, send2, send3])
    
    #s = Server('127.0.0.1', 8001, functools.partial(client_proxy.send_to, 'home', 1, 'test'))
    print 'done'
    

    
    