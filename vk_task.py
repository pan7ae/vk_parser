import requests
import structlog
from typing import Any, Optional
import csv
import json
from datetime import datetime
import yaml


logger = structlog.getLogger()

URL = "https://api.vk.com/method/friends.get"


class HttpClient:
    def request(self, method: str, url: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        response = requests.request(
            method=method,
            url=url,
            params=params
        )
        return self.check_response(response)

    def check_response(self, response: requests.Response) -> Optional[list[dict[str, Any]]]:
        if response.status_code == 200:
            return response.json()
        else:
            error_msg = f"Your request returned {response.status_code} status code."
            if response.status_code == 404:
                error_msg += " The requested resource wasn't found."
            elif response.status_code == 500:
                error_msg += " The server encountered an internal error."
            raise Exception(error_msg)


class Paginator:
    def __init__(self, user_id: int, access_token: str, count: int = 1000) -> None:
        self.access_token = access_token
        self.user_id = user_id
        self.count = count
        self.http_request = HttpClient()

    def get_all_friends(self, count: int = 1000) -> list[dict[str, Any]]:
        offset = 0
        friends_list = []
        while True:
            friends = self.get_friends(offset)
            friends_list.extend(friends)
            if len(friends) < count:
                break
            offset += count
        return friends_list

    def get_friends(self, offset: int) -> list[dict[str, Any]]:
        params = {
            "access_token": self.access_token,
            "user_id": self.user_id,
            "offset": offset,
            "count": self.count,
            "fields": "country, city ,bdate, sex",
            "v": 5.131
        }
        try:
            friends_request = self.http_request.request("get", URL, params)
            return friends_request["response"]["items"]
        except Exception as e:
            raise Exception(f"Error occurred while requesting friends list: {e}")


class FriendsParser:
    FIELDS = ["first_name", "last_name", "country", "city", "bdate", "sex"]

    def __init__(
        self,
        user_id: int,
        access_token: str,
        output_format: str = "csv",
        output_name: str = "report"
    ) -> None:
        self.user_id = user_id
        self.access_token = access_token
        self.output_format = output_format
        self.output_name = output_name
        self.paginator = Paginator(self.user_id, self.access_token)

    def parse(self) -> list[dict[str, Any]]:
        friends = self.paginator.get_all_friends()
        return friends

    def extract_data(self, friend: dict[str, Any]) -> dict[str, Any]:
        person = {}
        for field in self.FIELDS:
            if field in ["country", "city"]:
                value = self.get_value_from_data(friend, field)
                person[field] = value
            elif field == "bdate":
                value = self.get_date_value(friend, "bdate")
                person[field] = value
            else:
                person[field] = friend.get(field)
        return person

    def get_value_from_data(self, friend: dict[str, Any], key: str) -> Optional[str]:
        element = friend.get(key)
        if element:
            return element.get("title")
        return element

    def get_date_value(self, friend: dict[str, Any], value: str) -> Optional[str]:
        date = friend.get(value)
        if date is None:
            return None
        try:
            date_obj = datetime.strptime(date, "%d.%m.%Y")
            return date_obj.date().isoformat()
        except ValueError:
            pass

    def create_report(self, friends_list: list[dict[str, Any]]) -> None:
        report_list = []
        for friend in sorted(friends_list, key=lambda d: d["first_name"]):
            current_friend = self.extract_data(friend)
            report_list.append(current_friend)
            logger.info(
                "Extracting data from user",
                first_name=current_friend["first_name"],
                last_name=current_friend["last_name"]
            )

        output_formats = {
            "csv": self.write_csv_tsv_file,
            "json": self.write_json_file,
            "tsv": self.write_csv_tsv_file,
            "yaml": self.write_yaml_file
        }

        write_method = output_formats.get(self.output_format)
        if write_method:
            write_method(report_list)
        else:
            raise ValueError(f"Invalid output file format: {self.output_format}. Allowed formats: csv, json, tsv, yaml")

    def write_csv_tsv_file(self, friends_list: list[dict[str, Any]]) -> None:
        delimiter = "," if self.output_format == "csv" else "\t"
        try:
            with open(f"{self.output_name}.{self.output_format}", "w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=friends_list[0].keys(), delimiter=delimiter)
                writer.writeheader()
                for row in friends_list:
                    writer.writerow(row)
        except (TypeError, ValueError, IOError, IndexError):
            logger.info(
                f"Error while creating {self.output_name}.{self.output_format} file"
            )

    def write_json_file(self, friends_list: list[dict[str, Any]]) -> None:
        try:
            with open(f"{self.output_name}.{self.output_format}", "w") as file:
                json.dump(friends_list, file)
        except (TypeError, IOError):
            logger.info(
                f"Error while creating {self.output_name}.{self.output_format} file"
            )

    def write_yaml_file(self, friends_list: list[dict[str, Any]]) -> None:
        try:
            with open(f"{self.output_name}.{self.output_format}", "w") as file:
                yaml.dump(friends_list, file, default_flow_style=False)
        except (TypeError, IOError):
            logger.info(
                f"Error while creating {self.output_name}.{self.output_format} file"
            )
