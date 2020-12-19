
"""WiFi Network manager"""

from empower.core.app import EVERY

MANIFEST = {
    "label": "WiFi Network manager",
    "desc": "WiFi Network manager",
    "modules": ['lvapp'],
    "params": {
        "every": {
            "desc": "The update loop period (in ms).",
            "mandatory": False,
            "default": EVERY*3,
            "type": "int"
        }
    }
}