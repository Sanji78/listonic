from homeassistant.components.application_credentials import AuthorizationServer, ClientCredential
from homeassistant.core import HomeAssistant
from .const import DOMAIN, GOOGLE_AUTH_URL, GOOGLE_TOKEN_URL

async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    return AuthorizationServer(
        authorize_url=GOOGLE_AUTH_URL,
        token_url=GOOGLE_TOKEN_URL,
    )

