from types import MethodType
from pika import BlockingConnection, ConnectionParameters
from typing import Any, Optional, Union
from abc import ABC, abstractmethod
from sqlalchemy import create_engine


""" Descriptor class that does not store
    the connection object in its own instance
    but in its owner's instance
"""


class Connection(ABC):
    def __init__(self, con_param, max_con=3, *args, **kwargs):
        self.con_param = con_param
        self.max_con = max_con

    def __get__(self, obj, obj_cls) -> Any:
        if obj is None:
            print("accessing descriptor outside the intance")
            return self
        try:
            return obj.__dict__[str(self.con_param)]

        except (KeyError, AttributeError):
            obj.__dict__[str(self.con_param)] = self.build_connection(
                self.con_param)
            return obj.__dict__[str(self.con_param)]

    def __set__(self, obj, value) -> None:
        raise Exception("Connection Class Is Immutable")

    @abstractmethod
    def __delete__(self, obj):
        raise NotImplementedError

    @abstractmethod
    def build_connection(self, value):
        raise NotImplementedError


class RabbitMQConnection(Connection):
    """ Descriptor class does not store
        the connection object in its own instance
        but in its owner's instance
    """

    __pool = dict()

    def __init__(self, 
                 fget=None,
                 fset=None,
                 fdel=None,
                 *,
                 con_param,
                 max_con=3):

        self.con_param = con_param
        self.con: Union[BlockingConnection, Any] = None
        self.max_con = max_con
        self.con_num = 0

    def __set_name__(self, cls, name) -> None:
        self.name = name

    def __get__(self, obj, cls) -> BlockingConnection:
        if obj is None:
            raise Exception("Class Not Instantiated")
        obj.__dict__["get_channel"] = MethodType(self.get_channel, obj)
        if self.con and self.con.is_open:
            return self.con
        self.con = self.build_connection(self.con_param)
        return self.con

    def __set__(self, obj, value) -> None:
        raise Exception("Connection Class Is Immutable")

    def __delete__(self, obj):
        self.__pool[f"con_{self.con_num}"].close()

    def get_channel(self, obj):
        ''' Bug: every time broker.channel is called
            it creates a new channel up to 3
        '''
        channel = obj.__dict__.get(f"channel_{self.con_num}")
        if channel and channel.is_open:
            return channel
        channel = self.con.channel()
        obj.__dict__.update({f"channel_{self.con_num}": channel})
        channel = obj.__dict__[f"channel_{self.con_num}"]
        self.increase_con_num()
        return channel

    def increase_con_num(self):
        while len(self.__pool) < self.max_con:
            self.con_num += 1
            self.con_num %= self.max_con
            return self.con_num
        raise Exception("Too much connection")

    def build_connection(self, con_param):
        connection = BlockingConnection(con_param)
        return connection


class MysqlConnection(Connection):
    def __init__(self, con_param):
        self.engine = create_engine(con_param)

    def build_connection(self):
        self.conn = self.engine.begin()
        return self.conn

    def __delete__(self):
        self.conn.close()

