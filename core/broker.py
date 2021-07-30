from typing import Callable
from pika import exceptions
from core.config import settings
from conn.conn import RabbitMQConnection


class Broker:
    """ Every instance of the Broker class would
        create a new channel for it to run with
        multi-threads at the same time
        we can limit the number of connections
        using the object pool pattern
    """

    connection = RabbitMQConnection(con_param=settings.RMQ_CON_PARAM)

    def __init__(self):
        pass

    @property
    def channel(self):
        return self.get_channel()

    def subscribe(self, queue):
        self.channel.queue_declare(queue=queue)

    def unsubscribe(self, queue):
        self.channel.queue_delete(queue=queue)


broker = Broker()

if __name__== '__main__':
    broker.channel

