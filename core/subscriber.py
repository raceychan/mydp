
import json
from datetime import datetime
from typing import Callable

from core.broker import broker
''' despite the broker instance of 
    class Broker is imported in different
    files, it remains the same instance everywhere 
'''


class Subscriber:
    def __init__(self, queue='main', broker=broker):
        self.queue = queue
        self.broker = broker
        self.channel = self.broker.channel

    def callback(self, ch, method, topic, body):
        data = json.loads(body)

        if topic.content_type == 'sql_update':
            print(f'''
                    receive topic: {topic} and 
                    body: {body} 
                    at {datetime.now().date}''')

    def register(self, queue: str = 'main',
                 auto_ack: bool = False,
                 callback: Callable = None):
        self.broker.channel.basic_consume(queue=self.queue,
                                          auto_ack=auto_ack,
                                          on_message_callback=self.callback)

    def consume(self):
        self.broker.channel.start_consuming()


# class Subscriber:
#     def __init__(self, name):
#         self.name = name
#         self.history = {}

#     def update(self, data_module, event, message):
#         print(f'{self.name} received message from module {data_module}: {message}')
#         if f'{data_module}' not in self.history.keys():
#             self.history[f'{data_module}'] = {event: ''}
#         self.history[f'{data_module}'][f'{event}'] = message


# class Manager(Subscriber):
#     def __init__(self):
#         super(Manager, self).__init__(name='manager')


# manager = Manager()
