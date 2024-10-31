import time
import requests
from flask import Flask, request, jsonify, Response, stream_with_context, g
from flask_cors import CORS
import smartsheet
from smartsheet.exceptions import ApiError
import logging
import threading
from threading import Lock
import textwrap
from teams_integration import TeamsIntegration
import sys
import random
import datetime
import pytz
import json
import subprocess
import os
from queue import Queue, Empty
import re
import dotenv
import waitress

dotenv.load_dotenv()

# Set the logging level to WARNING or higher
log = logging.getLogger('werkzeug')
log.setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.CRITICAL)

SMARTSHEET_ACCESS_TOKEN = os.environ.get('SMARTSHEET_ACCESS_TOKEN')
SMARTSHEET_SHEET_ID = 8892937224015748
# SMARTSHEET_SHEET_ID = 7492158143549316
WEBHOOK_NAME = "smartupdate-webhook"

smart = smartsheet.Smartsheet(SMARTSHEET_ACCESS_TOKEN)
smart.errors_as_exceptions(True)
sheet = smart.Sheets.get_sheet(SMARTSHEET_SHEET_ID)
column_map = {column.title: column.id for column in sheet.columns}

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5


# Get column name by id
def col_name(col_id):
    return list(column_map.keys())[list(column_map.values()).index(col_id)]


def escape_values_in_dict(data_dict):
    def escape_value(val):
        if isinstance(val, str):
            # Use json.dumps to ensure proper JSON string escaping
            return json.dumps(val)[1:-1]  # json.dumps adds double quotes, so we remove them
        return val

    return {k: escape_value(v) for k, v in data_dict.items()}


# Function to delete the existing webhook (if it exists) and create a new one
def delete_and_create_webhook(name, sheet_id):
    # Retrieve existing webhooks
    existing_webhooks = smart.Webhooks.list_webhooks().data

    # Delete all matching existing webhooks
    deleted_ids = []
    for webhook in existing_webhooks:
        if (webhook.scope == 'sheet' and
                webhook.scope_object_id == sheet_id and
                webhook.callback_url.endswith('/webhook')):

            try:
                smartsheet_api_call_with_retry(smart.Webhooks.delete_webhook, webhook.id)
                deleted_ids.append(webhook.id)
                print(f"Deleted existing webhook: {webhook.id}")
            except Exception as e:
                print(f"Failed to delete webhook {webhook.id}: {str(e)}")

    # Log all deleted webhooks
    if not deleted_ids:
        print("No matching webhooks were found to delete.")
    else:
        print(f"All matching webhooks deleted: {deleted_ids}")

    # Create a new webhook
    ngrok_process, ngrok_url = run_ngrok()
    callback_url = f'{ngrok_url}/webhook'
    new_webhook = smartsheet_api_call_with_retry(
        smart.Webhooks.create_webhook,
        smart.models.Webhook({
            "name": name,
            "callbackUrl": callback_url,
            "scope": 'sheet',
            "scopeObjectId": sheet_id,
            "events": ['*.*'],
            "version": 1
        })
    )

    # Enable the newly created webhook with retry
    if new_webhook:
        threading.Thread(target=enable_webhook_with_retry, args=(new_webhook.result.id,)).start()
        return new_webhook.result.id
    else:
        print("Failed to create new webhook.")
        return None


# Define the exponential backoff function
def exponential_backoff(attempt, max_attempts=5, base_delay=60, max_delay=300):
    if attempt >= max_attempts:
        return False
    delay = min(max_delay, base_delay * 2 ** attempt) + random.uniform(0, 10)
    print(f"Waiting for {delay:.2f} seconds before retrying...")
    time.sleep(delay)
    return True


# Define a threading.Condition object
thread_condition = threading.Condition()


# Function to wrap Smartsheet SDK calls with backoff
def smartsheet_api_call_with_retry(call, *args, **kwargs):
    attempt = 0
    max_attempts = 5
    while attempt < max_attempts:
        try:
            return call(*args, **kwargs)
        except smartsheet.exceptions.ApiError as e:
            error_message = f"Error Code: {e.error.result.error_code}, Message: {e.error.result.message}"
            if e.error.result.error_code == 4003:
                thread_condition.acquire()
                if not exponential_backoff(attempt, max_attempts):
                    print("Max retry attempts reached for rate limit error. Giving up.")
                    thread_condition.release()
                    return None
                thread_condition.release()
            elif e.error.result.error_code == 1006:
                print(f"Unable to retry, {error_message}")
                return None
            else:
                thread_condition.acquire()
                if not exponential_backoff(attempt, max_attempts, base_delay=10, max_delay=60):
                    print(f"Max retry attempts reached. {error_message}")
                    thread_condition.release()
                    return None
                thread_condition.release()
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
        attempt += 1


def enable_webhook_with_retry(webhook_id, MAX_RETRIES=5):
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(5)  # Adjust the sleep duration as needed

            # Capture the response from the update webhook call
            response = smart.Webhooks.update_webhook(
                webhook_id=webhook_id,
                webhook_obj=smart.models.Webhook({
                    "enabled": True
                })
            )

            # Convert the response to a dictionary
            response_dict = response.to_dict()
            print(response_dict)
            # Check if the webhook was successfully enabled
            if response_dict.get('data', {}).get('enabled', False):
                print("Webhook enabled successfully.")
                time.sleep(3)
                os.system('cls')
                break  # Break out of the loop if successful
            else:
                print(
                    f"Attempt {attempt + 1} failed to enable webhook. Status: {response_dict.get('data', {}).get('status', 'Unknown')}")
        except Exception as e:
            print(f"Error enabling webhook (attempt {attempt + 1}): {e}")

            # Wait before retrying
            time.sleep(RETRY_DELAY_SECONDS)
    else:
        print("Max retries reached. Webhook not enabled.")


# Function to run ngrok
def run_ngrok(max_retries=30):
    print("Checking for existing ngrok session...")

    try:
        response = requests.get('http://localhost:4040/api/tunnels')
        if response.status_code == 200:
            tunnels = response.json().get('tunnels', [])
            if tunnels:
                ngrok_url = tunnels[0]['public_url']
                print(f"Existing ngrok session found: {ngrok_url}")
                return None, ngrok_url
    except Exception as e:
        print(f"Error checking for existing ngrok sessions: {e}")

    print("Starting ngrok session...")
    creation_flags = subprocess.CREATE_NEW_CONSOLE
    ngrok_process = subprocess.Popen(['C:\\Users\\mmarcotte\\Documents\\Python\\Apps\\ngrok.exe', 'http', '8080'],
                                     creationflags=creation_flags)
    time.sleep(10)

    try:
        for attempt in range(max_retries):
            print("Checking for ngrok URL...", end="")
            try:
                ngrok_url = requests.get('http://localhost:4040/api/tunnels').json()['tunnels'][0]['public_url']
                print(f"\nNgrok URL: {ngrok_url}")
                return ngrok_process, ngrok_url
            except (IndexError, KeyError, requests.exceptions.RequestException):
                print(" failed.")
                time.sleep(10)  # Adjust based on your needs
    except KeyboardInterrupt:
        print("Ngrok URL fetch process interrupted.")

    ngrok_process.terminate()
    raise Exception("Failed to obtain ngrok public URL after multiple attempts.")


# Retrieve smartsheet cell value with column id
def get_value(sheet_arg, row_id, column_id):
    zero_val = False

    # Retrieve the row using row ID
    row = smartsheet_api_call_with_retry(sheet_arg.get_row, row_id)

    # Check if the row is not None
    if row is not None:
        # Retrieve the column value using column title
        value = row.get_column(column_id).value

        if str(value).startswith("0"):
            zero_val = True
        if str(value).startswith("+"):
            return str(value)
        try:
            value = float(value)
            if value.is_integer():
                value = int(value)
        except:
            pass

        if zero_val:
            value = "0" + str(value)
        else:
            value = str(value)

        return value
    else:
        # Handle the case where the row is not found
        return None


# Retrieve smartsheet cell value with column string
def get_value_str(sheet_arg, row_id, column_str):
    column_map = {column.title: column.id for column in sheet_arg.columns}
    zero_val = False

    # Retrieve the row using row ID
    row = smartsheet_api_call_with_retry(sheet_arg.get_row, row_id)

    # Check if the row is not None
    if row is not None:
        # Retrieve the column value using column title
        value = row.get_column(column_map.get(column_str)).value

        if str(value).startswith("0"):
            zero_val = True

        try:
            value = float(value)
            if value.is_integer():
                value = int(value)
        except:
            pass

        if zero_val:
            value = "0" + str(value)
        else:
            value = str(value)

        return value
    else:
        # Handle the case where the row is not found
        return None


user_info_cache = {}  # Cache structure: {user_id: user_info, email: user_info}
users_list_last_fetched = None
cache_ttl_seconds = 3600  # Cache TTL


def update_user_cache():
    global users_list_last_fetched, user_info_cache
    current_time = time.time()

    # Refresh cache if it's stale
    if users_list_last_fetched is None or (current_time - users_list_last_fetched > cache_ttl_seconds):
        try:
            users_list = smart.Users.list_users(include_all=True).data
            users_list_last_fetched = current_time
            # Update cache
            user_info_cache = {user.id: user for user in users_list}
            # Also map by email for email-based lookup
            for user in users_list:
                user_info_cache[user.email] = user
        except Exception as e:
            print(f"Failed to update user cache: {e}")


def get_user_name(user_id):
    # Ensure cache is up-to-date
    update_user_cache()
    if user_id == 8577180050450308:
        return "System/Automation"
    else:
        user_info = user_info_cache.get(user_id)
        if not user_info:
            return "System/Automation"

        if user_info.first_name is None or user_info.last_name is None:
            return user_info.email
        else:
            return f"{user_info.first_name} {user_info.last_name}" if user_info.first_name and user_info.last_name else user_info.email


def get_full_name_from_email(email):
    # Directly return "System/Automation" without appending domain if matched
    if email.lower() == 'system/automation':
        return "System/Automation"

    # Ensure cache is up-to-date
    update_user_cache()

    if email.lower() == 'mmarcotte@granitenet.com' or email.lower() == 'system/automation@granitenet.com':
        return "System/Automation"
    else:
        user_info = user_info_cache.get(email)
        if user_info:
            return f"{user_info.first_name} {user_info.last_name}" if user_info.first_name and user_info.last_name else email
        else:
            # Append domain only if it's an actual email and not "system/automation"
            if "@" not in email and email.lower() != 'system/automation':
                email += "@granitenet.com"
            return email


def parse_serial_numbers(serial_text):
    serial_numbers_dict = {}
    current_part = None
    lines = serial_text.strip().split("\n")

    # Improved parsing logic
    for line in lines:
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            current_part = line[1:-1].strip()
            serial_numbers_dict[current_part] = []
        elif current_part is not None:
            if line:
                serial_numbers_dict[current_part].append(line)

    if serial_numbers_dict:
        return serial_numbers_dict
    else:
        return re.sub(r'\s+', ' ', serial_text)


def print_equipment_ticket_info(ticket_num, ticket_info, add_up, timestamp):
    max_column_name_length = ticket_info['_max_column_name_length']
    user_id = ticket_info.get('user_id', '')
    separator = '─' * 100

    if add_up == "added":
        # Use "Prov Username" directly from ticket_info
        prov_username = ticket_info.get('Prov Username', 'System/Automation')
        prov_name = get_full_name_from_email(f"{prov_username}@granitenet.com")
        print(f"Equipment ticket {ticket_num} added by {prov_name} [{timestamp}]".center(100))
        action_by = prov_name
    else:
        # Use the userId to get user email or name
        user_name = get_user_name(user_id) if user_id else "System/Automation"
        print(f"Equipment ticket {ticket_num} updated by {user_name} [{timestamp}]".center(100))
        action_by = user_name

    print(separator)

    ticket_data = {
        "Equipment Ticket": ticket_num,
        "Action": add_up,
        "Action By": action_by,
        "Timestamp": timestamp
    }

    # Calculate total indentation and sub_indent outside the loop
    sub_indent = ' ' * (max_column_name_length + 3)

    # Print 'Status' column first (if updated)
    if 'Status' in ticket_info:
        updated_value = ticket_info['Status']
        ticket_data["Status"] = updated_value
        max_width = 100 - max_column_name_length - 5
        wrapped_value = textwrap.fill(str(updated_value), width=max_width)

        # Split wrapped text into lines
        lines = wrapped_value.split('\n')

        # Print the first line with the column name and align the colon to the right
        if lines:
            indentation = ' ' * (max_column_name_length - len('Status'))
            print(f' {indentation}Status:  {lines[0]}')

        # Print subsequent lines without repeating the column name
        for line in lines[1:]:
            print(f' {sub_indent}{line}')
    # Print other "Status" columns (if updated)
    for column_name, updated_value in ticket_info.items():
        if 'Status' in column_name and column_name != 'Status':
            ticket_data[column_name] = updated_value
            max_width = 100 - max_column_name_length - 5
            wrapped_value = textwrap.fill(str(updated_value), width=max_width)

            # Split wrapped text into lines
            if column_name == 'Serial Number(s)':
                parsed_serials = parse_serial_numbers(updated_value)
                ticket_data["Serial Number(s)"] = parsed_serials
                lines = updated_value.splitlines()
            else:
                lines = wrapped_value.split('\n')

            # Print the first line with the column name and align the colon to the right
            if lines:
                indentation = ' ' * (max_column_name_length - len(column_name))
                print(f' {indentation}{column_name}:  {lines[0]}')

            # Print subsequent lines without repeating the column name
            for line in lines[1:]:
                print(f' {sub_indent}{line}')
    # Print other columns
    for column_name, updated_value in ticket_info.items():
        if column_name not in {'Equipment Ticket', '_max_column_name_length', 'Status', 'Created',
                               'Created By', 'ticket_processed', 'user_id',
                               'Timestamp'} and 'Status' not in column_name:
            ticket_data[column_name] = updated_value
            max_width = 100 - max_column_name_length - 5
            wrapped_value = textwrap.fill(str(updated_value), width=max_width)

            # Split wrapped text into lines
            if column_name == 'Serial Number(s)':
                parsed_serials = parse_serial_numbers(updated_value)
                ticket_data["Serial Number(s)"] = parsed_serials
                lines = updated_value.splitlines()
            else:
                ticket_data[column_name] = updated_value
                lines = wrapped_value.split('\n')

            # Print the first line with the column name and align the colon to the right
            if lines:
                indentation = ' ' * (max_column_name_length - len(column_name))
                print(f' {indentation}{column_name}:  {lines[0]}')

            # Print subsequent lines without repeating the column name
            for line in lines[1:]:
                print(f' {sub_indent}{line}')
    # print(json.dumps(ticket_data, indent=2))
    add_ticket_to_queue(ticket_data)
    return ticket_data


def escape_value(value):
    # Escape double quotes with the escape character \
    return value.replace('\"', '\\"').replace('\'', '\\\'')


def send_adaptive_card_with_retries(teams_integration, adaptive_card_template_path, sheet, row_id, dynamic_data,
                                    max_retries=3):
    dynamic_data = {
        key: escape_value(value) for key, value in dynamic_data.items()
    }
    for retry_count in range(max_retries):
        try:
            if retry_count >= 1:
                # Re-fetch dynamic data
                dynamic_data = {
                    "prov_rep": escape_value(get_value_str(sheet, row_id, 'Prov Username')),
                    "eqp_type": escape_value(get_value_str(sheet, row_id, 'Equipment Type')),
                    "conf_rep": escape_value(get_value_str(sheet, row_id, 'Config Lab Rep')),
                    "cust_name": escape_value(get_value_str(sheet, row_id, 'Customer Name')),
                    "ticket_num": escape_value(get_value_str(sheet, row_id, 'Equipment Ticket')),
                    "requested_arrival": escape_value(get_value_str(sheet, row_id, 'Requested Arrival')),
                    "acct_num": escape_value(get_value_str(sheet, row_id, 'Child Account')),
                    "escalated_str": escape_value(
                        get_value_str(sheet, row_id, 'Escalated Order') == '1' and 'Yes' or 'No')
                }
                print(json.dumps(dynamic_data, indent=4))
            # Send adaptive card
            teams_integration.send_adaptive_card(adaptive_card_template_path, dynamic_data, retry_count)
            return "success"  # If successful, break the loop and return success
        except Exception as e:
            # print(f"An error occurred: {str(e)}")
            if retry_count < max_retries - 1:
                # print(f"Retrying in 1 second (Retry {retry_count + 1}/{max_retries})")
                time.sleep(5)
            else:
                print(f"Max retries reached. Unable to send adaptive card. Error: {e}")
    return "error"  # If max retries are reached, return an error status


app = Flask(__name__)
CORS(app)

# Global queue for all ticket data
global_tickets_queue = Queue()

# Lock for thread-safe operations on the clients list
clients_lock = Lock()

# List of client queues
client_queues = []


def add_ticket_to_queue(ticket_data):
    """
    Add ticket data to the global queue and to each client's queue.
    """
    global client_queues
    with clients_lock:
        for client_queue in client_queues:
            client_queue.put(ticket_data)


def stream_tickets(client_queue, batch_size=20, batch_timeout=5):
    """
    Stream tickets to a single client from their queue in batches.
    """
    try:
        while True:
            batch = []
            start_time = time.time()

            while len(batch) < batch_size and (time.time() - start_time) < batch_timeout:
                try:
                    ticket = client_queue.get(timeout=0.1)
                    batch.append(ticket)
                except Empty:
                    if (time.time() - start_time) >= batch_timeout:
                        break

            if batch:
                yield f"data: {json.dumps(batch)}\n\n"
            else:
                yield ": keep-alive\n\n"
    finally:
        with clients_lock:
            client_queues.remove(client_queue)


@app.route('/stream')
def stream():
    client_queue = Queue()
    with clients_lock:
        client_queues.append(client_queue)

    # Store the client_queue in the application context
    g.client_queue = client_queue

    headers = {
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Content-Type': 'text/event-stream'
    }

    return Response(stream_with_context(stream_tickets(client_queue)), headers=headers)


@app.teardown_request
def remove_client_queue(exception=None):
    client_queue = g.pop('client_queue', None)
    if client_queue:
        with clients_lock:
            if client_queue in client_queues:
                client_queues.remove(client_queue)


initial_line = False
user_id_lock = threading.Lock()


def process_webhook(data):
    global initial_line
    timestamp = ''
    try:
        # print(data)
        equipment_tickets = {}  # Store updates/additions for each ticket
        for event in data['events']:
            # print(event)
            if event['objectType'] == 'row':
                current_row = event['id']
                add_up = "updated" if event['eventType'] == 'updated' else "added"
                user_id = event.get('userId', None)

                for sub_event in data['events']:
                    if sub_event['objectType'] == 'cell' and sub_event['rowId'] == current_row:
                        row_id = sub_event['rowId']
                        try:
                            ticket_num = get_value_str(sheet, row_id, 'Equipment Ticket')
                            column_id = sub_event['columnId']
                            updated_value = get_value(sheet, row_id, column_id)
                            column_name = col_name(column_id)
                            original_timestamp = event['timestamp']
                            dt = datetime.datetime.fromisoformat(original_timestamp.rstrip('Z'))
                            eastern = pytz.timezone('US/Eastern')
                            dt_eastern = dt.astimezone(eastern)
                            timestamp = dt_eastern.strftime('%I:%M%p - %b %d %Y')
                        except Exception as e:
                            print(f"Error processing event data: {e}")

                        if ticket_num not in equipment_tickets:
                            equipment_tickets[ticket_num] = {
                                'Equipment Ticket': ticket_num,
                                '_max_column_name_length': 0,
                                '_row_id': row_id,
                                '_add_up': add_up,
                                'ticket_processed': False,
                                'Timestamp': timestamp
                            }

                        # Acquire the lock before accessing and storing user_id
                        with user_id_lock:
                            equipment_tickets[ticket_num]['user_id'] = user_id

                        if column_name == 'Escalated Order':
                            updated_value = "Yes" if int(updated_value) == 1 else "No"

                        equipment_tickets[ticket_num][column_name] = updated_value
                        equipment_tickets[ticket_num]['_max_column_name_length'] = max(
                            equipment_tickets[ticket_num]['_max_column_name_length'], len(column_name)
                        )

        for ticket_num, ticket_info in equipment_tickets.items():
            if not ticket_info['ticket_processed']:
                if not initial_line:
                    print('▄' * 100)
                    print('▀' * 100)
                    initial_line = True
                add_up = ticket_info.pop('_add_up')
                row_id = ticket_info.pop('_row_id')
                print_equipment_ticket_info(ticket_num, ticket_info, add_up, timestamp)
                ticket_info['ticket_processed'] = True

                if add_up == "added" and get_value_str(sheet, row_id, 'Equipment Type') != 'Algo/ATA/Phones':
                    print("─" * 100)
                    for attempt in range(3):
                        dynamic_data = {
                            "prov_rep": get_value_str(sheet, row_id, 'Prov Username'),
                            "eqp_type": get_value_str(sheet, row_id, 'Equipment Type'),
                            "conf_rep": get_value_str(sheet, row_id, 'Config Lab Rep'),
                            "cust_name": get_value_str(sheet, row_id, 'Customer Name'),
                            "ticket_num": get_value_str(sheet, row_id, 'Equipment Ticket'),
                            "requested_arrival": get_value_str(sheet, row_id, 'Requested Arrival'),
                            "acct_num": get_value_str(sheet, row_id, 'Child Account'),
                            "escalated_str": get_value_str(sheet, row_id,
                                                           'Escalated Order') == '1' and 'Yes' or 'No'
                        }
                        dynamic_data = escape_values_in_dict(dynamic_data)
                        if all(value for value in dynamic_data.values()):
                            break
                        elif attempt == 3:
                            break
                        else:
                            attempt += 1
                            time.sleep(2)

                    # Teams integration and adaptive card sending
                    teams_integration = TeamsIntegration(
                        team_id="364cbee7-956f-4279-938e-51355b788fe2",
                        channel_id="19:Z5RKc10ld2RPdIHLaG1N3RFgZYIZLFXw1ZD64rqOOMY1@thread.tacv2"
                    )
                    adaptive_card_template_path = "adaptive_card_template.json"
                    result = send_adaptive_card_with_retries(teams_integration, adaptive_card_template_path, sheet,
                                                             row_id, dynamic_data)
                    if result == "success":
                        print("Adaptive Card sent successfully.".center(100))
                print('▄' * 100)
                print('▀' * 100)
    except Exception as e:
        print(f"Error processing webhook data: {e}")


# Endpoint to handle incoming webhooks
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if 'challenge' in data:
        # Respond to verification challenge
        return jsonify({"smartsheetHookResponse": data['challenge']})
    else:
        # Handle webhook data
        thread = threading.Thread(target=process_webhook, args=(data,))
        thread.start()
        return jsonify({'status': 'Webhook received, processing in background'})


@app.route('/api/smartsheet/metric-value', methods=['GET'])
def get_metric_value():
    # "metric_name": (row_id, column_id)
    metric_dict = {
        "Average Days to Ship": (6835787952197508, 6859193865686916),  # days from creation to ship
        "Current Open Tickets": (6835787952197508, 1229694331473796),  # current open tickets
        "Active Escalations": (7961687859040132, 6859193865686916),  # current open escalations
        "Tickets Created (Past 60 Days)": (3833559068807044, 92410932580228),  # sum tickets added past 30 days
        "Tickets Shipped (Past 60 Days)": (3833559068807044, 4596010559950724),  # sum tickets shipped past 30 days
        "Shipping Variance (Actual Ship vs Requested Ship)": (6835787952197508, 5733293958844292),
        # +/- requested ship vs actual ship
        "Shipped On Time %": (6835787952197508, 4905128030064516)
    }

    metric_values = {}
    metric_sheet = smart.Sheets.get_sheet(7492158143549316)
    for metric_name, (row_id, column_id) in metric_dict.items():
        # Use the get_value function to retrieve the value for each metric
        metric_value = str(get_value(metric_sheet, row_id, column_id))
        metric_values[metric_name] = metric_value

    return jsonify(metric_values)


def run_debug():
    app.run(host="0.0.0.0", port=8080, debug=True, use_reloader=False)


def run_waitress():
    waitress.serve(app, host="0.0.0.0", port=8080)


if __name__ == '__main__':
    # Delete existing webhook (if it exists) and create a new one
    webhook_id = delete_and_create_webhook(WEBHOOK_NAME, SMARTSHEET_SHEET_ID)
    print(f"Webhook ID: {webhook_id}")

    # Uncomment below to run app in either debug mode or production

    # debug
    # run_debug()

    # production
    run_waitress()
