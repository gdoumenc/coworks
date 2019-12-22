from coworks import *


class App(BizMicroService):
    pass


app = App("arn:aws:states:eu-west-1:848422798754:stateMachine:HelloWorld")

if __name__ == '__main__':
    app.run()
