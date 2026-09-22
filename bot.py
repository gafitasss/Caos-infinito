import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

from database import Database
from game import Game


TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("Falta BOT_TOKEN")


# ==========================================
# SERVIDOR HTTP PARA RENDER
# ==========================================

PORT = int(os.environ.get("PORT", 10000))


class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain"
        )
        self.end_headers()

        self.wfile.write(
            b"CAOS INFINITO OK"
        )

    def log_message(self, format, *args):
        return


def start_web_server():

    server = HTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler
    )

    print(
        f"Servidor HTTP escuchando "
        f"en el puerto {PORT}"
    )

    server.serve_forever()


threading.Thread(
    target=start_web_server,
    daemon=True
).start()


# ==========================================
# JUEGO
# ==========================================

db = Database()
game = Game(db)


# ==========================================
# MENÚ
# ==========================================

def main_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "🎮 JUGAR",
                callback_data="play"
            ),
            InlineKeyboardButton(
                "📊 ESTADO",
                callback_data="status"
            )
        ],

        [
            InlineKeyboardButton(
                "🏆 RANKING",
                callback_data="ranking"
            ),
            InlineKeyboardButton(
                "🌍 MUNDO",
                callback_data="world"
            )
        ]

    ]

    return InlineKeyboardMarkup(keyboard)


def action_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "🧭 EXPLORAR",
                callback_data="action_explore"
            ),
            InlineKeyboardButton(
                "🛡️ PROTEGER",
                callback_data="action_protect"
            )
        ],

        [
            InlineKeyboardButton(
                "💥 SABOTEAR",
                callback_data="action_sabotage"
            ),
            InlineKeyboardButton(
                "🧬 MUTAR",
                callback_data="action_mutate"
            )
        ],

        [
            InlineKeyboardButton(
                "🌍 MUNDO",
                callback_data="world"
            )
        ]

    ]

    return InlineKeyboardMarkup(keyboard)


# ==========================================
# START
# ==========================================

async def start(update, context):

    user = update.effective_user

    game.register(user)

    await update.message.reply_text(

        "🌌 *CAOS INFINITO*\n\n"

        "Bienvenido al mundo donde "
        "cada jugador puede cambiar "
        "el destino del grupo.\n\n"

        "⚡ Explora\n"
        "🛡️ Protege\n"
        "💥 Sabotea\n"
        "🧬 Muta\n\n"

        "Añádeme a un grupo y pulsa "
        "*JUGAR*.",

        parse_mode="Markdown",

        reply_markup=main_menu()
    )


# ==========================================
# AYUDA
# ==========================================

async def ayuda(update, context):

    await update.message.reply_text(

        "🎮 *COMANDOS*\n\n"

        "/jugar — entrar en la partida\n"
        "/estado — ver estadísticas\n"
        "/mundo — ver el mundo\n"
        "/ranking — clasificación\n"
        "/ayuda — ayuda\n\n"

        "Cada jugador puede realizar "
        "una acción por ronda.",

        parse_mode="Markdown"
    )


# ==========================================
# JUGAR
# ==========================================

async def jugar(update, context):

    chat = update.effective_chat
    user = update.effective_user

    game.join(
        chat.id,
        user
    )

    group = db.get_group(
        chat.id
    )

    if not group:

        await update.message.reply_text(
            "❌ Error creando la partida."
        )

        return

    await update.message.reply_text(

        f"🌌 *RONDA {group['round']}*\n\n"

        f"{group['event']}\n\n"

        f"🌍 Energía: "
        f"{group['world_energy']}%\n"

        f"🌀 Caos: "
        f"{group['chaos']}%\n\n"

        "Elige tu acción:",

        parse_mode="Markdown",

        reply_markup=action_menu()
    )


# ==========================================
# ESTADO
# ==========================================

async def estado(update, context):

    user = update.effective_user

    game.register(user)

    player = game.status(
        user.id
    )

    await update.message.reply_text(

        f"👤 *{player['name']}*\n\n"

        f"🔋 Energía: "
        f"{player['energy']}\n"

        f"💎 Fragmentos: "
        f"{player['fragments']}\n"

        f"⭐ Puntos: "
        f"{player['score']}\n"

        f"🎮 Acciones: "
        f"{player['actions']}",

        parse_mode="Markdown"
    )


# ==========================================
# MUNDO
# ==========================================

async def mundo(update, context):

    chat_id = update.effective_chat.id

    db.create_group(
        chat_id
    )

    group = db.get_group(
        chat_id
    )

    await update.message.reply_text(

        f"🌍 *MUNDO*\n\n"

        f"🌌 Ronda: "
        f"{group['round']}\n\n"

        f"⚡ Evento: "
        f"{group['event']}\n\n"

        f"🌍 Energía: "
        f"{group['world_energy']}%\n"

        f"🌀 Caos: "
        f"{group['chaos']}%",

        parse_mode="Markdown"
    )


# ==========================================
# RANKING
# ==========================================

async def ranking(update, context):

    chat_id = update.effective_chat.id

    rows = game.ranking(
        chat_id
    )

    if not rows:

        await update.message.reply_text(
            "🏆 Todavía no hay jugadores."
        )

        return

    text = "🏆 *RANKING DEL CAOS*\n\n"

    for i, player in enumerate(rows):

        text += (
            f"{i + 1}. "
            f"{player['name']} — "
            f"⭐ {player['score']}\n"
        )

    await update.message.reply_text(
        text,
        parse_mode="Markdown"
    )


# ==========================================
# BOTONES
# ==========================================

async def buttons(update, context):

    query = update.callback_query

    await query.answer()

    user = query.from_user
    chat_id = query.message.chat.id
    data = query.data


    if data == "play":

        game.join(
            chat_id,
            user
        )

        group = db.get_group(
            chat_id
        )

        await query.edit_message_text(

            f"🌌 *RONDA {group['round']}*\n\n"

            f"{group['event']}\n\n"

            f"🌍 Energía: "
            f"{group['world_energy']}%\n"

            f"🌀 Caos: "
            f"{group['chaos']}%\n\n"

            "Elige tu acción:",

            parse_mode="Markdown",

            reply_markup=action_menu()
        )

        return


    if data == "status":

        game.register(user)

        player = game.status(
            user.id
        )

        await query.edit_message_text(

            f"👤 *{player['name']}*\n\n"

            f"🔋 Energía: "
            f"{player['energy']}\n"

            f"💎 Fragmentos: "
            f"{player['fragments']}\n"

            f"⭐ Puntos: "
            f"{player['score']}\n"

            f"🎮 Acciones: "
            f"{player['actions']}",

            parse_mode="Markdown",

            reply_markup=main_menu()
        )

        return


    if data == "world":

        group = db.get_group(
            chat_id
        )

        await query.edit_message_text(

            f"🌍 *MUNDO*\n\n"

            f"🌌 Ronda: "
            f"{group['round']}\n\n"

            f"⚡ {group['event']}\n\n"

            f"🌍 Energía: "
            f"{group['world_energy']}%\n"

            f"🌀 Caos: "
            f"{group['chaos']}%",

            parse_mode="Markdown",

            reply_markup=main_menu()
        )

        return


    if data == "ranking":

        rows = game.ranking(
            chat_id
        )

        if not rows:

            text = "🏆 No hay jugadores."

        else:

            text = "🏆 *RANKING*\n\n"

            for i, player in enumerate(rows):

                text += (
                    f"{i + 1}. "
                    f"{player['name']} — "
                    f"⭐ {player['score']}\n"
                )

        await query.edit_message_text(

            text,

            parse_mode="Markdown",

            reply_markup=main_menu()
        )

        return


    if data.startswith("action_"):

        action = data.replace(
            "action_",
            ""
        )

        success, result = game.perform_action(
            chat_id,
            user,
            action
        )

        if not success:

            await query.answer(
                result,
                show_alert=True
            )

            return

        message, count = result

        group = db.get_group(
            chat_id
        )

        await query.edit_message_text(

            f"{message}\n\n"

            f"👥 Acciones realizadas: "
            f"{count}\n\n"

            f"🌍 Energía: "
            f"{group['world_energy']}%\n"

            f"🌀 Caos: "
            f"{group['chaos']}%",

            parse_mode="Markdown",

            reply_markup=main_menu()
        )


# ==========================================
# ARRANQUE
# ==========================================

def main():

    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "ayuda",
            ayuda
        )
    )

    application.add_handler(
        CommandHandler(
            "jugar",
            jugar
        )
    )

    application.add_handler(
        CommandHandler(
            "estado",
            estado
        )
    )

    application.add_handler(
        CommandHandler(
            "mundo",
            mundo
        )
    )

    application.add_handler(
        CommandHandler(
            "ranking",
            ranking
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            buttons
        )
    )

    print(
        "🌌 CAOS INFINITO iniciado"
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
