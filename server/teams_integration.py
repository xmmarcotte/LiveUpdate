import os
import requests
from msal import ConfidentialClientApplication
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from threading import Thread, Event
import uuid
import time


class TeamsIntegrationException(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP Error {self.status_code}: {self.message}")


def escape_values_in_dict(data_dict):
    return json.loads(json.dumps(data_dict))


class TeamsIntegration:
    def __init__(self, team_id, channel_id):
        self.tenant_id = os.getenv('TEAMS_TENANT_ID')
        self.client_id = os.getenv('TEAMS_CLIENT_ID')
        self.client_secret = os.getenv('TEAMS_CLIENT_SECRET')
        self.team_id = team_id
        self.channel_id = channel_id
        self.redirect_uri = "http://localhost:8888"  # Change the port if needed
        self.authorize_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize?client_id={self.client_id}&scope=https://graph.microsoft.com/.default offline_access&response_type=code&redirect_uri={self.redirect_uri}"
        self.token_file_path = "token.json"
        self.session = requests.Session()

        self.app = ConfidentialClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            client_credential=self.client_secret,
        )

        self.scope = ["https://graph.microsoft.com/.default"]
        self.token_response = None
        # Add an event object for synchronization
        self.auth_completed_event = Event()

    def start_http_server(self, port=8888):
        server_address = ("127.0.0.1", port)
        httpd = HTTPServer(server_address,
                           lambda *args, **kwargs: TeamsIntegrationRedirectHandler(teams_integration=self,
                                                                                   *args, **kwargs))

        # print(f"Starting server on {server_address[0]}:{server_address[1]}...")
        httpd.handle_request()

    def authenticate(self):
        token_response = self.load_token_from_file()

        if token_response and 'access_token' in token_response:
            if not self.is_token_expired(token_response) and self.test_token_validity(token_response):
                return token_response
            elif 'refresh_token' in token_response:
                silent_response = self.acquire_token_by_refresh_token(token_response['refresh_token'])
                if silent_response:
                    return silent_response

        print("Attempting interactive token acquisition.")
        return self.acquire_new_token()

    def acquire_token_by_refresh_token(self, refresh_token):
        token_response = self.app.acquire_token_by_refresh_token(refresh_token, scopes=self.scope)

        if "access_token" in token_response:
            self.save_token_to_file(token_response)
            print("Refresh token acquired!")
            return token_response
        else:
            print("Failed to acquire token by refresh token. Error: ", token_response.get("error_description"))
            return None

    def delete_token_file(self):
        if os.path.exists(self.token_file_path):
            os.remove(self.token_file_path)
            # print("Token file deleted.")

    def test_token_validity(self, token_response):
        # Make a test API call using the access token
        graph_url = "https://graph.microsoft.com/v1.0/users"
        headers = {
            "Authorization": f"Bearer {token_response['access_token']}",
            "Accept": "application/json"
        }
        params = {
            "$filter": f"userPrincipalName eq 'mmarcotte@granitenet.com'"
        }

        response = self.session.get(graph_url, headers=headers, params=params)
        if response.status_code == 200:
            return True

    def save_token_to_file(self, token_response):
        with open(self.token_file_path, 'w') as file:
            json.dump(token_response, file)
            # print("Token saved to file.")

    def load_token_from_file(self):
        if os.path.exists(self.token_file_path):
            with open(self.token_file_path, 'r') as file:
                return json.load(file)
        return None

    def is_token_expired(self, token_response):
        try:
            expiration_seconds = int(token_response['expires_in'])
        except KeyError:
            print("Error: 'expires_in' not found in token response.")
            return False

        current_timestamp = int(time.time())

        if expiration_seconds <= 0:
            return 'refresh_token' not in token_response

        # Calculate the absolute expiration time ('expires_on')
        expires_on = current_timestamp + expiration_seconds

        return current_timestamp >= expires_on

    def acquire_new_token(self):
        max_retries = 3  # Set a maximum number of retry attempts
        retry_delay = 5  # Set a delay between retries (in seconds)

        for _ in range(max_retries):
            # Start the HTTP server on a separate thread
            server_thread = Thread(target=self.start_http_server)
            server_thread.start()

            # Open the authorization URL in the default web browser
            webbrowser.open(self.authorize_url, new=2, autoraise=True)

            # Wait for the authentication process to complete or timeout
            auth_completed = self.auth_completed_event.wait(timeout=60)

            # Close the HTTP server
            server_thread.join()

            # Check if the authentication was completed and token response is available
            if auth_completed and self.token_response:
                # Save the token to the file
                self.save_token_to_file(self.token_response)
                return self.token_response
            else:
                print("Error: Authentication may not have been completed. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)

        print("Error: Authentication failed after multiple retries.")
        return None

    def get_user_info(self, username):
        token_response = self.authenticate()
        if username == "swong":
            username = "stwong"
        if username == "jaroth":
            username = "jroth"
        graph_url = "https://graph.microsoft.com/v1.0/users"
        headers = {
            "Authorization": f"Bearer {token_response['access_token']}",
            "Accept": "application/json"
        }
        params = {
            "$filter": f"userPrincipalName eq '{username}@granitenet.com'"
        }

        response = self.session.get(graph_url, headers=headers, params=params)

        if response.status_code == 200:
            user_info = response.json()
            if 'value' in user_info and len(user_info['value']) > 0:
                user = user_info['value'][0]
                return {
                    "id": user.get("id", ""),
                    "userPrincipalName": user.get("userPrincipalName", ""),
                    "displayName": user.get("displayName", "")
                }
            else:
                # print(f"Error: User not found for username {username}")
                # print(f"Response JSON: {json.dumps(user_info, indent=2)}")  # Add this line for debugging
                return None
        else:
            # print(f"Error: {response.status_code}, {response.text}")
            return None

    def send_adaptive_card(self, template_path, dynamic_data, retry_count):
        dynamic_data = escape_values_in_dict(dynamic_data)
        # Read the Adaptive Card template from the provided file
        with open(template_path, 'r', encoding='utf-8') as template_file:
            adaptive_card_template = json.load(template_file)

        # Generate a unique ID for the Adaptive Card
        card_id = str(uuid.uuid4())
        # Fetch user information
        try:
            prov_rep_info = self.get_user_info(dynamic_data.get('prov_rep', ''))
        except:
            if retry_count == 3:
                prov_rep_info = ''
        try:
            conf_rep_info = self.get_user_info(dynamic_data.get('conf_rep', ''))
        except:
            if retry_count == 3:
                conf_rep_info = ''

        # Replace placeholders in the Adaptive Card template with dynamic data
        dynamic_data["prov_rep_display"] = prov_rep_info.get('displayName', '')
        dynamic_data["conf_rep_display"] = conf_rep_info.get('displayName', '')

        # Replace placeholders in the Adaptive Card template with dynamic data
        self.recursive_replace(adaptive_card_template, dynamic_data)

        # Generate a new ID
        attachment_id = str(uuid.uuid4())

        adaptive_card_template = json.dumps(adaptive_card_template, indent=2)

        # # Debug print: Print the modified Adaptive Card template
        # print("Modified Adaptive Card Template:")
        # print(adaptive_card_template)

        # Construct the payload with user information and the generated ID
        payload = {
            "body": {
                "contentType": "html",
                "content": f"<attachment id=\"{attachment_id}\"></attachment>"
            },
            "attachments": [
                {
                    "id": attachment_id,
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": adaptive_card_template
                }
            ],
            "mentions": [
                {
                    "id": 0,
                    "mentionText": f"{prov_rep_info.get('displayName', '')}",
                    "mentioned": {
                        "user": {
                            "@odata.type": "#microsoft.graph.teamworkUserIdentity",
                            "id": prov_rep_info.get('id', ''),
                            "displayName": prov_rep_info.get('displayName', ''),
                            "userIdentityType": "aadUser"
                        }
                    }
                },
                {
                    "id": 1,
                    "mentionText": f"{conf_rep_info.get('displayName', '')}",
                    "mentioned": {
                        "user": {
                            "@odata.type": "#microsoft.graph.teamworkUserIdentity",
                            "id": conf_rep_info.get('id', ''),
                            "displayName": conf_rep_info.get('displayName', ''),
                            "userIdentityType": "aadUser"
                        }
                    }
                }
            ]
        }

        # # Uncomment for payload debug
        # print("Payload:")
        # print(json.dumps(payload, indent=2))

        # Send the payload
        self.send_html_message(payload)

    def recursive_replace(self, obj, data):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    self.recursive_replace(value, data)
                elif isinstance(value, str):
                    for data_key, data_value in data.items():
                        placeholder = "{" + data_key + "}"
                        obj[key] = obj[key].replace(placeholder, str(data_value))

        elif isinstance(obj, list):
            for i in obj:
                self.recursive_replace(i, data)

    def send_html_message(self, payload):
        token_response = self.authenticate()

        # Define the request headers
        headers = {
            "Authorization": f"Bearer {token_response['access_token']}",
            "Content-Type": "application/json",
        }

        # # Debug print: Raw JSON being sent
        # print("Raw JSON being sent:")
        # print(json.dumps(payload, indent=2))

        # Create payload for sending the HTML message
        teams_url = f"https://graph.microsoft.com/v1.0/teams/{self.team_id}/channels/{self.channel_id}/messages"
        response = self.session.post(teams_url, headers=headers, json=payload)

        if response.status_code not in [200, 201, 202]:
            raise TeamsIntegrationException(response.status_code, response.text)

    @staticmethod
    def create_mention(display_name, user_id):
        return {
            "id": user_id,
            "mentionText": display_name,
            "mentioned": {
                "@odata.type": "#microsoft.graph.teamworkUserIdentity",
                "id": user_id,
                "displayName": display_name,
                "userIdentityType": "aadUser"
            }
        }

    def get_all_teams(self):
        token_response = self.authenticate()

        if token_response:
            headers = {
                "Authorization": f"Bearer {token_response['access_token']}",
                "Accept": "application/json"
            }
            graph_url = "https://graph.microsoft.com/beta/groups"
            response = self.session.get(graph_url, headers=headers)

            if response.status_code == 200:
                teams_info = response.json()
                team_dict = {team['id']: team['displayName'] for team in teams_info.get('value', [])}
                return team_dict
            else:
                print(f"Error fetching teams: {response.status_code}, {response.text}")
                # Optionally, you can print more details about the error
                try:
                    error_details = response.json()
                    print("Error details:", error_details)
                except json.JSONDecodeError:
                    print("Error decoding JSON response.")
        return None

    def get_team_emails(self, team_id):
        token_response = self.authenticate()

        if token_response:
            headers = {
                "Authorization": f"Bearer {token_response['access_token']}",
                "Accept": "application/json"
            }
            graph_url = f"https://graph.microsoft.com/v1.0/groups/{team_id}/members"
            response = self.session.get(graph_url, headers=headers)

            if response.status_code == 200:
                members_info = response.json()
                emails = [member['userPrincipalName'] for member in members_info['value']]
                return emails
            else:
                print(f"Error fetching team members: {response.status_code}, {response.text}")

        return None


class TeamsIntegrationRedirectHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.teams_integration = kwargs.pop('teams_integration', None)
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        # Only log error messages (status codes 400 and above)
        if args[1].startswith("4") or args[1].startswith("5"):
            super().log_message(format, *args)

    def do_GET(self):
        if self.path == '/favicon.ico':
            # Ignore requests for favicon.ico
            return

        query = urlparse(self.path).query
        params = parse_qs(query)
        auth_code = params.get("code", [""])[0]

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><head><title>Authentication Complete</title></head>")
        self.wfile.write(b"<body><p>Authentication completed. This window will close shortly.</p></body></html>")

        if auth_code:
            # print("Received authorization code:", auth_code)

            try:
                token_response = self.teams_integration.app.acquire_token_by_authorization_code(
                    auth_code,
                    scopes=self.teams_integration.scope,
                    redirect_uri=self.teams_integration.redirect_uri,
                )

                # print("Token response:", token_response)

                if "access_token" not in token_response:
                    print("Access token not found in the token response.")
                    raise ValueError("Access token not found in token response.")

                # Set the token_response and signal that authentication is completed
                self.teams_integration.token_response = token_response
                self.teams_integration.auth_completed_event.set()

            except Exception as e:
                print(f"Error during token retrieval: {e}")

        # Include JavaScript to close the window
        self.wfile.write(b"<script>window.close();</script>")


if __name__ == "__main__":
    teams_integration = TeamsIntegration(
        team_id="364cbee7-956f-4279-938e-51355b788fe2",
        channel_id="19:Z5RKc10ld2RPdIHLaG1N3RFgZYIZLFXw1ZD64rqOOMY1@thread.tacv2"
    )
