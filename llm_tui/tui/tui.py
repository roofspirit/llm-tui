import sys
from functools import partial
from types import SimpleNamespace
from typing import Callable, Literal, TypedDict

from rich import print
from rich.align import Align
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from llm_tui.llm_api.llm_api import (
    GigaChatConnector,
    GigaChatMessageRoles,
)


class Route(TypedDict):
    caption: str
    handler: Callable


class TitledPanel(Panel):
    """Class for generating pre-defined Panels with title"""

    def __init__(
        self,
        renderable: str | Markdown,
        title: str = "",
        title_align: Literal["left", "center", "right"] = "left",
        title_color: str = "green",
        border_color: str = "white",
        **kwargs,
    ) -> None:
        title = f"[bold {title_color}]{title}[/]"
        super().__init__(
            renderable,
            title=title,
            title_align=title_align,
            border_style=border_color,
            **kwargs,
        )


class MenuRoutes:
    """Class for storing and process Menu Routes"""

    routes: dict[int, Route]

    def __init__(
        self, routes: dict[int, Route] | list[tuple[int, str, Callable]] = {}
    ) -> None:
        if isinstance(routes, list):
            routes = {
                idx: {"caption": caption, "handler": handler}
                for idx, caption, handler in routes
            }

        self.routes = routes

    @property
    def menu_text(self) -> str:
        """Returns text for Panel, that will be rendered"""
        return "\n".join(
            f"{f'[bold magenta][{idx}][/bold magenta]': <4} {route['caption']}"
            for idx, route in self.routes.items()
        )

    @property
    def choices(self) -> list[str]:
        """Returns list of menu item IDs"""
        return list(map(str, self.routes.keys()))

    def add_route(self, route: Route, route_id):
        self.routes.update({route_id: route})

    def get_route_handler(self, route_id: int) -> Callable:
        return self.routes[route_id]["handler"]


class MessagePanel(TitledPanel):
    role: GigaChatMessageRoles

    def __init__(self, role: GigaChatMessageRoles, text: str, **kwargs) -> None:
        self.role = role

        title = ""
        title_align = "left"
        title_color = "white"
        border_color = "white"
        renderable = text

        match role:
            case "system":
                title = "System prompt"
                title_align = "center"
                title_color = "dim"
                border_color = "magenta dim"
                renderable = f"[dim]{text}[/]"
            case "user":
                title = "User"
                title_color = "blue"
                border_color = "blue"
                renderable = Markdown(text, justify="left")
            case "assistant":
                title = "Assistant"
                title_color = "green"
                border_color = "green"
                renderable = Markdown(text, justify="left")

        super().__init__(
            renderable,
            title=title,
            title_align=title_align,
            title_color=title_color,
            border_color=border_color,
            # width=80,
            expand=False,
            **kwargs,
        )


class MessagePanelsGroup(Group):
    def __init__(self, message_panels: list | tuple) -> None:
        group = []
        for message in message_panels:
            match message.role:
                case "system":
                    message = Align.center(message)
                case "user":
                    message = Align.right(message)
                case "assistant":
                    message = Align.left(message)
            group.append(message)
        super().__init__(*group, fit=True)


class TUIApp:
    """TUI engine"""

    def __init__(self, constants: SimpleNamespace, llm: GigaChatConnector) -> None:
        self.constants: dict = vars(constants)
        self.console: Console = Console()
        self.current_handler: Callable = self.startpage
        self.llm: GigaChatConnector = llm

    def chat(self, chat_id: str):
        self.console.clear()
        self.llm.select_chat(chat_id)
        panel = TitledPanel("", title=f"Chat: {chat_id}")
        while True:
            self.console.clear()
            messages = self.llm.get_messages()
            message_groups = tuple(
                MessagePanel(message["role"], message["content"])
                for message in messages
            )
            panel.renderable = MessagePanelsGroup(message_groups)
            print(panel)
            user_input = Prompt.ask("Type here, `!q` to exit").strip()
            if user_input.lower() == "!q":
                break
            self.llm.ask(user_input)

        return self.startpage

    def new_chat(self):
        self.console.clear()
        chat_ids = self.llm.chat_ids
        panel = TitledPanel("", title="New chat")
        if not chat_ids:
            panel.renderable = "No chats found"
        else:
            text = "[bold]Existing chats:[/]"
            for name in chat_ids:
                text += "\n  - " + name
            panel.renderable = text

        print(panel)
        new_chat_name = ""
        while True:
            new_chat_name = Prompt.ask(
                "Enter new chat name or enter `0` to exit", default="0"
            )
            if new_chat_name == "0":
                return self.startpage
            elif new_chat_name in chat_ids:
                print("[red]This chat_id already exists[/]")
            else:
                break

        self.llm.add_chat(new_chat_name)
        system_prompt = Prompt.ask("Enter system prompt, press `ENTER` to skip").strip()
        if system_prompt:
            self.llm.select_chat(new_chat_name)
            self.llm.add_system_prompt(system_prompt)
        return lambda: self.chat(new_chat_name)

    def select_chat(self):
        self.console.clear()
        chat_ids = self.llm.chat_ids
        panel = TitledPanel("", title="Select chat")
        if not chat_ids:
            panel.renderable = "No chats available"
            print(panel)
            Prompt.ask("Press any key to return to Start Page")
            return self.startpage

        routes_list = [(0, "[bold red]Exit to Start Page[/]", self.startpage)]
        routes_list.extend(
            [
                (idx + 1, chat_id, partial(self.chat, chat_id))
                for idx, chat_id in enumerate(self.llm.chat_ids)
            ]
        )
        routes = MenuRoutes(routes_list)
        panel.renderable = routes.menu_text
        print(panel)
        route_id = int(
            Prompt.ask(
                "Choose option", choices=routes.choices, default=routes.choices[0]
            )
        )
        return routes.get_route_handler(route_id)

    def settings(self):
        self.console.clear()
        name_max_length = max(map(len, self.constants.keys()))
        text = "\n".join(
            f"{k: <{name_max_length}} = {v}" for k, v in self.constants.items()
        )
        print(TitledPanel(text, title="Settings"))
        Prompt.ask("Press any key to return to Start Page")
        return self.startpage

    def balance(self) -> Callable:
        self.console.clear()
        text = f"Balance: {self.llm.balance}"
        print(TitledPanel(text, title="Balance"))
        Prompt.ask("Press any key to return to Start Page")
        return self.startpage

    def startpage(self) -> Callable:
        routes = MenuRoutes(
            [
                (0, "[red]Exit[/]", self.exit),
                (1, "New chat", self.new_chat),
                (2, "Select chat", self.select_chat),
                (3, "Show settings", self.settings),
                (4, "Check balance", self.balance),
            ]
        )

        self.console.clear()
        print(TitledPanel(routes.menu_text, title="Start Page"))
        route_id = int(
            Prompt.ask(
                "Choose option", choices=routes.choices, default=routes.choices[0]
            )
        )
        return routes.get_route_handler(route_id)

    def exit(self):
        return sys.exit

    def run(self):
        while True:
            try:
                result = self.current_handler()
                if isinstance(result, Callable):
                    self.current_handler = result
                else:
                    break
            except KeyboardInterrupt:
                sys.exit()
            except Exception as ex:
                print(ex)
                match input(
                    "\n\nPress `ENTER` to try again. Type `!q` to exit"
                ).strip():
                    case "!q":
                        self.exit()
                    case _:
                        continue
