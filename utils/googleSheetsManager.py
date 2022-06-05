import re
from datetime import datetime
from pprint import pprint

import apiclient.discovery
import httplib2
from oauth2client.service_account import ServiceAccountCredentials
import utils.config as config


class GoogleSheetsManager:
    secret_key = config.secret_key_google
    templates = eval(secret_key)
    credentials = ServiceAccountCredentials._from_parsed_json_keyfile(
        templates,
        [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
    )
    httpAuth = credentials.authorize(httplib2.Http())
    service = apiclient.discovery.build('sheets', 'v4', http=httpAuth)

    def __init__(self, spreadsheetId):
        self.spreadsheetId = spreadsheetId

    def get_sheet_values(self, list_name):
        ranges = [f"{list_name}!A1:Z1000"]  #

        results = self.service.spreadsheets().values().batchGet(
            spreadsheetId=self.spreadsheetId,
            ranges=ranges,
            valueRenderOption='FORMATTED_VALUE',
            dateTimeRenderOption='FORMATTED_STRING'
        ).execute()
        sheet_values = results['valueRanges'][0]['values']

        header = sheet_values[0]
        result_list = [dict(zip(header, elem)) for elem in sheet_values[1:]]

        # pprint(result_list)
        return result_list

    def set_data_to_sheet(self, list_name, data):
        arr = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "N", "O", "P"]
        values = []
        len_rows = 0
        len_column = 0
        if data:
            len_rows = len(data)
            len_column = len(data[0])
            title = [elem for elem in data[0]]
            values.append(title)

            for rows in data:
                title_rows = [elem for elem in rows]
                [title.append(elem) for elem in title_rows if elem not in title]
                values.append([rows.get(elem) for elem in title])
        results = self.service.spreadsheets().values().batchUpdate(spreadsheetId=self.spreadsheetId, body={
            "valueInputOption": "USER_ENTERED",
            # Данные воспринимаются, как вводимые пользователем (считается значение формул)
            "data": [
                {"range": f"{list_name}!A1:{arr[len_column]}{len_rows + 1}",
                 "majorDimension": "ROWS",  # Сначала заполнять строки, затем столбцы
                 "values": values}
            ]
        }).execute()
        return results

    @staticmethod
    def take_data_from_raw_dict(data_dict):
        for elem in data_dict:
            if re.search(r"(0?[1-9]|[12][0-9]|3[01])[\/\-\.](0?[1-9]|1[012])[\/\-\.](0?20[0-9][0-9]|[0-9][0-9])",
                         data_dict[elem]):
                if len(re.search(
                        r"(0?[1-9]|[12][0-9]|3[01])[\/\-\.](0?[1-9]|1[012])[\/\-\.](0?20[0-9][0-9]|[0-9][0-9])",
                        data_dict[elem]).group(3)) == 4:
                    data_dict[elem] = datetime.date(datetime.strptime(data_dict[elem], '%d.%m.%Y'))
                else:
                    data_dict[elem] = datetime.date(datetime.strptime(data_dict[elem], '%d.%m.%y'))
            elif re.search(r"(true)|(false)", data_dict[elem], re.IGNORECASE):
                data_dict[elem] = eval(data_dict[elem].capitalize())
            elif data_dict[elem].strip() in ["", "-"]:
                data_dict[elem] = None
        return data_dict


if __name__ == "__main__":
    spreadsheetId = config.spreadsheetId
    sheet = GoogleSheetsManager(spreadsheetId)
    for elem in sheet.get_sheet_values("ads_test"):
        pprint(sheet.take_data_from_raw_dict(elem))
    # sheet.get_sheet_values("Стандартные ответы")
