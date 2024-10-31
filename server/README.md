# LiveUpdate Server

This repository contains the server-side code for the LiveUpdate application, built using Python and Flask. The server integrates with Microsoft Teams and utilizes the Smartsheet API.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Environment Variables](#environment-variables)
- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Features

- Authentication with Microsoft Teams using OAuth2.
- Webhook integration with Smartsheet to handle real-time updates.
- Endpoint to stream ticket data in real-time.
- Adaptive card notifications sent to a Teams channel.

## Requirements

- Python 3.x
- Flask
- Requests
- MSAL (Microsoft Authentication Library)
- Smartsheet SDK

## Environment Variables

Before running the application, set the following environment variables in your `.env` file or your environment:

- `TEAMS_TENANT_ID`: The Tenant ID for your Microsoft Teams application.
- `TEAMS_CLIENT_ID`: The Client ID for your Microsoft Teams application.
- `TEAMS_CLIENT_SECRET`: The Client Secret for your Microsoft Teams application.
- `SMARTSHEET_ACCESS_TOKEN`: The access token for the Smartsheet API.
- `SMARTSHEET_SHEET_ID`: The ID of the Smartsheet to interact with.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/xmmarcotte/LiveUpdate.git
   ```

2. Navigate to the server directory:

   ```bash
   cd LiveUpdate/server
   ```

3. Create a virtual environment and activate it:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

4. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Set up your environment variables as mentioned above.
2. Run the server:

   ```bash
   python app.py
   ```

3. The server will start, and you can interact with the endpoints defined in `app.py`.

## License

This project is intended for Granite Telecommunications internal use.
