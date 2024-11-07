from llm_tui.llm_api.llm_api import GigaChatConnector
from llm_tui.tui.tui import TUIApp
from llm_tui.constants import Constants


constants = Constants

gigachat = GigaChatConnector(
    auth_token=constants.GIGACHAT_AUTH_TOKEN,
    api_scope=constants.GIGACHAT_API_SCOPE,
    chats_json_path=constants.GIGACHAT_CHATS_JSON,
    max_tokens=Constants.GIGACHAT_MAX_TOKENS,
)

gigachat.authorize()

app = TUIApp(Constants, gigachat)
app.run()
