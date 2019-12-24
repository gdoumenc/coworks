import os

from coworks import *


class App(TechMicroService):

    def get(self, param1, param2="re", param3=[]):
        value = print(f'{param1} - {param2} - {param3}')
        return value


app = App()

if __name__ == '__main__':
    app.run()
