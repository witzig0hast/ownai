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


class NotAdmin(APIError):
    def __init__(self, message: str = "Nur für Administratoren."):
        super().__init__(403, "not_admin", message)


class RegistrationClosed(APIError):
    def __init__(self, message: str = "Registrierung ist aktuell geschlossen."):
        super().__init__(403, "registration_closed", message)


class SystemPaused(APIError):
    def __init__(self, message: str = "Das System ist aktuell pausiert."):
        super().__init__(503, "system_paused", message)


class InvalidAgentKey(APIError):
    def __init__(self, message: str = "Ungültiger Agent-Schlüssel."):
        super().__init__(401, "invalid_agent_key", message)


class AgentNameTaken(APIError):
    def __init__(self, message: str = "Dieser Agent-Name ist bereits vergeben."):
        super().__init__(409, "agent_name_taken", message)


class AgentNotFound(APIError):
    def __init__(self, message: str = "Agent nicht gefunden."):
        super().__init__(404, "agent_not_found", message)
