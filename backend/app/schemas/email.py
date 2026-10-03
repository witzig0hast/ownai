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
    # Both false until an EmailAccount exists at all (has_custom_account above covers SMTP) -
    # separate from it since a user can have SMTP connected without ever setting up IMAP.
    has_imap_account: bool = False
    inbound_agent_enabled: bool = False


class ImapConnectRequest(BaseModel):
    imap_host: str
    imap_port: int = 993
    imap_username: str
    imap_password: str


class ImapConnectResponse(BaseModel):
    connected: bool = True


class InboundAgentEnabledRequest(BaseModel):
    enabled: bool
