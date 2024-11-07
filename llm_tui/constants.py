import os
from enum import Enum
from types import SimpleNamespace

current_dir = os.getcwd()

# Load environment variables from .env file if present
ENV_FILE_PATH = os.environ.get("ENV_FILE_PATH", os.path.join(current_dir, ".env"))
# Загрузка переменных окружения из файла, если он существует
if os.path.exists(ENV_FILE_PATH):
    with open(ENV_FILE_PATH, "r", encoding="utf-8") as envfile:
        lines = envfile.readlines()
        for line in lines:
            if not line.strip().startswith("#"):
                key_value_pair = line.split("=", maxsplit=1)
                if len(key_value_pair) == 2:
                    key, value = key_value_pair
                    os.environ[key.strip()] = value.strip()


class GigaChatApiShortScope(Enum):
    PERS = "PERS"
    B2B = "B2B"
    CORP = "CORP"


# Определяем объект Constants с необходимыми значениями
Constants = SimpleNamespace(
    ENV_FILE_PATH=ENV_FILE_PATH,
    GIGACHAT_AUTH_TOKEN=os.environ.get("GIGACHAT_AUTH_TOKEN", None),
    GIGACHAT_API_SCOPE="GIGACHAT_API_" + GigaChatApiShortScope.PERS.value,
    GIGACHAT_CHATS_JSON=os.environ.get(
        "GIGACHAT_CHATS_JSON",  os.path.join(current_dir, "gigachat_chats.json")
    ),
    GIGACHAT_MAX_TOKENS=int(os.environ.get("GIGACHAT_MAX_TOKENS", 100)),
)

# Проверка и установка GIGACHAT_API_SCOPE в зависимости от значения GIGACHAT_API_TYPE
gigachat_api_type = os.environ.get("GIGACHAT_API_SCOPE", None)
if gigachat_api_type and gigachat_api_type in GigaChatApiShortScope.__members__:
    Constants.GIGACHAT_API_SCOPE = "GIGACHAT_API_" + gigachat_api_type

# Проверка файла с чатами
if not os.path.isfile(Constants.GIGACHAT_CHATS_JSON):

    # Create directories if they do not exist
    directory_name = os.path.dirname(Constants.GIGACHAT_CHATS_JSON)
    if directory_name:
        os.makedirs(directory_name, exist_ok=True)

    # Create an empty JSON file
    with open(Constants.GIGACHAT_CHATS_JSON, 'w', encoding='utf-8') as file:
        file.write("")

if __name__ == "__main__":
    constants = Constants
    for k, v in vars(constants).items():
        print(k, v)
