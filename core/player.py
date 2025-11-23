class Player:
    def __init__(self, name="Player", starting_cash=100000):
        self.name = name
        self.cash = float(starting_cash)

    def can_afford(self, cost):
        return self.cash >= cost

    def spend(self, amount):
        self.cash -= amount

    def earn(self, amount):
        self.cash += amount
