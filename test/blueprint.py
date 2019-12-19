from coworks import Blueprint


class BP(Blueprint):

    def get(self):
        return "blueprint root"

    def get_test(self, index):
        return f"blueprint test {index}"
