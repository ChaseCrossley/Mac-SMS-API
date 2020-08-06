from sqlite3 import Connection

from flask import Flask, jsonify
from flask import request
import sqlite3
import time
import threading
import subprocess
from ScriptingBridge import SBApplication
from pathlib import Path

app = Flask(__name__)

CONTINUATION_STRING = "CONTINUE"
DISCONTINUATION_STRING = "STOP"
MAX_ITERATION_COUNT = 3
MESSAGE_SET_SIZE = 5
LAST_ROW_NUMBER = 1363
BEGINNING_STRING = "You have signed up to receive the lines of the bee movie script line by line. At any point you " \
                   f"can opt out of this program by sending a message containing the string: {DISCONTINUATION_STRING}. " \
                   f"In an interest to your time and my CPU, I will only send lines {MESSAGE_SET_SIZE} at a time in " \
                   f"the beginning. There will be {MAX_ITERATION_COUNT} of message sets before I SPAM you with " \
                   f"the rest of the bee movie script. The entire bee movie script is {LAST_ROW_NUMBER} lines long. " \
                   f"Meaning you will receive {LAST_ROW_NUMBER} messages. MESSAGE AND DATA RATES DO APPLY. " \
                   f"If you would like to continue please send us a message containing the string: {CONTINUATION_STRING}"
Messages = SBApplication.applicationWithBundleIdentifier_("com.apple.iChat")
most_recent_date = 0
first_message_que = []
phone_number_iteration = {}
BEE_MOVIE_PATH = 'static/bee movie script.txt'


@app.route('/', methods=['POST', 'GET'])
def add_phone_number():
    if request.method == 'POST':
        data = request.get_json()
        phone_number = data.get('phone number')
        phone_number_iteration.update({phone_number: 0})
        first_message_que.append(phone_number)
        return jsonify(f"I have started communication with {phone_number}")
    if request.method == 'GET':
        return 'I AM WORKING'


def send_message(phone_number: str, message: str, SPAM=False, delimiter=None, use_script=False):
    if message:
        if use_script:
            subprocess.check_call('./static/sendMessage.sh "%s" "%s"' % (phone_number, message.replace('"', '\\"')),
                                  shell=True)
            return

        buddy_to_message = [b for b in Messages.buddies() if
                            b.fullName().replace('(', '').replace(')', '').replace(' ', '').replace('-',
                                                                                                    '') == phone_number][
            0]
        if SPAM:
            assert delimiter
            for sub_message in message.split(sep=delimiter):
                Messages.send_to_(sub_message, buddy_to_message)
        else:
            Messages.send_to_(message, buddy_to_message)


def connect_to_db():
    return sqlite3.connect(f'{Path.home()}/Library/Messages/chat.db')


def get_initial_most_recent_date(db_connection: Connection):
    cursor = db_connection.execute(
        "SELECT date FROM message "
        f"WHERE is_from_me == 0 "
        "ORDER BY date DESC")
    return cursor.fetchone()[0]


def poll(db_connection: Connection):
    global most_recent_date
    cursor = db_connection.execute(
        "SELECT \"text\" as message, date, handle.id as \"phone number\" FROM message INNER JOIN "
        "handle on message.handle_id = handle.ROWID "
        f"WHERE date > {most_recent_date} AND is_from_me == 0 "
        "ORDER BY date DESC")
    return cursor.fetchall()


def get_file_lines(start_lines, end_line):
    data = ""
    with open(BEE_MOVIE_PATH, "r") as BEE_MOVIE:
        script = BEE_MOVIE.readlines()
        for line_num in range(start_lines, end_line):
            data += script[line_num]
    return data


""" message should be a tuple of (message:string, date:int(long), phone_number:string)"""


def valid_message(message_data: tuple):
    global most_recent_date
    global CONTINUATION_STRING
    global DISCONTINUATION_STRING

    message_text = message_data[0]
    date = message_data[1]
    most_recent_date = date if most_recent_date < date else most_recent_date
    if CONTINUATION_STRING in message_text.upper() or DISCONTINUATION_STRING in message_text.upper():
        return True
    else:
        return False


""" message should be a tuple of (message:string, date:int(long), phone_number:string)"""


def send_rest_of_messages(phone_number: str):
    send_message(phone_number, get_file_lines(5 * MAX_ITERATION_COUNT, LAST_ROW_NUMBER), SPAM=True, delimiter='\n')


def send_first_messages():
    while True:
        if first_message_que:
            send_message(first_message_que[0], BEGINNING_STRING, use_script=True)
            first_message_que.pop(0)
            time.sleep(4)


def get_next_message(message_data: tuple):
    global phone_number_iteration
    global CONTINUATION_STRING
    global DISCONTINUATION_STRING
    message_text = message_data[0]
    phone_number = message_data[2]

    if CONTINUATION_STRING in message_text.upper():
        iteration = phone_number_iteration.get(phone_number) + 1
        phone_number_iteration.update({phone_number: iteration})
        if iteration > MAX_ITERATION_COUNT:
            return send_rest_of_messages(phone_number)
        else:
            continuation_message = f"This is message set {iteration}. You have {MAX_ITERATION_COUNT - iteration}" \
                                   f" set(s) until the rest of the script is sent." if MAX_ITERATION_COUNT != iteration \
                else "WARNING WARNING WARNING WARNING this is the LAST TIME to opt out before the rest of the " \
                     "script is sent. Once you start the process there is no going back. " \
                     "REMEMBER message rates DO apply."
            return get_file_lines((iteration - 1) * MESSAGE_SET_SIZE,
                                  (iteration - 1) * MESSAGE_SET_SIZE + MESSAGE_SET_SIZE) + continuation_message
    else:
        phone_number_iteration.pop(phone_number)
        return "We have canceled your contact information. Don't forget to check out actual club meetings of the CBU " \
               "ACM."


""" message should be a tuple of (message:string, date:int(long), phone_number:string)"""


def get_contact_info(message_data : tuple):
    return message_data[2]


if __name__ == '__main__':
    REST_API = threading.Thread(target=app.run, kwargs=({"host": '0.0.0.0', "port": "80"}), daemon=True)
    REST_API.start()

    first_contact = threading.Thread(target=send_first_messages, daemon=True)
    first_contact.start()

    db_conn = connect_to_db()
    most_recent_date = get_initial_most_recent_date(db_conn)
    while True:
        new_messages = poll(db_conn)
        if new_messages:
            for message_data in new_messages:
                if valid_message(message_data):
                    processThread = threading.Thread(target=send_message, daemon=True, args=(
                        get_contact_info(message_data), get_next_message(message_data), True, '\n',))
                    processThread.start()
        time.sleep(3)
