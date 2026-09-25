class APIError(Exception):
    """Raised anywhere in the app to produce the {"error": {"code", "message"}} envelope from API.md."""

    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class InvalidCredentials(APIError):
    def __init__(self, message: str = "E-Mail oder Passwort falsch."):
        super().__init__(401, "invalid_credentials", message)


class InvalidRefreshToken(APIError):
    def __init__(self, message: str = "Refresh-Token ungültig oder abgelaufen."):
        super().__init__(401, "invalid_refresh_token", message)


class EmailTaken(APIError):
    def __init__(self, message: str = "Diese E-Mail-Adresse ist bereits registriert."):
        super().__init__(409, "email_taken", message)


class NotAuthenticated(APIError):
    def __init__(self, message: str = "Nicht authentifiziert."):
        super().__init__(401, "not_authenticated", message)


class InvalidDeviceKey(APIError):
    def __init__(self, message: str = "Ungültiger Geräteschlüssel."):
        super().__init__(401, "invalid_device_key", message)


class NotFound(APIError):
    def __init__(self, message: str = "Nicht gefunden."):
        super().__init__(404, "not_found", message)


class CalendarNotConnected(APIError):
    def __init__(self, message: str = "Kein CalDAV-Kalender verbunden."):
        super().__init__(409, "calendar_not_connected", message)


class NotImplementedYet(APIError):
    def __init__(self, message: str = "Noch nicht implementiert."):
        super().__init__(501, "not_implemented", message)
