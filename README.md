# LLM TUI
---

Консольное приложение на Python для работы с LLM-моделями.
На данный момент поддерживает только GigaChat

# Стек

- Python 3.11.9
- requests
- rich
- poetry / pip

Использованы различные методы ООП.

Вместо REST API можно было бы использовать готовый SDK от GigaChat. Использовал REST API для демонстрации своих навыков работы с REST API.

Сделал более сложный интерфейс, нежели простое консольное приложение используя `rich`. Кроме того, это позволило разработать платформо-независимое приложение.

Использовал ruff и pyright для проверки типов, линтинга и форматирования.

Настройки подгружаются из переменных среды.

# Какие проблемы есть?

- Для добавления новых LLM-провайдеров, нужно переделать систему классов
- Могут наблюдаться проблемы с прокруткой в интерфейсе
- Отсутствуют тесты и логирование

# Запуск
0. Убедитесь, что вы используете Python 3.11.9.
Для удобного управления версиями Python можно использовать `pyenv`.
Для [Linux/MacOS](https://github.com/pyenv/pyenv).
Для [Windows](https://github.com/pyenv-win/pyenv-win)

1. Выполните клонирование репозитория с помощью `git clone`
2. Перейдите в корневую папку репозитория
3. Выполните инициализацию виртуального окружения, его инициализацию и установку пакетов
  - Poetry:
    - Создание venv и установка пакетов
      - `poetry install`
    - Активация venv
      - Linux
        - `source .venv/bin/activate`
      - Windows
        - `.venv\Scripts\activate`

  - Pip:
    - Cоздание venv
      - `python -m venv .venv`
    - Активация venv
      - Linux
        - `source .venv/bin/activate`
      - Windows
        - `.venv\Scripts\activate`
    - Установка пакетов
      - `pip install -r requirements.txt`

4. Введите настройки в файле `.env` (их также можно передать как переменные среды при запуске модуля)
 - `GIGACHAT_AUTH_TOKEN` - Ваш ключ авторизации. Подробности как получить ключ авторизации GigaChat [здесь](https://developers.sber.ru/docs/ru/gigachat/quickstart/ind-using-api)
 - `GIGACHAT_API_SCOPE` `[PERS/B2B/CORP]` - Версия API без префикса `GIGACHAT_API_`, по-умолчанию `PERS` для физических лиц. Подробнее [здесь](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/post-token)
 - `GIGACHAT_CHATS_JSON` - Путь до файла, в котором хранятся чаты и сообщения. По-
 - `GIGACHAT_MAX_TOKENS` - Максимальное количество токенов для генерации ответов. По-умолчанию `100`, для экономии токенов в бесплатной версии

5. Запустите модуль `main`
 - `python -m llm_tui.main`
 - С перемнными среды в MacOS/Linux: `GIGACHAT_API_SCOPE=PERS GIGACHAT_MAX_TOKENS=100 <...> python -m llm_tui.main`

