from coworks import Blueprint


class BP(Blueprint):

    def get_test(self, index):
        return f"blueprint test {index}"

    def get_extended_test(self, index):
        return f"blueprint extended test {index}"
