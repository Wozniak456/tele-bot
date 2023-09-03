from telegram import PollAnswer

class User:
    def __init__(self, id, name, password):
        self.id = id
        self.name = name
        self.password = password
