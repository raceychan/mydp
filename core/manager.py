
class Subscriber:
    def __init__(self, name):
        self.name = name
        self.history = {}

    def update(self, data_module, event, message):
        print(f'{self.name} received message from module {data_module}: {message}')
        if f'{data_module}' not in self.history.keys():
            self.history[f'{data_module}'] = {event: ''}
        self.history[f'{data_module}'][f'{event}'] = message


class Manager(Subscriber):
    def __init__(self):
        super(Manager, self).__init__(name='manager')


manager = Manager()
