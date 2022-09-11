from utils.googleSheetsManager import GoogleSheetsManager
from config import spreadsheetId


def get_conversation_settings() -> dict:
    _google_sheet: GoogleSheetsManager = GoogleSheetsManager(spreadsheetId)
    raw_settings: list = _google_sheet.get_sheet_values("Очистка обсуждений")

    conversations_settings = {}

    for row in raw_settings:
        conv_id = _get_int_from_str(row.get('conversation_id'))
        if conv_id == 0:
            continue

        if conv_id not in conversations_settings:
            conversations_settings[conv_id] = default_conv_settings()

        days_for_cleaning = _get_int_from_str(row.get('days_for_cleaning'))

        user_id = _get_int_from_str(row.get('user_id'))
        if user_id != 0:
            conversations_settings[conv_id]['users_settings'][user_id] = days_for_cleaning

        comment_id = _get_int_from_str(row.get('comment_id'))
        if comment_id != 0:
            conversations_settings[conv_id]['comments_settings'][comment_id] = days_for_cleaning

    return conversations_settings


def default_conv_settings() -> dict:
    users_settings = {}
    comments_settings = {}
    conv_settings = {'users_settings': users_settings, 'comments_settings': comments_settings}
    return conv_settings


def _get_int_from_str(str_value: str) -> int:
    if not isinstance(str_value, str) or str_value == '' or not str_value.isdigit():
        int_value = 0
    else:
        try:
            int_value = int(str_value)
        except ValueError:
            int_value = 0

    return int_value
