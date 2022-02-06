#-*- coding: utf-8 -*-


class Singleton(object):
    instance = None
    def __new__(cls, *args, **kwargs):
        if not isinstance(cls.instance, cls):
            cls.instance = object.__new__(cls)
        return cls.instance
