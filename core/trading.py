def buy_shares(company, amount, cash):
    cost = company.price * amount
    if cash < cost:
        return cash, False  # not enough money

    company.player_owned += amount
    company.public_float -= amount
    cash -= cost
    return cash, True


def sell_shares(company, amount, cash):
    if amount > company.player_owned:
        return cash, False  # cannot sell more than owned

    revenue = company.price * amount
    company.player_owned -= amount
    company.public_float += amount
    cash += revenue
    return cash, True
