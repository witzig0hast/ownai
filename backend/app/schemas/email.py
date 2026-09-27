from pydantic import BaseModel


class EmailConnectRequest(BaseModel):
    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    from_address: str
    use_tls: bool = True


class EmailConnectResponse(BaseModel):
    connected: bool = True


class EmailStatusOut(BaseModel):
    has_custom_account: bool
    effective_from_address: str | None
