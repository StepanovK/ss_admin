import os
from pprint import pprint

import apiclient.discovery
import httplib2
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()


class GoogleSheetsManager:
    secret_key = os.environ.get("secret")
    print(secret_key)
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

        pprint(result_list)
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
        print(results)
        return results


if __name__ == "__main__":
    spreadsheetId = os.environ.get("spreadsheetId")
    sheet = GoogleSheetsManager(spreadsheetId)
    sheet.get_sheet_values("Реклама")
    # sheet.get_sheet_values("Стандартные ответы")
