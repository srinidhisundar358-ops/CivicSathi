BACKEND = 8000
DOCUMENTS = 8101
DIGILOCKER = 8102
FORMFILL = 8103
SERVICES = 8201
INBOX = 8202
DEADLINES = 8301


def mcp_url(port: int, host: str = 'localhost') -> str:
    return f'http://{host}:{port}/mcp'
