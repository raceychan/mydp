import pika
import json
from typing import Type, Any
from core.broker import broker


''' Store States between Decorators:
    refer: https://stackoverflow.com/questions/33707456/storing-state-between-decorators-in-python
'''


class Publisher:
    ''' Todo:
        1. make Publisher a class decorator
        2. enable it saves attrs of decorated method

        refer: https://github.com/pallets/click/blob/29df8795dc146ddea328e458068185d3314820e5/src/click/decorators.py
        the users of Publisher class are all different data modules
        that are in charge of extracting data from the outside sourcs
        we extracting the params from method sql_update and save it to class Publisher
        then paste it to method data_update

        idea2:
        make pub a class
        with a function decorator register
        that turns the method decorated
        into a Register class, which shares states with pub

        where app is a instance of a Callable class
        task is a method of the Callable class and also
        a function decorator which turns the function
        it decorates into a class
        reference: Celery https://github.com/celery/celery/blob/52b6238a87f80c3c63d79595deb375518af95372/celery/app/base.py#L464
        class Celery:
            def task(self, *args, **opts):
                'Decorator to create a task class out of any callable'
                    def _task_from_fun(self, fun, name=None, base=None, bind=False, **options):
                        name = name
                        base = self.Task
                        task = type(fun.__name__, (base,)
    '''

    def __init__(self, queue: str = 'main', broker=broker):
        self.broker = broker
        self.queue = queue

    def publish(self,
                topic='sql_update',
                queue='main',
                body: str = 'hello world',
                exchange='',):
        ''' this should be a decorator
        '''
        self.broker.subscribe(queue)
        topic = pika.BasicProperties(content_type=topic)
        body = json.dumps(body)

        self.broker.channel.basic_publish(exchange=exchange,
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
