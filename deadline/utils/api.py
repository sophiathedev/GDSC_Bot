#coding: utf-8

import json
from typing import Any, Dict, List

from datetime import datetime, date, timedelta

import gspread


class SheetAPI:
    def __init__( self, url: str ) -> None:
        self.url: str = url

        # authorize the spreadsheet
        self.spread_client: gspread.Client = gspread.service_account(filename="./credentials.json")
        self.working_sheet: gspread.Spreadsheet = self.spread_client.open_by_url( self.url )

        # deadline sheet will must in first sheet in spreadsheet
        self.deadline_sheet: gspread.Worksheet = self.working_sheet.get_worksheet(0)

    def serialize( self ) -> List[Dict[str, Any]]:
        records:  List[Dict[str, Any]] = self.deadline_sheet.get_all_records()
        return records

class DeadlineSerializer:

    def __init__( self, src: Dict[str, Any] ) -> None:
        # assert the required field
        assert "task_name" in src
        assert "assigned_to" in src
        assert "start" in src
        assert "deadline" in src
        assert "deadline_id" in src
        assert "status" in src

        self.data: Dict[Any, Any] = src

        # convert status to int for easier handling deadline
        extract_status_value: Dict[str, int] = { "Doing": 0, "Done": 1 }
        self.data["extract_status"] = extract_status_value[ self.data["status"] ]

        # info for deadline diff date
        self.data["warning_late"] = False
        self.data["warning_today"] = False
        # check deadline is fkin out
        current_date: date = date.today()
        if current_date > self.data["deadline"]:
            self.data["warning_late"] = True
        elif current_date == self.data["deadline"]:
            self.data["warning_today"] = True

    def get_late_deadline( self ) -> timedelta:
        return self.data["late_dl_diff"]

    def __getattr__( self, ref: str ) -> Any:
        return self.data[ref]

    def __str__( self ) -> str:
        return f"[{self.data['task_name']}]({self.data['url']}) - {str(self.data['deadline'])}"
