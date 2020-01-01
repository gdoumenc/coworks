import os

from collections import defaultdict

from coworks import *


class App(TechMicroService):
    values = defaultdict(int)

    def get(self, usage="test"):
        return f"Simple microservice for {usage}.\n"

    def get_value(self, index):
        return f"{self.values[index]}\n"

    def put_value(self, index, value=0):
        self.values[index] = value
        return value

    def get_env(self):
        return f"Simple microservice for {os.getenv('test')}.\n"


app = App()

if __name__ == '__main__':
    app.run()
