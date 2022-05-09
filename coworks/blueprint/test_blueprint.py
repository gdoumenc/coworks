from werkzeug.exceptions import BadRequest

from coworks import Blueprint
from coworks import entry
from coworks.utils import get_app_workspace


class TestBlueprint(Blueprint):
    """Test blueprint.
    This blueprint proposes a template blueprint for CI/CD purpose.

    It has a single get entry for testing purpose.

    .. versionchanged:: 0.7.3
        Added.
    """

    def __init__(self, name='test', **kwargs):
        super().__init__(name=name, **kwargs)

        @self.before_request
        def check():
            if get_app_workspace() not in self.test_workspaces:
                raise BadRequest("Entry accessible only in test environment")

    @property
    def test_workspaces(self):
        return ['dev']

    @entry
    def post_reset(self):
        """Entry to reset the test environment."""
        return 'ok'

    @entry
    def get(self):
        """Test entry.

        Returns the next entry test case if needed. {'path':..., 'expected value':...}
        """
        self.post_reset()
        self.test()
        self.post_reset()

    def test(self):
        return 'ok'
