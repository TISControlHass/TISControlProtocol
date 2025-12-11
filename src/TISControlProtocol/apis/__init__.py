import TISControlProtocol.views as views
import TISControlProtocol.public as public
from .shared import STATIC_URL_PREFIX
import importlib.resources
from homeassistant.components.http import StaticPathConfig

from .tis_endpoint import TISEndPoint
from .scan_devices_endpoint import ScanDevicesEndPoint
from .get_key_endpoint import GetKeyEndpoint
from .change_password_endpoint import ChangeSecurityPassEndpoint
from .restart_endpoint import RestartEndpoint
from .update_endpoint import UpdateEndpoint
from .bill_config_endpoint import BillConfigEndpoint
from .get_bill_config_endpoint import GetBillConfigEndpoint
from .password_form_endpoint import PasswordFormEndpoint
from .submit_password import SubmitPasswordEndpoint
from .password_dashboard import PasswordDashboardEndpoint
from .passwords_endpoint import PasswordsEndpoint


__all__ = [
    "TISEndPoint",
    "ScanDevicesEndPoint",
    "GetKeyEndpoint",
    "ChangeSecurityPassEndpoint",
    "RestartEndpoint",
    "UpdateEndpoint",
    "BillConfigEndpoint",
    "GetBillConfigEndpoint",
    "SubmitPasswordEndpoint",
    "PasswordsEndpoint",
]


async def setup_views(hass):
    """
    1. Locate the absolute path of the 'views' folder.
    2. Register it as a static path in Home Assistant.
    3. Register the individual API views.
    """

    # Get absolute path to 'src/TISControlProtocol/views'
    views_path = str(importlib.resources.files(views))
    public_path = str(importlib.resources.files(public))

    # Register the ROOT views folder
    # Now, anything inside 'views/' is accessible via HTTP
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                url_path=STATIC_URL_PREFIX,
                path=public_path,
                cache_headers=True,
            )
        ]
    )
    hass.http.register_view(PasswordFormEndpoint(views_path))
    hass.http.register_view(PasswordDashboardEndpoint(views_path))
