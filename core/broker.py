import pika
import json
from datetime import datetime
from typing import Callable
from core.config import settings


class Broker:
    ''' Every instance of the Broker class would 
        create a new channel for it to run with 
        multi-threads at the same time
    '''

    def __init__(self):
        self.__con = pika.BlockingConnection(
            settings.RABBITMQ_CONNECTION_PARAMETER)
        self.__channel = self.__con.channel()

    @property
    def con(self):
        ''' Todo: add a retry decorator
        '''
        if self.__con.is_closed:
            self.__con = pika.BlockingConnection(
                settings.RABBITMQ_CONNECTION_PARAMETER)
        return self.__con

    @property
    def channel(self):
        if self.__con.is_closed or self.__channel.is_closed:
            self.__channel = self.con.channel()
        return self.__channel

    @con.deleter
    def con(self):
        return self.__con.close()

    @channel.deleter
    def channel(self):
        return self.__channel.close()

    def subscribe(self, queue):
        self.channel.queue_declare(queue=queue)

    def unsubscribe(self, queue):
        self.channel.queue_delete(queue=queue)


broker = Broker()


# class Publisher:
#     def __init__(self, queue: str = 'main', broker=broker):
#         self.broker = broker
#         self.queue = queue

#     def publish(self, topic, queue, body: str):
#         self.broker.notify(topic=topic, queue=queue, body=body)


# class Subscriber:
#     def __init__(self, queue='main', broker=broker):
#         self.broker = broker
#         self.queue = queue

#     def subscribe(self, queue=None):
#         queue = queue or self.queue
#         self.broker.subscribe(queue)

#     def callback(self, ch, method, topic, body):
#         data = json.loads(body)
#         print(data)
#         if topic.content_type == 'sql_update':
#             print(f'finished at {datetime.now()}')

#     def register(self, queue: str, auto_ack: bool, callback: Callable = None):
#         self.broker.channel.basic_consume(queue=queue,
#                                           auto_ack=auto_ack,
#                                           on_message_callback=self.callback)

#     def consume(self):
#         self.broker.channel.start_consuming()
