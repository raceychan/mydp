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
        callback = callback or self.callback
        self.broker.channel.basic_consume(queue=self.queue,
                                          auto_ack=auto_ack,
                                          on_message_callback=callback)

    def consume(self):
        self.broker.channel.start_consuming()
