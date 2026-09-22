import os
import time

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
    raise RuntimeError(
        "Falta la variable BOT_TOKEN"
    )


db = Database()
game = Game(db)


# ==========================================
# MENÚ PRINCIPAL
# ==========================================

def main_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "🎮 JUGAR",
                callback_data="play"
            ),

            InlineKeyboardButton(
                "📊 MI ESTADO",
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

    return InlineKeyboardMarkup(
        keyboard
    )


# ==========================================
# MENÚ DE ACCIONES
# ==========================================

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
                "🌍 VER MUNDO",
                callback_data="world"
            )
        ]

    ]

    return InlineKeyboardMarkup(
        keyboard
    )


# ==========================================
# /start
# ==========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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

        "Tus decisiones afectan "
        "a todos los jugadores.\n\n"

        "Añádeme a un grupo y pulsa "
        "*JUGAR*.",

        parse_mode="Markdown",

        reply_markup=main_menu()
    )


# ==========================================
# /ayuda
# ==========================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "🎮 *CAOS INFINITO*\n\n"

        "/jugar — entrar en la partida\n"
        "/estado — tus estadísticas\n"
        "/mundo — estado del mundo\n"
        "/ranking — clasificación\n"
        "/ayuda — ayuda\n\n"

        "⚠️ Cada jugador puede realizar "
        "una acción por ronda.\n\n"

        "🌍 Las acciones modifican "
        "el mundo compartido.",

        parse_mode="Markdown"
    )


# ==========================================
# CREAR / INICIAR PARTIDA
# ==========================================

async def play(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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
            "❌ No se pudo crear la partida."
        )

        return

    now = int(time.time())

    # Si la ronda terminó,
    # comenzamos una nueva.

    if group["round_ends"] <= now:

        game.start_round(
            chat.id
        )

        group = db.get_group(
            chat.id
        )

    seconds = max(
        0,
        group["round_ends"] - now
    )

    await update.message.reply_text(

        f"🌌 *RONDA {group['round']}*\n\n"

        f"{group['event']}\n\n"

        f"🌍 Energía mundial: "
        f"{group['world_energy']}%\n"

        f"🌀 Caos: "
        f"{group['chaos']}%\n\n"

        f"⏱️ Tiempo aproximado: "
        f"{seconds}s\n\n"

        "Elige tu acción:",

        parse_mode="Markdown",

        reply_markup=action_menu()
    )


# ==========================================
# /estado
# ==========================================

async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    game.register(
        user
    )

    player = game.status(
        user.id
    )

    if not player:

        await update.message.reply_text(
            "❌ No estás registrado."
        )

        return

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
# /mundo
# ==========================================

async def world(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat_id = update.effective_chat.id

    db.create_group(
        chat_id
    )

    group = db.get_group(
        chat_id
    )

    await update.message.reply_text(

        f"🌍 *ESTADO DEL MUNDO*\n\n"

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
# /ranking
# ==========================================

async def ranking(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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

    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]

    for index, player in enumerate(rows):

        if index < 3:
            prefix = medals[index]
        else:
            prefix = f"{index + 1}."

        text += (
            f"{prefix} "
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

async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    chat_id = query.message.chat.id

    data = query.data


    # ======================================
    # JUGAR
    # ======================================

    if data == "play":

        game.join(
            chat_id,
            user
        )

        group = db.get_group(
            chat_id
        )

        now = int(time.time())

        if group["round_ends"] <= now:

            game.start_round(
                chat_id
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


    # ======================================
    # ESTADO
    # ======================================

    if data == "status":

        game.register(
            user
        )

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


    # ======================================
    # RANKING
    # ======================================

    if data == "ranking":

        rows = game.ranking(
            chat_id
        )

        if not rows:

            text = (
                "🏆 Todavía no "
                "hay jugadores."
            )

        else:

            text = (
                "🏆 *RANKING DEL CAOS*\n\n"
            )

            for i, player in enumerate(
                rows
            ):

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


    # ======================================
    # MUNDO
    # ======================================

    if data == "world":

        db.create_group(
            chat_id
        )

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


    # ======================================
    # ACCIONES
    # ======================================

    if data.startswith(
        "action_"
    ):

        action = data.replace(
            "action_",
            ""
        )

        success, result = (
            game.perform_action(
                chat_id,
                user,
                action
            )
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

            f"👥 Jugadores que "
            f"ya actuaron: {count}\n\n"

            f"🌍 Energía mundial: "
            f"{group['world_energy']}%\n"

            f"🌀 Caos: "
            f"{group['chaos']}%",

            parse_mode="Markdown",

            reply_markup=main_menu()
        )

        return


# ==========================================
# ARRANQUE
# ==========================================

def build_application():

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
            help_command
        )
    )

    application.add_handler(
        CommandHandler(
            "jugar",
            play
        )
    )

    application.add_handler(
        CommandHandler(
            "estado",
            status
        )
    )

    application.add_handler(
        CommandHandler(
            "mundo",
            world
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

    return application


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":

    print(
        "🌌 CAOS INFINITO iniciado."
    )

    app = build_application()

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
  )
