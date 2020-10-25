
"""WiFi Network statistics"""

from empower.core.app import EVERY

MANIFEST = {
    "label": "WiFi Network statistics",
    "desc": "WiFi Network statistics",
    "modules": ['lvapp'],
    "params": {
        "every": {
            "desc": "The control loop period (in ms).",
            "mandatory": False,
            "default": EVERY,
            "type": "int"
        }
    }
}