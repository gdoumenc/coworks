from coworks import Blueprint
from coworks import entry


class TestBlueprint(Blueprint):
    """Test blueprint.
    This blueprint proposes a template blueprint for CI/CD purpose.

    It has a single get entry for testing purpose.

    .. versionchanged:: 0.7.3
        Added.
    """

    def __init__(self, name='test', **kwargs):
        super().__init__(name=name, **kwargs)

    @property
    def test_workspaces(self):
        return ['dev']

    @entry(stage='dev')
    def post_reset(self):
        """Entry to reset the test environment."""
        return 'ok'

    @entry(stage='dev')
    def get(self):
        """Test entry.

        Returns the next entry test case if needed. {'path':..., 'expected value':...}
        """
        self.post_reset()
        self.test()
        self.post_reset()

    def test(self):
        return 'ok'
