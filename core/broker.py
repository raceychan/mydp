import pika
import json
from datetime import datetime
from typing import Callable
from pika import BlockingConnection
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

    connection = RabbitMQConnection(settings.RMQ_CON_PARAM)

    def __init__(self):
        pass

    @property
    def channel(self):
        try:
            if self.__channel.is_open:
                return self.__channel
            else:
                raise AttributeError

        except (KeyError, AttributeError):
            self.__channel = self.connection.channel()
            return self.__channel

    @channel.deleter
    def channel(self):
        return self.__channel.close()

    def subscribe(self, queue):
        self.channel.queue_declare(queue=queue)

    def unsubscribe(self, queue):
        self.channel.queue_delete(queue=queue)


broker = Broker()
