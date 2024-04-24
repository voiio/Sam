import os
from urllib.parse import ParseResult, urlparse

#: PostgreSQL URL to connect to the database. WARNING: You should ALWAYS use read-only credentials.
POSTGRESQL_URL: ParseResult = urlparse(os.getenv("POSTGRESQL_URL", "postgresql:///"))

USERNAME = POSTGRESQL_URL.username
PASSWORD = POSTGRESQL_URL.password
DATABASE = POSTGRESQL_URL.path[1:]
HOSTNAME = POSTGRESQL_URL.hostname
PORT = POSTGRESQL_URL.port
