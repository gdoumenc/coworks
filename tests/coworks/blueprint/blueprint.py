from unittest.mock import Mock

from coworks import Blueprint, entry
from coworks.globals import event, context

class BP(Blueprint):

    @entry
    def get_test(self, index):
        return f"blueprint test {index}"

    @entry
    def get_extended_test(self, index):
        return f"blueprint extended test {index}"


class InitBP(BP):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_before_first_activation = Mock()
        self.do_before_activation = Mock()
        self.do_after_activation = Mock()

        @self.before_app_first_request
        def before_first_activation():
            self.do_before_first_activation(event, context)

        @self.before_app_request
        def before_activation():
            self.do_before_activation(event, context)

        @self.after_app_request
        def after_activation(response):
            self.do_after_activation(response)
            return response
