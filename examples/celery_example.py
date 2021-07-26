class Celery:
    def __init__(self, main=None, **kwargs):
        self._tasks = None
        self.registry_cls = TaskRegistry
        if not isinstance(self._tasks, TaskRegistry):
            # _tasks is a dict of class TaskRegistry
            self._tasks = self.registry_cls(self._tasks or {})
            # that instantiates all classes

    def task(self, *args, **opts):
        """     @app.task
                def fun():
                    pass
        """
        def inner_create_task_cls(shared=True, filter=None, lazy=True, **opts):
            def _create_task_cls(fun):
                ret = self._task_from_fun(fun, **opts)
                return ret
            return _create_task_cls

        if len(args) == 1 and callable(args[0]):
            return inner_create_task_cls(**opts)(*args)
        else:
            raise Exception('argument 1 to @task() must be a callable')
        return inner_create_task_cls(**opts)

    def _task_from_fun(self, fun, name=None, base=None, bind=False, **options):
        name = self.gen_task_name(fun.__name__, fun.__module__)
        '''def gen_task_name(app, name, module_name):
                    """Generate task name from name/module pair."""
                    module_name = module_name or '__main__'

                    module = sys.modules[module_name]

                    if module:
                        module_name = module.__name__
                        # - If the task module is used as the __main__ script
                        # - we need to rewrite the module part of the task name
                        # - to match App.main.
                        if MP_MAIN_FILE and module.__file__ == MP_MAIN_FILE:
                            module_name = '__main__'
                    if module_name == '__main__' and app.main:
                        return '.'.join([app.main, name])
                    return '.'.join(p for p in (module_name, name) if p)
            '''

        base = self.Task

        run = fun  # if bind else staticmethod(fun)

        task = type(fun.__name__, (base,), dict({
            'app': self,
            'name': name,
            'run': run,
            '_decorated': True,
            '__doc__': fun.__doc__,
            '__module__': fun.__module__,
            '__annotations__': fun.__annotations__,
            '__header__': staticmethod(head_from_fun(fun, bound=bind)),
            '__wrapped__': run}, **options))()
        task.__qualname__ = fun.__qualname__
        self._tasks[task.name] = task
        task.bind(self)  # connects task to this app

        ''' class Task  
                @classmethod
                def bind(cls, app):
                    was_bound, cls.__bound__ = cls.__bound__, True
                    cls._app = app
                    conf = app.conf
                    cls._exec_options = None  # clear option cache

                    for attr_name, config_name in cls.from_config:
                        if getattr(cls, attr_name, None) is None:
                            setattr(cls, attr_name, conf[config_name])

                    # decorate with annotations from config.
                    if not was_bound:
                        cls.annotate()

                        from celery.utils.threads import LocalStack
                        cls.request_stack = LocalStack()

                    cls.on_bound(app)      # PeriodicTask uses this to add itself 
                    return app             # to the PeriodicTask schedule
        '''

        return task
