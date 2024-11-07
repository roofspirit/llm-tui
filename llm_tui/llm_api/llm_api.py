import base64
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal, TypeAlias, TypedDict
from uuid import uuid4

import requests
import urllib3

import llm_tui.utils as utils

urllib3.disable_warnings()


class BadRequest(Exception):
    def __init__(
        self,
        status_code: int | None = None,
        message: str = "",
    ):
        self.message = message
        self.status_code = status_code

    def __str__(self):
        return f"BadRequest: [ {self.status_code} ] {self.message}"


class AuthorizationError(Exception):
    def __init__(self, message: str, code: int | None = None):
        self.message = message
        self.code = code

    def __str__(self):
        return f"Authorization error: {self.message}"


class LLMProviders(Enum):
    gigachat = "gigachat"


@dataclass
class AccessToken:
    token: str
    expires_at: datetime


GigaChatMessageRoles: TypeAlias = Literal["system", "user", "assistant"]


class GigaChatMessage(TypedDict):
    role: GigaChatMessageRoles
    content: str


class GigaChatConnector:
    auth_token: str
    api_scope: str
    _access_token: AccessToken

    chats: dict[str, list[GigaChatMessage]]
    chats_json_path: str
    current_chat_id: str

    OAUTH_URL: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    LLM_URL: str = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    BALANCE_URL: str = "https://gigachat.devices.sberbank.ru/api/v1/balance"
    LLM_MODEL: str = "GigaChat"

    @staticmethod
    def is_auth_token(string: str) -> bool:
        secrets_regex = r"[a-z0-9]{8}(-[a-z0-9]{4}){3}-[a-z0-9]{8}"

        if not utils.is_base64(string):
            return False
        decoded = base64.b64decode(string).decode()
        if ":" not in decoded:
            return False
        client_id, client_secret = decoded.split(":")
        if any(
            (
                re.match(secrets_regex, client_id) is None,
                re.match(secrets_regex, client_secret) is None,
            )
        ):
            return False
        return True

    @staticmethod
    def get_access_token(auth_token: str, api_type: str) -> AccessToken:
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid4()),
            "Authorization": f"Basic {auth_token}",
        }
        body = {"scope": "GIGACHAT_API_PERS"}
        response = requests.post(
            url=GigaChatConnector.OAUTH_URL,
            headers=headers,
            data=body,
            verify=False,
        )

        match response.status_code:
            case 400:
                raise BadRequest(response.status_code)
            case 401:
                data = response.json()
                code, message = data["code"], data["message"]
                raise AuthorizationError(message, code)
            case 200:
                data = response.json()
                return AccessToken(
                    data["access_token"],
                    utils.get_datetime_from_timestamp(data["expires_at"]),
                )
            case _:
                raise BadRequest(response.status_code)

    @staticmethod
    def _is_active_access_token(access_token: AccessToken):
        return datetime.now() > access_token.expires_at

    @staticmethod
    def _read_chats_json(filepath: str) -> dict[str, list[GigaChatMessage]]:
        chats = {}
        with open(filepath, "r", encoding="utf-8") as jsf:
            file_content = jsf.read()
            if file_content.strip():
                chats = json.loads(file_content)
        return chats

    @staticmethod
    def _write_chats_json(
        filepath: str, chats: dict[str, list[GigaChatMessage]]
    ) -> None:
        with open(filepath, "w", encoding="utf-8") as jsf:
            json.dump(chats, jsf, ensure_ascii=False, indent=4)

    @staticmethod
    def _get_messages(
        chats: dict[str, list[GigaChatMessage]], chat_id: str
    ) -> list[GigaChatMessage]:
        if chat_id not in chats:
            return []
        return chats[chat_id]

    @staticmethod
    def _get_answer(
        access_token: AccessToken,
        max_tokens: int = 100,
        chat: list[GigaChatMessage] = [],
    ) -> dict:
        headers = {
            "Authorization": f"Bearer {access_token.token}",
            "Content-Type": "application/json",
        }
        data = {
            "model": GigaChatConnector.LLM_MODEL,
            "messages": chat,
            "max_tokens": max_tokens,
        }
        answer = {}
        response = requests.post(
            GigaChatConnector.LLM_URL,
            headers=headers,
            data=json.dumps(data),
            verify=False,
        )
        match response.status_code:
            case 200:
                answer = response.json()
            case 401:
                data = response.json()
                code, message = data["code"], data["message"]
                raise AuthorizationError(message, code)
            case 400:
                raise BadRequest(response.status_code)
            case 404:
                raise ValueError(f"[ {response.status_code} ] No such model")
            case 422:
                message = response.json().get("message", "")
                raise ValueError(
                    f"[ {response.status_code} ] Validation error: {message}"
                )
            case 429:
                raise Exception(f"[ {response.status_code} ] Too many requests")
            case 500:
                raise Exception(f"[ {response.status_code} ] Internal server error")
            case _:
                raise BadRequest(response.status_code)
        return answer

    @staticmethod
    def _get_balance(access_token: AccessToken) -> dict:
        response = requests.get(
            GigaChatConnector.BALANCE_URL,
            headers={"Authorization": f"Bearer {access_token.token}"},
            verify=False,
        )
        match response.status_code:
            case 200:
                data = response.json()
                return data
            case 401:
                data = response.json()
                code, message = data["code"], data["message"]
                raise AuthorizationError(message, code)
            case 403:
                raise Exception(
                    f"[ {response.status_code} ] Permission denied. Check your tarification type"
                )
            case _:
                raise BadRequest(response.status_code)

    def __init__(
        self,
        auth_token: str,
        api_scope: str,
        chats_json_path: str = "",
        chats: dict[str, list[GigaChatMessage]] = {},
        max_tokens: int = 100,
    ) -> None:
        if not self.is_auth_token(auth_token):
            raise AuthorizationError("Provided auth_token is not valid")

        self.auth_token = auth_token
        self.api_scope = api_scope
        self.max_tokens = max_tokens

        self.chats_json_path = chats_json_path
        if chats:
            self.chats = chats
        elif chats_json_path:
            self.chats = self.read_chats_json()
        else:
            self.chats = {}

    def authorize(self) -> None:
        self._access_token = self.get_access_token(self.auth_token, self.api_scope)

    @property
    def access_token(self) -> AccessToken:
        if not self._is_active_access_token(self._access_token):
            self.authorize()
        return self._access_token

    @property
    def chat_ids(self) -> list[str]:
        return list(self.chats.keys())

    @property
    def balance(self) -> int | None:
        data = self._get_balance(self.access_token)
        for item in data["balance"]:
            if item["usage"] == GigaChatConnector.LLM_MODEL:
                return item["value"]
        return data["balance"][0]["value"]

    def read_chats_json(self) -> dict[str, list[GigaChatMessage]]:
        if not os.path.exists(self.chats_json_path):
            raise FileNotFoundError(f"File {self.chats_json_path} does not exist")
        return self._read_chats_json(self.chats_json_path)

    def write_chats_json(self) -> None:
        self._write_chats_json(self.chats_json_path, self.chats)

    def is_chat_exists(self, chat_id: str) -> bool:
        return chat_id in self.chats

    def add_chat(self, chat_id: str) -> None:
        if self.is_chat_exists(chat_id):
            raise ValueError(f"Chat {chat_id} already exists")
        else:
            self.chats[chat_id] = []

        self.write_chats_json()

    def select_chat(self, chat_id: str):
        if self.is_chat_exists(chat_id):
            self.current_chat_id = chat_id
        else:
            self.add_chat(chat_id)
            self.current_chat_id = chat_id

    def add_message(self, role: GigaChatMessageRoles, content: str) -> None:
        self.chats[self.current_chat_id].append({"role": role, "content": content})

        self.write_chats_json()

    def add_system_prompt(self, text: str) -> None:
        self.add_message(role="system", content=text)

    def get_messages(self) -> list[GigaChatMessage]:
        return self._get_messages(self.chats, self.current_chat_id)

    def get_answer(self) -> str:
        messages = self.get_messages()
        answer = self._get_answer(self.access_token, self.max_tokens, messages)
        message = answer["choices"][0]["message"]
        role, content = message["role"], message["content"]
        self.add_message(role, content)
        return content

    def ask(self, text: str) -> str:
        self.add_message(role="user", content=text)
        result = self.get_answer()
        return result


class LLMConnector:
    LLMProvider: LLMProviders

    def __init__(self, LLMProvider: LLMProviders) -> None:
        self.LLMProvider = LLMProvider


if __name__ == "__main__":

    def jprint(obj):
        print(json.dumps(obj, indent=4, ensure_ascii=False))

    from llm_tui.constants import Constants

    if Constants.GIGACHAT_AUTH_TOKEN is not None:
        giga = GigaChatConnector(
            api_scope=Constants.GIGACHAT_API_SCOPE,
            auth_token=Constants.GIGACHAT_AUTH_TOKEN,
            chats_json_path=Constants.GIGACHAT_CHATS_JSON,
            max_tokens=Constants.GIGACHAT_MAX_TOKENS,
        )
        giga.authorize()
        giga.select_chat("test")
        print(giga.ask("How old are you?"))
