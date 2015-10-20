#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function
import tornado.httpserver
import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.gen
import os
import tornadoredis

# import sys
# reload(sys)
# sys.setdefaultencoding('utf8')

host = '192.168.1.150'
pub_redis = tornadoredis.Client(host)
pub_redis.connect()


class MainHandler(tornado.web.RequestHandler):  # 每个浏览器打开页面时进入

    def check_origin(self, origin):
        return True

    def get(self):
        self.render('index.html', title='PubSub + WebSocket Demo')


class NewMessageHandler(tornado.web.RequestHandler):

    def check_origin(self, origin):
        return True

    def post(self):
        message = self.get_argument('message')
        pub_redis.publish('test_channel', message)
        self.set_header('Content-Type', 'text/plain')
        self.write('sent: %s' % (message, ))
        print(message + ' ')


class MessageHandler(tornado.websocket.WebSocketHandler):

    def check_origin(self, origin):
        return True

    def __init__(self, *args, **kwargs):
        super(MessageHandler, self).__init__(*args, **kwargs)
        self.listen()

    @tornado.gen.engine
    def listen(self):
        self.sub_client = tornadoredis.Client(host)
        self.sub_client.connect()
        yield tornado.gen.Task(self.sub_client.subscribe, 'test_channel'
                               )
        self.sub_client.listen(self.on_message)  # 设置redis订阅的回调函数

    def on_message(self, msg):
        if msg.kind == 'message':
            self.write_message(msg.body)  # 向浏览器发送订阅的信息
        if msg.kind == 'disconnect':

            # Do not try to reconnect, just send a message back
            # to the client and close the client connection

            self.write_message('The connection terminated due to a Redis server error.')
            self.close()

    def on_close(self):
        if self.sub_client.subscribed:
            self.sub_client.unsubscribe('test_channel')
            self.sub_client.disconnect()


settings = {'static_path': os.path.join(os.path.dirname(__file__),
            'static'),
            'js_path': os.path.join(os.path.dirname(__file__), 'js')}

application = tornado.web.Application([
        (r'/', MainHandler),
        (r'/msg', NewMessageHandler),
        (r'/track', MessageHandler),
        (r"/(favicon\.ico)", tornado.web.StaticFileHandler, dict(path=settings['static_path'])),
        (r"/js/(.*)", tornado.web.StaticFileHandler, dict(path=settings['js_path']))
    ], **settings)

if __name__ == '__main__':
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    print('Demo is runing at 0.0.0.0:8888\nQuit the demo with CONTROL-C')
    tornado.ioloop.IOLoop.instance().start()
