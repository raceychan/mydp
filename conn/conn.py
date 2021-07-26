from pika import BlockingConnection, ConnectionParameters
from typing import Any
from abc import ABC,  abstractmethod


''' Descriptor class that does not store
    the connection object in its own instance
    but in its owner's instance
'''


class Connection(ABC):
    def __init__(self, con_param, *args, **kwargs):
        self.con_param = con_param

    def __get__(self, obj, obj_cls) -> Any:
        if obj is None:
            print('accessing descriptor outside the intance')
            return self
        try:
            return obj.__dict__[str(self.con_param)]

        except (KeyError, AttributeError):
            obj.__dict__[str(self.con_param)] = self.build_connection(
                self.con_param)
            return obj.__dict__[str(self.con_param)]

    def __set__(self, obj, value)-> None:
        raise Exception('Connection Class Is Immutable')


    @abstractmethod
    def __delete__(self, obj):
        raise NotImplementedError

    @abstractmethod
    def build_connection(self, value):
        raise NotImplementedError


class RabbitMQConnection(Connection):
    ''' Descriptor class does not store
        the connection object in its own instance
        but in its owner's instance
    '''
    __pool = dict()
    max_con = 3

    def __init__(self, fget=None, fset=None, fdel=None, con_param=None, max_con=3):
        self.con_param = con_param
        self.con = None
        self.con_num = 1
    
    def __set_name__(self, cls, name)->None:
        self.name = name
    
    def __get__(self, obj, cls)->BlockingConnection:
        con = self.__pool.get(f'con_{self.con_num}')
        if con and con.is_open:
  #      if self.con and self.con.is_open:
            return self.__pool.get(f'con_{self.con_num}')
        self.__pool.update({f'con_{self.con_num}':self.build_connection(self.con_param)})
        self.con_num +=1
        self.con_num %= self.max_con
#        self.con = self.build_connection(self.con_param)
        return self.__pool.get(f'con_{self.coun_num}')

    def __set__(self, obj, value)-> None:
        raise Exception('Connection Class Is Immutable')

    # def channel(self):
    #     try:
    #         channel = self.

    def build_connection(self, con_param) -> BlockingConnection:
        connection = BlockingConnection(con_param)
        return connection

    def __delete__(self, obj):
        obj.__dict__[str(self.con_param)].close()
