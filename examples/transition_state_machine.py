try:
    from enum import Enum, EnumMeta
except ImportError:
    class Enum:
        pass

    class EnumMeta:
        pass

import inspect
import itertools
import logging

from collections import OrderedDict, defaultdict, deque
from functools import partial
from six import string_types
import warnings

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())

warnings.filterwarnings(
    action='default', message=r".*transitions version.*", category=DeprecationWarning)


def listify(obj):
    if obj is None:
        return []

    try:
        return obj if isinstance(obj, (list, tuple, EnumMeta)) else [obj]
    except ReferenceError:
        # obj is an empty weakref
        return [obj]


def _prep_ordered_arg(desired_length, arguments=None):
    arguments = listify(arguments) if arguments is not None else [None]
    if len(arguments) != desired_length and len(arguments) != 1:
        raise ValueError("Argument length must be either 1 or the same length as "
                         "the number of transitions.")
    if len(arguments) == 1:
        return arguments * desired_length
    return arguments


class State(object):
    dynamic_methods = ['on_enter', 'on_exit']

    def __init__(self, name, on_enter=None, on_exit=None,
                 ignore_invalid_triggers=None):
        self._name = name
        self.ignore_invalid_triggers = ignore_invalid_triggers
        self.on_enter = listify(on_enter) if on_enter else []
        self.on_exit = listify(on_exit) if on_exit else []

    @property
    def name(self):
        if isinstance(self._name, Enum):
            return self._name.name
        else:
            return self._name

    @property
    def value(self):
        return self._name

    def enter(self, event_data):
        event_data.machine.callbacks(self.on_enter, event_data)

    def exit(self, event_data):
        event_data.machine.callbacks(self.on_exit, event_data)

    def add_callback(self, trigger, func):
        callback_list = getattr(self, 'on_' + trigger)
        callback_list.append(func)

    def __repr__(self):
        return "<%s('%s')@%s>" % (type(self).__name__, self.name, id(self))


class Condition(object):
    def __init__(self, func, target=True):
        self.func = func
        self.target = target

    def check(self, event_data):
        predicate = event_data.machine.resolve_callable(self.func, event_data)
        if event_data.machine.send_event:
            return predicate(event_data) == self.target
        return predicate(*event_data.args, **event_data.kwargs) == self.target

    def __repr__(self):
        return "<%s(%s)@%s>" % (type(self).__name__, self.func, id(self))


class Transition(object):
    dynamic_methods = ['before', 'after', 'prepare']
    condition_cls = Condition

    def __init__(self, source, dest, conditions=None, unless=None, before=None,
                 after=None, prepare=None):
        self.source = source
        self.dest = dest
        self.prepare = [] if prepare is None else listify(prepare)
        self.before = [] if before is None else listify(before)
        self.after = [] if after is None else listify(after)

        self.conditions = []
        if conditions is not None:
            for cond in listify(conditions):
                self.conditions.append(self.condition_cls(cond))
        if unless is not None:
            for cond in listify(unless):
                self.conditions.append(self.condition_cls(cond, target=False))

    def _eval_conditions(self, event_data):
        for cond in self.conditions:
            if not cond.check(event_data):
                return False
        return True

    def execute(self, event_data):

        event_data.machine.callbacks(self.prepare, event_data)

        if not self._eval_conditions(event_data):
            return False

        event_data.machine.callbacks(itertools.chain(
            event_data.machine.before_state_change, self.before), event_data)

        if self.dest:  # if self.dest is None this is an internal transition with no actual state change
            self._change_state(event_data)

        event_data.machine.callbacks(itertools.chain(
            self.after, event_data.machine.after_state_change), event_data)
        return True

    def _change_state(self, event_data):
        event_data.machine.get_state(self.source).exit(event_data)
        event_data.machine.set_state(self.dest, event_data.model)
        event_data.update(
            getattr(event_data.model, event_data.machine.model_attribute))
        event_data.machine.get_state(self.dest).enter(event_data)

    def add_callback(self, trigger, func):
        callback_list = getattr(self, trigger)
        callback_list.append(func)

    def __repr__(self):
        return "<%s('%s', '%s')@%s>" % (type(self).__name__,
                                        self.source, self.dest, id(self))


class EventData(object):
    def __init__(self, state, event, machine, model, args, kwargs):

        self.state = state
        self.event = event
        self.machine = machine
        self.model = model
        self.args = args
        self.kwargs = kwargs
        self.transition = None
        self.error = None
        self.result = False

    def update(self, state):
        if not isinstance(state, State):
            self.state = self.machine.get_state(state)

    def __repr__(self):
        return "<%s('%s', %s)@%s>" % (type(self).__name__, self.state,
                                      getattr(self, 'transition'), id(self))


class Event(object):
    def __init__(self, name, machine):
        self.name = name
        self.machine = machine
        self.transitions = defaultdict(list)

    def add_transition(self, transition):
        self.transitions[transition.source].append(transition)

    def trigger(self, model, *args, **kwargs):
        func = partial(self._trigger, model, *args, **kwargs)
        return self.machine._process(func)

    def _trigger(self, model, *args, **kwargs):
        state = self.machine.get_model_state(model)
        if state.name not in self.transitions:
            msg = "%sCan't trigger event %s from state %s!" % (self.machine.name, self.name,
                                                               state.name)
            ignore = state.ignore_invalid_triggers if state.ignore_invalid_triggers is not None \
                else self.machine.ignore_invalid_triggers
            if ignore:
                _LOGGER.warning(msg)
                return False
            else:
                raise MachineError(msg)
        event_data = EventData(state, self, self.machine,
                               model, args=args, kwargs=kwargs)
        return self._process(event_data)

    def _process(self, event_data):
        self.machine.callbacks(self.machine.prepare_event, event_data)
        try:
            for trans in self.transitions[event_data.state.name]:
                event_data.transition = trans
                if trans.execute(event_data):
                    event_data.result = True
                    break
        except Exception as err:
            event_data.error = err
            if self.machine.on_exception:
                self.machine.callbacks(self.machine.on_exception, event_data)
            else:
                raise
        finally:
            try:
                self.machine.callbacks(self.machine.finalize_event, event_data)
            except Exception as err:
                pass

        return event_data.result

    def __repr__(self):
        return "<%s('%s')@%s>" % (type(self).__name__, self.name, id(self))

    def add_callback(self, trigger, func):

        for trans in itertools.chain(*self.transitions.values()):
            trans.add_callback(trigger, func)


class Machine(object):
    separator = '_'  # separates callback type from state/transition name
    wildcard_all = '*'  # will be expanded to ALL states
    wildcard_same = '='  # will be expanded to source state
    state_cls = State
    transition_cls = Transition
    event_cls = Event

    def __init__(self, model='self', states=None, initial='initial', transitions=None,
                 send_event=False, auto_transitions=True,
                 ordered_transitions=False, ignore_invalid_triggers=None,
                 before_state_change=None, after_state_change=None, name=None,
                 queued=False, prepare_event=None, finalize_event=None, model_attribute='state', on_exception=None,
                 **kwargs):

        try:
            super(Machine, self).__init__(**kwargs)
        except TypeError as err:
            raise ValueError('Passing arguments {0} caused an inheritance error: {1}'.format(
                kwargs.keys(), err))

        self._queued = queued
        self._transition_queue = deque()
        self._before_state_change = []
        self._after_state_change = []
        self._prepare_event = []
        self._finalize_event = []
        self._on_exception = []
        self._initial = None

        self.states = OrderedDict()
        self.events = {}
        self.send_event = send_event
        self.auto_transitions = auto_transitions
        self.ignore_invalid_triggers = ignore_invalid_triggers
        self.prepare_event = prepare_event
        self.before_state_change = before_state_change
        self.after_state_change = after_state_change
        self.finalize_event = finalize_event
        self.on_exception = on_exception
        self.name = name + ": " if name is not None else ""
        self.model_attribute = model_attribute

        self.models = []

        if states is not None:
            self.add_states(states)

        if initial is not None:
            self.initial = initial

        if transitions is not None:
            self.add_transitions(transitions)

        if ordered_transitions:
            self.add_ordered_transitions()

        if model:
            self.add_model(model)

    def add_model(self, model, initial=None):
        models = listify(model)

        if initial is None:
            if self.initial is None:
                raise ValueError(
                    "No initial state configured for machine, must specify when adding model.")
            else:
                initial = self.initial

        for mod in models:
            mod = self if mod == 'self' else mod
            if mod not in self.models:
                self._checked_assignment(
                    mod, 'trigger', partial(self._get_trigger, mod))

                for trigger in self.events:
                    self._add_trigger_to_model(trigger, mod)

                for state in self.states.values():
                    self._add_model_to_state(state, mod)

                self.set_state(initial, model=mod)
                self.models.append(mod)

    def remove_model(self, model):

        models = listify(model)

        for mod in models:
            self.models.remove(mod)
        if len(self._transition_queue) > 0:
            # the first element of the list is currently executed. Keeping it for further Machine._process(ing)
            self._transition_queue = deque(
                [self._transition_queue[0]] + [e for e in self._transition_queue if e.args[0] not in models])

    @classmethod
    def _create_transition(cls, *args, **kwargs):
        return cls.transition_cls(*args, **kwargs)

    @classmethod
    def _create_event(cls, *args, **kwargs):
        return cls.event_cls(*args, **kwargs)

    @classmethod
    def _create_state(cls, *args, **kwargs):
        return cls.state_cls(*args, **kwargs)

    @property
    def initial(self):
        """ Return the initial state. """
        return self._initial

    @initial.setter
    def initial(self, value):
        if isinstance(value, State):
            if value.name not in self.states:
                self.add_state(value)
            else:
                _ = self._has_state(value, raise_error=True)
            self._initial = value.name
        else:
            state_name = value.name if isinstance(value, Enum) else value
            if state_name not in self.states:
                self.add_state(state_name)
            self._initial = state_name

    @property
    def has_queue(self):
        return self._queued

    @property
    def model(self):
        if len(self.models) == 1:
            return self.models[0]
        return self.models

    @property
    def before_state_change(self):
        return self._before_state_change

    # this should make sure that _before_state_change is always a list
    @before_state_change.setter
    def before_state_change(self, value):
        self._before_state_change = listify(value)

    @property
    def after_state_change(self):
        return self._after_state_change

    # this should make sure that _after_state_change is always a list
    @after_state_change.setter
    def after_state_change(self, value):
        self._after_state_change = listify(value)

    @property
    def prepare_event(self):
        """Callbacks executed when an event is triggered."""
        return self._prepare_event

    # this should make sure that prepare_event is always a list
    @prepare_event.setter
    def prepare_event(self, value):
        self._prepare_event = listify(value)

    @property
    def finalize_event(self):
        return self._finalize_event

    # this should make sure that finalize_event is always a list
    @finalize_event.setter
    def finalize_event(self, value):
        self._finalize_event = listify(value)

    @property
    def on_exception(self):
        """Callbacks will be executed when an Event raises an Exception."""
        return self._on_exception

    # this should make sure that finalize_event is always a list
    @on_exception.setter
    def on_exception(self, value):
        self._on_exception = listify(value)

    def get_state(self, state):
        """ Return the State instance with the passed name. """
        if isinstance(state, Enum):
            state = state.name
        if state not in self.states:
            raise ValueError("State '%s' is not a registered state." % state)
        return self.states[state]


    def is_state(self, state, model):
        return getattr(model, self.model_attribute) == state

    def get_model_state(self, model):
        return self.get_state(getattr(model, self.model_attribute))

    def set_state(self, state, model=None):

        if not isinstance(state, State):
            state = self.get_state(state)
        models = self.models if model is None else listify(model)

        for mod in models:
            setattr(mod, self.model_attribute, state.value)

    def add_state(self, *args, **kwargs):
        """ Alias for add_states. """
        self.add_states(*args, **kwargs)

    def add_states(self, states, on_enter=None, on_exit=None,
                   ignore_invalid_triggers=None, **kwargs):


        ignore = ignore_invalid_triggers
        if ignore is None:
            ignore = self.ignore_invalid_triggers

        states = listify(states)

        for state in states:
            if isinstance(state, (string_types, Enum)):
                state = self._create_state(
                    state, on_enter=on_enter, on_exit=on_exit,
                    ignore_invalid_triggers=ignore, **kwargs)
            elif isinstance(state, dict):
                if 'ignore_invalid_triggers' not in state:
                    state['ignore_invalid_triggers'] = ignore
                state = self._create_state(**state)
            self.states[state.name] = state
            for model in self.models:
                self._add_model_to_state(state, model)
            if self.auto_transitions:
                for a_state in self.states.keys():
                    # add all states as sources to auto transitions 'to_<state>' with dest <state>
                    if a_state == state.name:
                        if self.model_attribute == 'state':
                            method_name = 'to_%s' % a_state
                        else:
                            method_name = 'to_%s_%s' % (
                                self.model_attribute, a_state)
                            self.add_transition('to_%s' % a_state, self.wildcard_all, a_state,
                                                prepare=partial(_warning_wrapper_to, 'to_%s' % a_state))
                        self.add_transition(
                            method_name, self.wildcard_all, a_state)

                    # add auto transition with source <state> to <a_state>
                    else:
                        if self.model_attribute == 'state':
                            method_name = 'to_%s' % a_state
                        else:
                            method_name = 'to_%s_%s' % (
                                self.model_attribute, a_state)
                            self.add_transition('to_%s' % a_state, state.name, a_state,
                                                prepare=partial(_warning_wrapper_to, 'to_%s' % a_state))
                        self.add_transition(method_name, state.name, a_state)

    def _add_model_to_state(self, state, model):
        func = partial(self.is_state, state.value, model)
        if self.model_attribute == 'state':
            method_name = 'is_%s' % state.name
        else:
            method_name = 'is_%s_%s' % (self.model_attribute, state.name)
            self._checked_assignment(model, 'is_%s' % state.name, partial(
                _warning_wrapper_is, method_name, func))
        self._checked_assignment(model, method_name, func)

        for callback in self.state_cls.dynamic_methods:
            method = "{0}_{1}".format(callback, state.name)
            if hasattr(model, method) and inspect.ismethod(getattr(model, method)) and \
                    method not in getattr(state, callback):
                state.add_callback(callback[3:], method)

    def _checked_assignment(self, model, name, func):
        if hasattr(model, name):
            _LOGGER.warning(
                "%sModel already contains an attribute '%s'. Skip binding.", self.name, name)
        else:
            setattr(model, name, func)

    def _add_trigger_to_model(self, trigger, model):
        self._checked_assignment(model, trigger, partial(
            self.events[trigger].trigger, model))

    def _get_trigger(self, model, trigger_name, *args, **kwargs):
        try:
            event = self.events[trigger_name]
        except KeyError:
            state = self.get_model_state(model)
            ignore = state.ignore_invalid_triggers if state.ignore_invalid_triggers is not None \
                else self.ignore_invalid_triggers
            if not ignore:
                raise AttributeError(
                    "Do not know event named '%s'." % trigger_name)
            return False
        return event.trigger(model, *args, **kwargs)

    def get_triggers(self, *args):
        names = set([state.name if hasattr(state, 'name')
                    else state for state in args])
        return [t for (t, ev) in self.events.items() if any(name in ev.transitions for name in names)]

    def add_transition(self, trigger, source, dest, conditions=None,
                       unless=None, before=None, after=None, prepare=None, **kwargs):

        if trigger == self.model_attribute:
            raise ValueError(
                "Trigger name cannot be same as model attribute name.")
        if trigger not in self.events:
            self.events[trigger] = self._create_event(trigger, self)
            for model in self.models:
                self._add_trigger_to_model(trigger, model)

        if source == self.wildcard_all:
            source = list(self.states.keys())
        else:
            source = [s.name if isinstance(s, State) and self._has_state(s, raise_error=True) or hasattr(s, 'name') else
                      s for s in listify(source)]

        for state in source:
            if dest == self.wildcard_same:
                _dest = state
            elif dest is not None:
                if isinstance(dest, State):
                    _ = self._has_state(dest, raise_error=True)
                _dest = dest.name if hasattr(dest, 'name') else dest
            else:
                _dest = None
            _trans = self._create_transition(state, _dest, conditions, unless, before,
                                             after, prepare, **kwargs)
            self.events[trigger].add_transition(_trans)

    def add_transitions(self, transitions):

        for trans in listify(transitions):
            if isinstance(trans, list):
                self.add_transition(*trans)
            else:
                self.add_transition(**trans)

    def add_ordered_transitions(self, states=None, trigger='next_state',
                                loop=True, loop_includes_initial=True,
                                conditions=None, unless=None, before=None,
                                after=None, prepare=None, **kwargs):

        if states is None:
            states = list(self.states.keys())  # need to listify for Python3
        len_transitions = len(states)
        if len_transitions < 2:
            raise ValueError("Can't create ordered transitions on a Machine "
                             "with fewer than 2 states.")
        if not loop:
            len_transitions -= 1
        conditions = _prep_ordered_arg(len_transitions, conditions)
        unless = _prep_ordered_arg(len_transitions, unless)
        before = _prep_ordered_arg(len_transitions, before)
        after = _prep_ordered_arg(len_transitions, after)
        prepare = _prep_ordered_arg(len_transitions, prepare)
        try:
            idx = states.index(self._initial)
            states = states[idx:] + states[:idx]
            first_in_loop = states[0 if loop_includes_initial else 1]
        except ValueError:
            first_in_loop = states[0]

        for i in range(0, len(states) - 1):
            self.add_transition(trigger, states[i], states[i + 1],
                                conditions=conditions[i],
                                unless=unless[i],
                                before=before[i],
                                after=after[i],
                                prepare=prepare[i],
                                **kwargs)
        if loop:
            self.add_transition(trigger, states[-1],
                                first_in_loop,
                                conditions=conditions[-1],
                                unless=unless[-1],
                                before=before[-1],
                                after=after[-1],
                                prepare=prepare[-1],
                                **kwargs)

    def get_transitions(self, trigger="", source="*", dest="*"):

        if trigger:
            try:
                events = (self.events[trigger], )
            except KeyError:
                return []
        else:
            events = self.events.values()
        transitions = []
        for event in events:
            transitions.extend(
                itertools.chain.from_iterable(event.transitions.values()))
        target_source = source.name if hasattr(
            source, 'name') else source if source != "*" else ""
        target_dest = dest.name if hasattr(
            dest, 'name') else dest if dest != "*" else ""
        return [transition
                for transition in transitions
                if (transition.source, transition.dest) == (target_source or transition.source,
                                                            target_dest or transition.dest)]

    def remove_transition(self, trigger, source="*", dest="*"):

        source = listify(source) if source != "*" else source
        dest = listify(dest) if dest != "*" else dest
        tmp = {key: value for key, value in
               {k: [t for t in v
                    if (source != "*" and t.source not in source) or (dest != "*" and t.dest not in dest)]
                for k, v in self.events[trigger].transitions.items()}.items()
               if len(value) > 0}
        if tmp:
            self.events[trigger].transitions = defaultdict(list, **tmp)
        else:
            for model in self.models:
                delattr(model, trigger)
            del self.events[trigger]

    def dispatch(self, trigger, *args, **kwargs):

        return all([getattr(model, trigger)(*args, **kwargs) for model in self.models])

    def callbacks(self, funcs, event_data):
        for func in funcs:
            self.callback(func, event_data)
            _LOGGER.info("%sExecuted callback '%s'", self.name, func)

    def callback(self, func, event_data):
        func = self.resolve_callable(func, event_data)
        if self.send_event:
            func(event_data)
        else:
            func(*event_data.args, **event_data.kwargs)

    @staticmethod
    def resolve_callable(func, event_data):
        if isinstance(func, string_types):
            try:
                func = getattr(event_data.model, func)
                if not callable(func):
                    def func_wrapper(*_, **__):  # properties cannot process parameters
                        return func
                    return func_wrapper
            except AttributeError:
                try:
                    mod, name = func.rsplit('.', 1)
                    m = __import__(mod)
                    for n in mod.split('.')[1:]:
                        m = getattr(m, n)
                    func = getattr(m, name)
                except (ImportError, AttributeError, ValueError):
                    raise AttributeError("Callable with name '%s' could neither be retrieved from the passed "
                                         "model nor imported from a module." % func)
        return func

    def _has_state(self, state, raise_error=False):
        found = state in self.states.values()
        if not found and raise_error:
            msg = 'State %s has not been added to the machine' % (
                state.name if hasattr(state, 'name') else state)
            raise ValueError(msg)
        return found

    def _process(self, trigger):

        if not self.has_queue:
            if not self._transition_queue:
                return trigger()
            else:
                raise MachineError(
                    "Attempt to process events synchronously while transition queue is not empty!")

        self._transition_queue.append(trigger)
        if len(self._transition_queue) > 1:
            return True

        while self._transition_queue:
            try:
                self._transition_queue[0]()
                self._transition_queue.popleft()
            except Exception:
                self._transition_queue.clear()
                raise
        return True

    @classmethod
    def _identify_callback(cls, name):
        for callback in itertools.chain(cls.state_cls.dynamic_methods, cls.transition_cls.dynamic_methods):
            if name.startswith(callback):
                callback_type = callback
                break
        else:
            return None, None

        target = name[len(callback_type) + len(cls.separator):]

        if target == '' or name[len(callback_type)] != cls.separator:
            return None, None

        return callback_type, target

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError("'{}' does not exist on <Machine@{}>"
                                 .format(name, id(self)))

        callback_type, target = self._identify_callback(name)

        if callback_type is not None:
            if callback_type in self.transition_cls.dynamic_methods:
                if target not in self.events:
                    raise AttributeError("event '{}' is not registered on <Machine@{}>"
                                         .format(target, id(self)))
                return partial(self.events[target].add_callback, callback_type)

            elif callback_type in self.state_cls.dynamic_methods:
                state = self.get_state(target)
                return partial(state.add_callback, callback_type[3:])

        try:
            return self.__getattribute__(name)
        except AttributeError:
            raise AttributeError(
                "'{}' does not exist on <Machine@{}>".format(name, id(self)))


class MachineError(Exception):
    def __init__(self, value):
        super(MachineError, self).__init__(value)
        self.value = value

    def __str__(self):
        return repr(self.value)

def _warning_wrapper_is(meth_name, func, *args, **kwargs):
    warnings.warn("Starting from transitions version 0.8.3, 'is_<state_name>' convenience functions will be"
                  " assigned to 'is_<model_attribute>_<state_name>' when 'model_attribute "
                  "!= \"state\"'. In 0.9.0, 'is_<state_name>' will NOT be assigned anymore when "
                  "'model_attribute != \"state\"'! Please adjust your code and use "
                  "'{0}' instead.".format(meth_name), DeprecationWarning)
    return func(*args, **kwargs)


def _warning_wrapper_to(meth_name, *args, **kwargs):
    warnings.warn("Starting from transitions version 0.8.3, 'to_<state_name>' convenience functions will be"
                  " assigned to 'to_<model_attribute>_<state_name>' when 'model_attribute "
                  "!= \"state\"'. In 0.9.0, 'to_<state_name>' will NOT be assigned anymore when "
                  "'model_attribute != \"state\"'! Please adjust your code and use "
                  "'{0}' instead.".format(meth_name), DeprecationWarning)
