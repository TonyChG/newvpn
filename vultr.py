# coding: utf8

import os
import json
import time
import logging
from typing import Optional, Any, Union
from argparse import ArgumentParser

import requests

BASE_URL = "https://api.vultr.com/v2"


class Vultr:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("VULTR_API_KEY")

    def _get_headers(self, headers: Optional[dict[str, str]] = None):
        _headers = {"Authorization": f"Bearer {self.api_key}"}
        if headers is not None:
            _headers.update(headers)
        return _headers

    def _response_handler(
        self,
        response: requests.Response,
        expected_status_code: tuple[int] = (200,),
    ):
        if response.status_code not in expected_status_code:
            raise ConnectionError(response.content)
        else:
            return response.json()

    def delete(
        self,
        endpoint: str,
        headers: Optional[dict[str, str]] = None,
        params: Optional[dict[str, str]] = None,
    ) -> requests.Response:
        return requests.delete(
            BASE_URL + endpoint,
            params=params,
            headers=self._get_headers(headers),
        )

    def get(
        self,
        endpoint: str,
        headers: Optional[dict[str, str]] = None,
        params: Optional[dict[str, str]] = None,
    ) -> requests.Response:
        return requests.get(
            BASE_URL + endpoint,
            params=params,
            headers=self._get_headers(headers),
        )

    def post(
        self,
        endpoint: str,
        data: dict[Any, Any],
        headers: Optional[dict[str, str]] = None,
        params: Optional[dict[str, str]] = None,
    ):
        return requests.post(
            BASE_URL + endpoint,
            params=params,
            headers=self._get_headers(headers),
            json=data,
        )

    def auth(self):
        try:
            self._response_handler(self.get("/account"))
        except requests.RequestException as error:
            logging.error(error)

    def list_plans(self, plan_type: str = "all") -> dict[Any, Any]:
        return self._response_handler(
            self.get(
                "/plans",
                params={"type": plan_type},
            )
        )

    def list_regions(self) -> dict[Any, Any]:
        return self._response_handler(self.get("/regions"))

    def list_os(self) -> dict[Any, Any]:
        return self._response_handler(self.get("/os"))

    def list_ssh_keys(self):
        return self._response_handler(self.get("/ssh-keys"))

    def region_id_from_city(self, city: str) -> Union[int, None]:
        regions = self.list_regions()

        for region in regions["regions"]:
            if region["city"] == city:
                return region["id"]

    def os_id_from_name(self, name: str) -> Union[int, None]:
        os_list = self.list_os()

        for os in os_list["os"]:
            if os["name"] == name:
                return os["id"]

    def ssh_key_id_from_name(self, name: str) -> Union[str, None]:
        ssh_keys = self.list_ssh_keys()

        for ssh_key in ssh_keys["ssh_keys"]:
            if ssh_key["name"] == name:
                return ssh_key["id"]

    def create_instance(
        self,
        label: str,
        ssh_key: str,
        city: str = "Paris",
        plan_id: str = "vc2-1c-1gb",
        os: str = "Debian 11 x64 (bullseye)",
    ):
        return self._response_handler(
            self.post(
                "/instances",
                data={
                    "region": self.region_id_from_city(city),
                    "plan": plan_id,
                    "label": label,
                    "os_id": self.os_id_from_name(os),
                    "sshkey_id": [self.ssh_key_id_from_name(ssh_key)],
                },
            ),
            expected_status_code=(202,),
        )

    def get_instance(self, instance_id: str) -> dict[Any, Any]:
        return self._response_handler(self.get(f"/instances/{instance_id}"))

    def delete_instance(self, instance_id: str) -> requests.Response:
        return self.delete(f"/instances/{instance_id}")


def command_create(name: str, ssh: str, api: Optional[str] = None):
    vultr = Vultr(args.api)
    instance = vultr.create_instance(args.name, args.ssh)

    while (
        instance["instance"]["status"] != "active"
        or instance["instance"]["server_status"] != "installingbooting"
        or instance["instance"]["power_status"] != "running"
    ):
        instance = vultr.get_instance(instance["instance"]["id"])
        time.sleep(1)

    print(json.dumps(instance, indent=4))


if __name__ == "__main__":
    logging.basicConfig(format="%(message)s", level=logging.DEBUG)
    parser = ArgumentParser()
    parser.add_argument("name", type=str)
    parser.add_argument("--ssh", type=str)
    parser.add_argument("--api", type=str, default=None)
    args = parser.parse_args()
    command_create(args.name, args.ssh, args.api)
