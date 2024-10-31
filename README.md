
# LiveUpdate

The **LiveUpdate** project is a full-stack application designed for real-time equipment ticket updates. It consists of a React frontend and a Python Flask backend that integrates with Smartsheet and Microsoft Teams.

## Features

- Real-time updates of equipment tickets.
- Dark mode support.
- Metrics display for various KPIs.
- Responsive design with a smooth user experience.

## Prerequisites

Ensure you have the following installed:

- Python 3.x
- Node.js
- npm (Node Package Manager)

## Installation

### Backend

1. Clone the repository:
   ```bash
   git clone https://github.com/xmmarcotte/LiveUpdate.git
   cd LiveUpdate/server
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   # On Windows
   .\venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your environment variables in a `.env` file. An example can be found in the repository.

### Frontend

1. Navigate to the client directory:
   ```bash
   cd ../client
   ```

2. Install the dependencies:
   ```bash
   npm install
   ```

## Usage

1. Start the backend server:
   ```bash
   cd server
   python app.py
   ```

2. In a new terminal window, navigate to the client directory and start the React app:
   ```bash
   cd client
   npm start
   ```

The React app should automatically open in your default web browser.


## License

This project is intended for Granite Telecommunications internal use.
