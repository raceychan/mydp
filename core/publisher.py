import pika
import json
from typing import Type, Any
# from core.manager import Manager, manager
from core.config import settings
from core.broker import broker


class Publisher:
    def __init__(self, queue: str = 'main', broker=broker):
        self.broker = broker
        self.channel = self.broker.channel
        self.queue = queue

    def publish(self, exchange='',
                topic='sql_update',
                queue='main',
                body: str = 'hello world'):

        topic = pika.BasicProperties(content_type=topic)
        body = json.dumps(body)
        self.channel.basic_publish(exchange=exchange,
                                   routing_key=queue,
                                   body=body,
                                   properties=topic)

        print(f'''sent message: {body} 
                to queue: {queue} 
                with topic: {topic}''')









# class Publisher:
#     def __init__(self, events=None):
#         self.events = events or settings.EVENTS
#         self.subscribers = {event: dict() for event in self.events}

#     def get_subscribers(self, event):
#         return self.subscribers[event]

#     # Todo: @publisher.register(bond=manager.update)
#     def register(self, event: str = None, receiver: Type[Manager] = manager, callback: str = None):
#         if not callback:
#             callback = getattr(receiver, 'update')

#         if not event:
#             for event in self.events:
#                 self.get_subscribers(event)[receiver] = callback

#     def unregister(self, event: str, receiver: Type[Manager] = manager):
#         del self.get_subscribers(event)[receiver]

#     # Todo: @publisher.notify
#     def notify(self, event: str = None, message: str = None):
#         data_module = self.__class__.__name__.lower()
#         for subscriber, callback in self.get_subscribers(event).items():
#             callback(data_module, event, message)
#     # Todo: make notify a decorator that can be decorated on different function
