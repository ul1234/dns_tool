#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, urllib, time
import jinja2, webapp2
import logging
from datetime import datetime
from google.appengine.api import users
from google.appengine.ext import ndb


#logging.getLogger().setLevel(logging.DEBUG)

class Message(ndb.Model):
    node = ndb.StringProperty()
    channel = ndb.IntegerProperty()
    cmd = ndb.StringProperty()
    payload = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    
    def __str__(self):
        if len(self.payload) < 100:
            msg_str = '[%s]node: %s, channel: %d, cmd: %s, payload len: %d. \n\tpayload: %s' % (self.date, self.node, self.channel, self.cmd, len(self.payload), self.payload)
        else:
            msg_str = '[%s]node: %s, channel: %d, cmd: %s, payload len: %d.' % (self.date, self.node, self.channel, self.cmd, len(self.payload))
        return msg_str
    
    @classmethod
    def query_node(cls, ancestor_key):
        return cls.query(ancestor=ancestor_key).order(cls.date)
        
    @classmethod
    def node_key(cls, node):
        return ndb.Key('Node', node)
    

class Node(webapp2.RequestHandler):
    def get(self):
        while True:
            ancestor_key = Message.node_key(self.request.get('node'))
            msgs = Message.query_node(ancestor_key)
            #logging.error('%s- %s', datetime.now(), msgs.count())
            if msgs.count(): break
            time.sleep(1)
        for msg in msgs:
            self.response.write('%s\n' % msg)
            msg.key.delete()

    def post(self):
        msg = Message(parent = Message.node_key(self.request.get('node')),
                      node = self.request.get('node'),
                      channel = int(self.request.get('channel')),
                      cmd = self.request.get('cmd'),
                      payload = self.request.get('payload'))
        msg.put()
        self.response.write('save: %s\n' % msg)
        

class MainPage(webapp2.RequestHandler):
    pass

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/node', Node),
], debug=True)
