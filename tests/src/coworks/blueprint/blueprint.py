from coworks import Blueprint, entry


class BP(Blueprint):

    @entry
    def get_test(self, index):
        return f"blueprint test {index}"

    @entry
    def get_extended_test(self, index):
        return f"blueprint extended test {index}"
