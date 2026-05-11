class DebtResolverError(Exception):
    pass


class UserNotFoundError(DebtResolverError):
    pass


class LoanNotFoundError(DebtResolverError):
    pass


class EntryNotFoundError(DebtResolverError):
    pass


class InvalidAmountError(DebtResolverError):
    pass


class InvalidDateError(DebtResolverError):
    pass
