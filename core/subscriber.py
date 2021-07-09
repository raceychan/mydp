
import json
from datetime import datetime
from typing import Callable

from core.broker import broker
''' despite the broker instance of 
    class Broker is imported in different
    files, it remains the same instance everywhere
    (within the same python process)
'''


class Subscriber:
    def __init__(self, queue: str = 'main', broker=broker):
        self.queue = queue
        self.broker = broker

    def callback(self, channel, method, topic, body):
        data = json.loads(body)

        if topic.content_type == 'sql_update':
            print('test_if_statement')

        print(f'''
                receive topic: {topic} and 
                body: {data} 
                at {datetime.now().date}''')
        self.broker.channel.basic_ack(delivery_tag=method.delivery_tag)

    def register(self, queue: str = 'main',
                 auto_ack: bool = False,
                 callback: Callable = None):
        ''' register as a consumer'''

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

