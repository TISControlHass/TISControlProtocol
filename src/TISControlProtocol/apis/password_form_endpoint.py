from homeassistant.components.http import HomeAssistantView


class PasswordFormEndpoint(HomeAssistantView):
    """TIS API endpoint."""

    url = "/api/password-form"
    name = "api:password-form"
    requires_auth = False

    def __init__(self): ...

    def get(self, request): ...
