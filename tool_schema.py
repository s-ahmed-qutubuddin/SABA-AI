from __future__ import annotations


# Shared Gemini function-declaration schema used by BOTH:
#
#   1. backend/live_voice.py
#   2. ai.py
#
# Voice and text therefore receive the same tools.


TOOL_DECLARATIONS = [

    # -----------------------------------------------------------------------
    # Memory
    # -----------------------------------------------------------------------

    {
        "name": "remember",
        "description": (
            "Store a durable user memory for the current speaker."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "memory": {
                    "type": "STRING"
                },
                "category": {
                    "type": "STRING"
                },
            },
            "required": [
                "memory"
            ],
        },
    },

    {
        "name": "recall_memory",
        "description": (
            "Recall relevant stored memories for the current speaker."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING"
                },
                "limit": {
                    "type": "INTEGER"
                },
            },
            "required": [
                "query"
            ],
        },
    },

    {
        "name": "identify_family_member",
        "description": (
            "Switch the current speaker to a known Jamal family profile "
            "when they explicitly say who they are."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {
                    "type": "STRING"
                }
            },
            "required": [
                "name"
            ],
        },
    },

    {
        "name": "family_context",
        "description": (
            "Retrieve relevant family profiles and relationships."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING"
                },
                "limit": {
                    "type": "INTEGER"
                },
            },
            "required": [
                "query"
            ],
        },
    },

    # -----------------------------------------------------------------------
    # Notes / tasks / preferences
    # -----------------------------------------------------------------------

    {
        "name": "create_note",
        "description": "Create a note.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING"
                },
                "content": {
                    "type": "STRING"
                },
            },
            "required": [
                "title",
                "content",
            ],
        },
    },

    {
        "name": "create_task",
        "description": (
            "Create a task. due_date can be natural language or ISO text."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING"
                },
                "description": {
                    "type": "STRING"
                },
                "due_date": {
                    "type": "STRING"
                },
            },
            "required": [
                "title"
            ],
        },
    },

    {
        "name": "set_preference",
        "description": "Set a user preference.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "key": {
                    "type": "STRING"
                },
                "value": {
                    "type": "STRING"
                },
            },
            "required": [
                "key",
                "value",
            ],
        },
    },

    # -----------------------------------------------------------------------
    # macOS controls
    # -----------------------------------------------------------------------

    {
        "name": "open_allowed_app",
        "description": (
            "Open an allowlisted macOS application."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {
                    "type": "STRING",
                    "enum": [
                        "Safari",
                        "Google Chrome",
                        "Visual Studio Code",
                        "Terminal",
                        "Finder",
                        "Music",
                        "Notes",
                        "Spotify",
                    ],
                }
            },
            "required": [
                "name"
            ],
        },
    },

    {
        "name": "set_volume",
        "description": (
            "Set macOS output volume from 0 to 100."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "percent": {
                    "type": "INTEGER"
                }
            },
            "required": [
                "percent"
            ],
        },
    },

    {
        "name": "get_volume",
        "description": (
            "Get current macOS output volume."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },

    {
        "name": "media_control",
        "description": "Control Music playback.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": [
                        "play_pause",
                        "next",
                        "previous",
                        "stop",
                    ],
                }
            },
            "required": [
                "action"
            ],
        },
    },

    {
        "name": "battery_status",
        "description": (
            "Read basic Mac battery status."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },

    {
        "name": "system_info",
        "description": (
            "Read basic Mac system information."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },

    {
        "name": "clipboard_read",
        "description": (
            "Read the current clipboard text."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },

    {
        "name": "clipboard_write",
        "description": (
            "Write text to the clipboard."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text": {
                    "type": "STRING"
                }
            },
            "required": [
                "text"
            ],
        },
    },

    {
        "name": "open_url",
        "description": (
            "Open an http or https URL on the host Mac."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {
                    "type": "STRING"
                }
            },
            "required": [
                "url"
            ],
        },
    },

    # -----------------------------------------------------------------------
    # Web / utility
    # -----------------------------------------------------------------------

    {
        "name": "search_web",
        "description": (
            "Search the web for current information."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING"
                }
            },
            "required": [
                "query"
            ],
        },
    },

    {
        "name": "get_weather",
        "description": (
            "Get current weather for a city."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {
                    "type": "STRING"
                }
            },
            "required": [
                "city"
            ],
        },
    },

    {
        "name": "get_news",
        "description": (
            "Get current news for a topic."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING"
                }
            },
            "required": [
                "query"
            ],
        },
    },

    {
        "name": "calculate",
        "description": (
            "Safely evaluate a basic arithmetic expression."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "expression": {
                    "type": "STRING"
                }
            },
            "required": [
                "expression"
            ],
        },
    },

    # -----------------------------------------------------------------------
    # HOME / SMARTTHINGS / LG
    # -----------------------------------------------------------------------

    {
        "name": "home_list_devices",
        "description": (
            "List all connected Samsung SmartThings and LG ThinQ "
            "home appliances available to Saba. "
            "Never ask the user for API keys, PATs, passwords, "
            "or credentials."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },

    {
        "name": "home_find_device",
        "description": (
            "Find a real connected home appliance by natural language. "
            "Use this whenever the user names an appliance by nickname, "
            "room, family member, model, or device type. "
            "Examples: 'Samsung AC', 'mother room AC', "
            "'room air conditioner', 'LG washer'. "
            "Never invent a device ID."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING"
                }
            },
            "required": [
                "query"
            ],
        },
    },

    {
        "name": "home_get_status",
        "description": (
            "Read the current state of a REAL connected home appliance. "
            "The device_id must be a real ID returned by "
            "home_find_device or home_list_devices."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "provider": {
                    "type": "STRING",
                    "enum": [
                        "lg_thinq",
                        "smartthings",
                    ],
                },
                "device_id": {
                    "type": "STRING"
                },
            },
            "required": [
                "provider",
                "device_id",
            ],
        },
    },

    {
        "name": "home_get_capabilities",
        "description": (
            "Read supported capabilities for a REAL connected appliance "
            "before attempting control."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "provider": {
                    "type": "STRING",
                    "enum": [
                        "lg_thinq",
                        "smartthings",
                    ],
                },
                "device_id": {
                    "type": "STRING"
                },
            },
            "required": [
                "provider",
                "device_id",
            ],
        },
    },

    {
        "name": "home_control_device",
        "description": (
            "Control a REAL connected appliance. "
            "NEVER invent, guess, or fabricate device_id values. "
            "For a natural-language request such as "
            "'turn on the Samsung AC', 'open mother's room AC', "
            "or 'set the room AC to turbo', first use home_find_device "
            "or use the known local device alias. "
            "For SmartThings, command must contain capability, "
            "command, optional args/arguments, and component. "
            "Never use placeholders such as "
            "'mother_room_ac_id_placeholder'. "
            "Never ask the user for credentials."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {

                "provider": {
                    "type": "STRING",
                    "enum": [
                        "lg_thinq",
                        "smartthings",
                    ],
                },

                "device_id": {
                    "type": "STRING",
                    "description": (
                        "Real provider device ID. "
                        "Never invent this."
                    ),
                },

                "command": {
                    "type": "OBJECT",
                    "properties": {

                        "device_query": {
                            "type": "STRING",
                            "description": (
                                "Optional natural-language device "
                                "description such as 'Samsung AC', "
                                "'mother room AC', or 'room air conditioner'. "
                                "Use this when device_id is not known."
                            ),
                        },

                        "capability": {
                            "type": "STRING"
                        },

                        "command": {
                            "type": "STRING"
                        },

                        "args": {
                            "type": "ARRAY",
                            "items": {},
                        },

                        "arguments": {
                            "type": "ARRAY",
                            "items": {},
                        },

                        "component": {
                            "type": "STRING"
                        },

                        "device_name": {
                            "type": "STRING"
                        },

                        "room": {
                            "type": "STRING"
                        },

                        "query": {
                            "type": "STRING"
                        },
                    },
                },
            },

            "required": [
                "provider",
                "device_id",
                "command",
            ],
        },
    },

    {
        "name": "home_get_energy",
        "description": (
            "Read energy, power, consumption, and related telemetry "
            "currently exposed by a connected appliance."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "provider": {
                    "type": "STRING",
                    "enum": [
                        "lg_thinq",
                        "smartthings",
                    ],
                },
                "device_id": {
                    "type": "STRING"
                },
            },
            "required": [
                "provider",
                "device_id",
            ],
        },
    },

    {
        "name": "home_get_energy_usage",
        "description": (
            "Read historical LG ThinQ energy usage."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "provider": {
                    "type": "STRING",
                    "enum": [
                        "lg_thinq",
                        "smartthings",
                    ],
                },
                "device_id": {
                    "type": "STRING"
                },
                "energy_property": {
                    "type": "STRING"
                },
                "period": {
                    "type": "STRING",
                    "enum": [
                        "DAY",
                        "WEEK",
                        "MONTH",
                    ],
                },
                "start_date": {
                    "type": "STRING"
                },
                "end_date": {
                    "type": "STRING"
                },
            },
            "required": [
                "provider",
                "device_id",
                "energy_property",
            ],
        },
    },

    {
        "name": "home_estimate_cost",
        "description": (
            "Estimate electricity cost from kWh and a tariff "
            "per kWh."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "kwh": {
                    "type": "NUMBER"
                },
                "tariff_per_kwh": {
                    "type": "NUMBER"
                },
            },
            "required": [
                "kwh",
                "tariff_per_kwh",
            ],
        },
    },

    # -----------------------------------------------------------------------
    # Developer tools
    # -----------------------------------------------------------------------

    {
        "name": "activate_developer_mode",
        "description": (
            "Creator-only: activate developer mode."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },

    {
        "name": "developer_diagnostics",
        "description": (
            "Creator-only developer diagnostics."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },

    {
        "name": "open_project",
        "description": (
            "Creator-only: open the Saba project folder in Finder."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },

    {
        "name": "list_project",
        "description": (
            "Creator-only: list a bounded set of project files."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },

    {
        "name": "git_status",
        "description": (
            "Creator-only read-only Git status for the current project."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },
]