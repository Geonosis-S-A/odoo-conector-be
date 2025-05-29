class EmployeeNotFound(Exception):
    pass


class UserAlreadyExists(Exception):
    pass


class UserNotFound(Exception):
    pass


class OTPNotFound(Exception):
    pass


class PasswordNotMatch(Exception):
    pass


class UserInactive(Exception):
    pass


class PasswordUpdateError(Exception):
    pass


class TokenNotFound(Exception):
    pass


class TokenRevoked(Exception):
    pass
