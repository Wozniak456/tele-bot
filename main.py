import telebot
from telebot import types
import psycopg2
from user import *

bot = telebot.TeleBot('')
name = ''
user_found = False
user = None
selected_day = 0
poll_list = {}


def connect():
    conn = psycopg2.connect(
        host="localhost",
        dbname="postgres",
        user="postgres",
        password="admin",
        port=5432
    )
    cur = conn.cursor()
    return conn, cur


@bot.message_handler(commands=['start_bot'])
def main(message):
    global user, user_found, name
    conn, cur = connect()
    user_data = None
    cur.execute("SELECT temp_id, name, pass FROM users WHERE temp_id = %s;", (message.from_user.id,))
    user_data = cur.fetchone()

    if user_data is None:
        bot.send_message(message.chat.id, 'Привіт! Введи своє ім\'я:')
        bot.register_next_step_handler(message, user_name)
    else:
        temp_id, name, password = user_data
        user = User(temp_id, name, password)
        user_found = True
        # bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.send_message(message.chat.id, f'Привіт, {message.from_user.first_name}! Чим можу бути корисним?',
                         reply_markup=default_markup())


def user_name(message):
    global name
    name = message.text.strip()
    bot.send_message(message.chat.id, 'А тепер пароль:')
    bot.register_next_step_handler(message, user_pass)


def user_pass(message):
    global user_found, user
    password = message.text.strip()
    conn, cur = connect()

    cur.execute("SELECT temp_id, pass FROM users WHERE name = %s;", (name,))
    user_data = cur.fetchone()
    if user_data:
        user_id, user_pass = user_data
        cur.execute("update users set temp_id = %s where temp_id = %s;", (message.from_user.id, user_id,))
        user_found = True

        user = User(message.from_user.id, name, password)
        bot.send_message(message.chat.id, f"Знайдено користувача: : ID - {user.id}")

        markup = default_markup()
        bot.send_message(message.chat.id, f'Привіт, {message.from_user.first_name}! Чим можу бути корисним?',
                          reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Користувача не знайдено")

    conn.commit()
    cur.close()
    conn.close()


def default_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Переглянути меню')
    markup.row(btn1)
    btn2 = types.KeyboardButton('Сформувати власне меню')
    btn3 = types.KeyboardButton('Переглянути створене меню')
    markup.row(btn2, btn3)
    return markup


@bot.message_handler(func=lambda message: user_found and message.text == 'Переглянути меню')
def show_menu(message):
    if message.text == 'Переглянути меню':
        bot.send_message(message.chat.id, 'Дивимось меню...')
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Понеділок', callback_data='Понеділок'))
        markup.add(types.InlineKeyboardButton('Вівторок', callback_data='Вівторок'))
        markup.add(types.InlineKeyboardButton('Середа', callback_data='Середа'))
        markup.add(types.InlineKeyboardButton('Четвер', callback_data='Четвер'))
        markup.add(types.InlineKeyboardButton('П\'ятниця', callback_data='П''ятниця'))
        bot.send_message(message.chat.id, f'Оберіть день, щоб оглянути меню:',
                         reply_markup=markup)


@bot.message_handler(func=lambda message: user_found and message.text == 'Сформувати власне меню')
def create_menu(message):
    if message.text == 'Сформувати власне меню':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Понеділок', callback_data='form_menu_monday'))
        markup.add(types.InlineKeyboardButton('Вівторок', callback_data='form_menu_tuesday'))
        markup.add(types.InlineKeyboardButton('Середа', callback_data='form_menu_wednesday'))
        markup.add(types.InlineKeyboardButton('Четвер', callback_data='form_menu_thursday'))
        markup.add(types.InlineKeyboardButton('П\'ятниця', callback_data='form_menu_friday'))
        bot.send_message(message.chat.id, f'Оберіть день, щоб сформувати меню:',
                         reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'form_menu_monday' or call.data == 'form_menu_tuesday'
                                              or call.data == 'form_menu_wednesday' or call.data == 'form_menu_thursday'
                                              or call.data == 'form_menu_friday')
def callback_form_menu(callback):
    global selected_day, poll_list
    message = callback.message  # form_menu_monday
    if callback.data == 'form_menu_monday':
        selected_day = 1
    elif callback.data == 'form_menu_tuesday':
        selected_day = 2
    elif callback.data == 'form_menu_wednesday':
        selected_day = 3
    elif callback.data == 'form_menu_thursday':
        selected_day = 4
    elif callback.data == 'form_menu_friday':
        selected_day = 5

    if selected_day is not None:
        conn, cur = connect()

        dish_types = ['first_dishes', 'second_dishes', 'desserts', 'drinks']

        for dish_type in dish_types:
            query = "select dish_id, name from {};".format(dish_type)
            cur.execute(query)
            user_data = cur.fetchall()
            options = {}
            for item in user_data:
                options[item[0]] = item[1]

            poll = bot.send_poll(message.chat.id, "Обери страву:", list(options.values()), is_anonymous=False,
                                 )
            poll_list[dish_type] = poll.poll.id

        cur.close()
        conn.close()
    else:
        bot.send_message(message.chat.id, 'nothing')


@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    global selected_day, poll_list

    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids

    bot.send_message(user_id, f"You voted for option with IDs: {option_ids}.")

    conn, cur = connect()
    matching_key = None
    for key, value in poll_list.items():
        if value == poll_id:
            matching_key = key
            break
    if matching_key is not None:
        sql = "insert into chosen_meal_schedule(user_id, day_id, dish_id) values (%s, %s, " \
              "(select id from {} where dish_id = %s));".format(matching_key)
        cur.execute(sql, (user_id, selected_day, option_ids[0] + 1,))

    conn.commit()
    cur.close()
    conn.close()


@bot.message_handler(func=lambda message: user_found and message.text == 'Переглянути створене меню')
def create_menu(message):
    if message.text == 'Переглянути створене меню':
        conn, cur = connect()
        cur.execute("SELECT days.day FROM days LEFT JOIN chosen_meal_schedule ch_m ON days.id = ch_m.day_id "
                    "AND ch_m.user_id = %s WHERE ch_m.user_id IS NULL", (user.id,))
        default_days = cur.fetchall()

        cur.execute("select distinct days.day from days LEFT join chosen_meal_schedule ch_m on days.id = ch_m.day_id "
                    "AND ch_m.user_id = %s where dish_id is not null", (user.id,))
        formed_days = cur.fetchall()

        cur.execute("select days.day from days")
        all_days = cur.fetchall()

        for day in all_days:
            if day in formed_days:
                cur.execute("select dishes.name from chosen_meal_schedule ch_m "
                            "inner join dishes on dishes.id = ch_m.dish_id "
                            "inner join days on days.id = ch_m.day_id "
                            "where user_id = %s and days.day = %s "
                            "order by dishes.dish_type_id",
                                (user.id, day,))
                user_data = cur.fetchall()
                user_message = f'{day[0]}:\n'
                for item in user_data:
                    user_message += f'{item[0]}\n'
                bot.send_message(message.chat.id, user_message)
            elif day in default_days:
                cur.execute(
                    "select dishes.name from meal_schedule m_sch inner join dishes on dishes.id = m_sch.dish_id "
                    "inner join days on days.id = m_sch.day_id where days.day in (%s) order by dishes.dish_type_id",
                    (day,))
                user_data = cur.fetchall()
                user_message = f'{day[0]}. Звичайне меню:\n'
                for item in user_data:
                    user_message += f'{item[0]}\n'
                bot.send_message(message.chat.id, user_message)

        cur.close()
        conn.close()


@bot.callback_query_handler(func=lambda call: call.data == 'Понеділок' or call.data == 'Вівторок'
                                              or call.data == 'Середа' or call.data == 'Четвер'
                                              or call.data == 'П''ятниця')
def callbackmessage(callback):
    message = callback.message
    selected_day = callback.data
    if selected_day == 'Пятниця':
        selected_day = "П'ятниця"
    conn, cur = connect()
    cur.execute("select day from days")
    days = cur.fetchall()
    for day in days:
        day = day[0]
        if day == selected_day:
            cur.execute("SELECT dishes.name FROM meal_schedule as m "
                        "INNER JOIN dishes ON m.dish_id = dishes.id "
                        "INNER JOIN dish_type ON dishes.dish_type_id = dish_type.id "
                        "INNER JOIN days ON m.day_id = days.id WHERE day = %s;", (day,))
            user_data = cur.fetchall()
            user_message = f"У меню на {day}:\n"
            for dish in user_data:
                user_message += f'\n{dish[0]}'
            bot.send_message(message.chat.id, user_message)
            break

    cur.close()
    conn.close()


bot.polling(none_stop=True)



