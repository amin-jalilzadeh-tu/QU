"""
data_lookup.py

Stores universal constants and default parameters for the project.
"""

DEFAULT_CONFIG = {
    "hv_voltage": 110000,  # 110 kV
    "mv_voltage": 20000,   # 20 kV
    "lv_voltage": 400,     # 0.4 kV

    "hv_slack_voltage_pu": 1.0,  # Slack bus reference
}

DEFAULT_LINE_PARAMS = {
    # Nominal values for line impedances, etc.
    "mv_r1": 1.0,   # example ohms or pu
    "mv_x1": 5.0,   # example ohms or pu
    "lv_r1": 0.5,   # example
    "lv_x1": 1.0,   # example
    "i_n": 300      # nominal current rating
}

DEFAULT_TRANSFORMER_PARAMS = {
    "r1": 0.5,
    "x1": 3.0,
    "i_n": 200,
    "rating_MVA": 1.0
}

# You can add more if needed, e.g. default building load range, etc.
