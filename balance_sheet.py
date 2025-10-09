class LineItem:

    def __init__(self, name: str, amount: float):

        self.name = name
        self.amount = amount

    def __repr__(self):
        return f'{self.name}: {self.amount}'


class Category:

    def __init__(self, name: str):
        
        self.name = name
        self.items = []
        self.total = 0
        
    def add_item(self, item: LineItem):

        self.items.append(item)
        self.total_amount()

    def total_amount(self) -> float:
        
        self.total = sum([item.amount for item in self.items])

        return self.total

    def __repr__(self):

        lines = "\n    ".join(repr(i) for i in self.items)
        
        return f"{self.name}:\n    {lines}\n  Total {self.name}: {self.total:,.2f}"


class Section:

    def __init__(self, name: str):

        self.name = name
        self.items = []
        self.total = 0
        
    def add_category(self, item: Category):
        
        self.items.append(item)
        self.total_amount()

    def total_amount(self) -> float:
        
        self.total = sum([item.total for item in self.items])
        
        return self.total

    def __repr__(self):

        lines = "\n    ".join(repr(i) for i in self.items)
        
        return f"{self.name}:\n    {lines}\n  Total {self.name}: {self.total:,.2f}"


class BalanceSheet:
    
    def __init__(self, date: str):
        
        self.date = date
        self.assets = Section("Assets")
        self.liabilities = Section("Liabilities")
        self.equity = Section("Equity")

    def is_balanced(self) -> bool:
        
        return abs(self.assets.total_amount() - (self.liabilities.total_amount() + self.equity.total_amount())) < 1e-6

    def __repr__(self):
        
        return (
            f"\nBALANCE SHEET as of {self.date}\n"
            f"{'-'*40}\n"
            f"{self.assets}\n\n{self.liabilities}\n\n{self.equity}\n"
            f"{'-'*40}\n"
            f"Assets: {self.assets.total_amount():,.2f}\n"
            f"Liab + Eq: {self.liabilities.total_amount() + self.equity.total_amount():,.2f}\n"
            f"Balanced? {'Yes' if self.is_balanced() else 'No'}"
        )


# --- Current Assets ---
cash = LineItem("Cash", 10_000)
accounts_receivable = LineItem("Accounts Receivable", 5_000)
inventory = LineItem("Inventory", 8_000)

current_assets = Category("Current Assets")
current_assets.add_item(cash)
current_assets.add_item(accounts_receivable)
current_assets.add_item(inventory)

# --- Non-current Assets ---
equipment = LineItem("Equipment", 20_000)
land = LineItem("Land", 15_000)
noncurrent_assets = Category("Non-current Assets")
noncurrent_assets.add_item(equipment)
noncurrent_assets.add_item(land)

# --- Current Liabilities ---
accounts_payable = LineItem("Accounts Payable", 6_000)
short_term_loan = LineItem("Short-term Loan", 4_000)
current_liabilities = Category("Current Liabilities")
current_liabilities.add_item(accounts_payable)
current_liabilities.add_item(short_term_loan)

# --- Equity ---
owner_equity = LineItem("Owner’s Capital", 48_000)
equity_cat = Category("Equity")
equity_cat.add_item(owner_equity)

# --- Build the sheet ---
bs = BalanceSheet(date="2025-10-08")
bs.assets.add_category(current_assets)
bs.assets.add_category(noncurrent_assets)
bs.liabilities.add_category(current_liabilities)
bs.equity.add_category(equity_cat)

print(bs)
