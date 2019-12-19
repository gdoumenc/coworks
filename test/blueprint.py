from coworks import Blueprint


class BP(Blueprint):

    def get(self):
        return "blueprint root"

    def get_test(self, index):
        return f"blueprint test {index}"


class SlugBP(Blueprint):
    slug = 'slug'

    def get(self):
        return "blueprint root"

    def get_test(self, index):
        return f"blueprint test {index}"
