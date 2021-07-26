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
        # Todo: add a singleton decorator
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
