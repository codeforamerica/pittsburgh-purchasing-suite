# -*- coding: utf-8 -*-

import re
import inspect
from copy import deepcopy

from flask import (
    render_template, current_app
)
from flask.views import View

from purchasing.decorators import logview

URL_PREFIX = '/sherpa'

class SherpaView(View):
    '''A generic sherpa view.
    '''
    methods = ['GET']
    decorators = [logview]

    def __init__(self, url=None):
        self.prefix = URL_PREFIX
        url = url if url else self.make_url(self.__class__.__name__)
        self.url = '/{}'.format(url).replace('//', '/').rstrip('/')
        self.blueprint = URL_PREFIX.lstrip('/')

    def make_url(self, url):
        new_url = re.sub(r"([A-Z])", r" \1", url).split()
        return '-'.join(new_url).lower()

    @staticmethod
    def get_url(self):
        return self.url

    def get_view_attributes(self):
        '''
        '''
        attributes = inspect.getmembers(self, lambda _self: not(inspect.isroutine(_self)))
        cls_attributes = [a for a in attributes if not(
            a[0].startswith('__') and a[0].endswith('__')
        ) and a[0] not in ['methods', 'decorators']]
        return dict(cls_attributes)

    def get_template_name(self):
        raise NotImplementedError()

    def build_url(self, obj):
        if 'url' in obj and 'external' not in obj:
            endpoint = '{}.{}'.format(self.blueprint, obj['url'].lower())
            try:
                obj['url'] = current_app.url_map.iter_rules(endpoint).next().rule
            except (KeyError, StopIteration):
                # TODO: handle this more intelligently.
                pass

        return obj

    def render_template(self):
        _view_attributes = self.get_view_attributes()
        view_attributes = deepcopy(_view_attributes)

        for name, val in view_attributes.iteritems():
            if isinstance(val, list):
                if len(val) == 0:
                    continue
                else:
                    val = [self.build_url(i) for i in val]
            elif isinstance(val, dict):
                val = self.build_url(val)
            else:
                continue

        return render_template(self.get_template_name(), **view_attributes)

    def dispatch_request(self):
        return self.render_template()

class QuestionNode(SherpaView):
    '''A question node
    '''
    def get_template_name(self):
        return 'sherpa/question.html'

class TerminationNode(SherpaView):
    '''A termination node
    '''
    def get_template_name(self):
        return 'sherpa/termination.html'

def register_endpoint(bp, obj):
    bp.add_url_rule(obj.get_url(obj), view_func=obj.as_view(obj.__class__.__name__.lower()))
