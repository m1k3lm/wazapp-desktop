#!/usr/bin/python
# -*- coding: utf-8 -*-

class Events(object):
    def getEventBindings(self):
        bindings = {}
        for methodname in dir(self):
            method = getattr(self, methodname)
            if hasattr(method, '_events'):
                bindings[method] = method._events
        return bindings

    @staticmethod
    def bind(event):
        def wrapper(func):
            if not hasattr(func, '_events'):
                func._events = []
            func._events.append(event)
            return func
        return wrapper


