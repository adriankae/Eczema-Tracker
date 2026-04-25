from __future__ import annotations

import logging
from dataclasses import dataclass

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from czm_cli.client import CzmClient
from czm_cli.config import AppConfig
from czm_cli.errors import CzmError, EXIT_AUTH
from czm_cli.telegram.commands import TelegramCommandContext, handle_text_command
from czm_cli.telegram.config import validate_telegram_config
from czm_cli.telegram.formatting import backend_error_message
from czm_cli.telegram.handlers import TelegramHandlerContext, handle_callback, handle_guided_text, handle_location_image_set_text, handle_photo
from czm_cli.telegram.keyboards import main_menu_keyboard
from czm_cli.telegram.security import ensure_allowed, identity_from_update
from czm_cli.telegram.setup import validate_bot_token
from czm_cli.telegram.state import ConversationStore


TELEGRAM_COMMANDS = [
    "start",
    "menu",
    "help",
    "status",
    "subjects",
    "subject_create",
    "locations",
    "location_create",
    "location_image_set",
    "episodes",
    "episode",
    "episode_create",
    "due",
    "log",
    "events",
    "timeline",
    "adherence",
    "adherence_calendar",
    "adherence_missed",
    "adherence_rebuild",
]


@dataclass(slots=True)
class TelegramRuntime:
    config: AppConfig
    client: CzmClient
    state: ConversationStore | None = None


def build_application(runtime: TelegramRuntime) -> Application:
    if runtime.state is None:
        runtime.state = ConversationStore()
    application = Application.builder().token(runtime.config.telegram.bot_token or "").build()
    handler_ctx = TelegramHandlerContext(TelegramCommandContext(runtime.config, runtime.client), runtime.state)
    for command in TELEGRAM_COMMANDS:
        application.add_handler(CommandHandler(command, _handler(runtime, handler_ctx)))
    application.add_handler(CallbackQueryHandler(lambda update, context: handle_callback(update, context, handler_ctx)))
    application.add_handler(MessageHandler(filters.PHOTO, lambda update, context: handle_photo(update, context, handler_ctx)))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: handle_guided_text(update, context, handler_ctx)))
    return application


def run_polling(config: AppConfig) -> None:
    validate_telegram_config(config)
    validate_bot_token(config.telegram.bot_token or "")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.info("Starting Zema Telegram bot for %s", config.base_url)
    client = CzmClient(config.base_url, config.api_key or "")
    try:
        application = build_application(TelegramRuntime(config=config, client=client))
        application.run_polling()
    finally:
        client.close()


def _handler(runtime: TelegramRuntime, handler_ctx: TelegramHandlerContext):
    async def handle(update, context) -> None:
        message = getattr(update, "effective_message", None)
        if message is None:
            return
        try:
            ensure_allowed(runtime.config.telegram, identity_from_update(update))
            text = getattr(message, "text", "") or ""
            if text.split(maxsplit=1)[0].split("@", 1)[0] in {"/start", "/menu"}:
                menu_reply = await handle_text_command(TelegramCommandContext(runtime.config, runtime.client), text)
                await message.reply_text(menu_reply, reply_markup=main_menu_keyboard())
                return
            if text.split(maxsplit=1)[0].split("@", 1)[0] == "/location_image_set":
                await message.reply_text(await handle_location_image_set_text(update, context, handler_ctx))
                return
            reply = await handle_text_command(TelegramCommandContext(runtime.config, runtime.client), text)
        except CzmError as exc:
            reply = exc.message if exc.exit_code in {EXIT_AUTH} else backend_error_message(exc.message)
        except Exception:
            logging.exception("Telegram command failed")
            reply = "Zema request failed."
        await message.reply_text(reply)

    return handle
