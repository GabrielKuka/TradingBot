import re


class ValidateString(object):
    """Provides a number of functions to validate strings"""

    @staticmethod
    def is_asset_valid(asset):
        return bool(re.match("^[A-Z\s]{1,4}$", asset))

    @staticmethod
    def are_days_valid(days):
        return True if days.isdigit() and 100 <= int(days) <= 1000 else False
