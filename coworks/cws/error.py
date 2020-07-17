class CwsError(Exception):
    def __init__(self, message):
        self.msg = message


class CwsClientError(CwsError):
    pass


class CwsCommandError(CwsError):
    pass
