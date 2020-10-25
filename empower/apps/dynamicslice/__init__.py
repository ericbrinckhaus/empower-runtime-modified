
"""Change slice quantum according to Network state"""

from empower.core.app import EVERY

MANIFEST = {
    "label": "Dynamic slice quantum",
    "desc": "Change slice quantum according to Network state",
    "modules": ['lvapp'],
    "params": {
        "slice_id": {
            "desc": "The slice update quantum.",
            "mandatory": True,
            "default": 0,
            "type": "int"
        },
        "every": {
            "desc": "The control loop period (in ms).",
            "mandatory": False,
            "default": EVERY,
            "type": "int"
        }
    }
}