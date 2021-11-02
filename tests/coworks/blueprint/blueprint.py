from unittest.mock import Mock

from coworks import Blueprint
from coworks import entry
from coworks.globals import aws_context
from coworks.globals import aws_event
from ..ms import TechMS


class BP(Blueprint):

    @entry
    def get_test(self, index):
        return f"blueprint BP {index}"

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
            self.do_before_first_activation(aws_event, aws_context)

        @self.before_app_request
        def before_activation():
            self.do_before_activation(aws_event, aws_context)

        @self.after_app_request
        def after_activation(response):
            self.do_after_activation(response)
            return response


class DocumentedMS(TechMS):

    def token_authorizer(self, token):
        return True

    @entry
    def get(self):
        """Root access."""
        return "get"

    @entry
    def post_content(self, value, other="none"):
        """Add content."""
        return f"post_content {value}{other}"

    @entry
    def post_contentannotated(self, value: int, other: str = "none"):
        """Add content."""
        return f"post_content {value}{other}"

    @entry
    def get_list(self, values: [int]):
        """Tests list param."""
        return "ok"


class HiddenBlueprint(Blueprint):

    @entry
    def get(self):
        """Test not in routes."""
        return "ok"
