# LiveUpdate Client

The **LiveUpdate Client** is a React application that displays live equipment ticket updates. It features a dark mode toggle, real-time logging, and metrics display, providing users with a user-friendly interface to monitor equipment tickets and metrics.

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Scripts](#scripts)
- [Environment Variables](#environment-variables)
- [Dependencies](#dependencies)
- [Contributing](#contributing)
- [License](#license)

## Features
- Real-time updates of equipment tickets.
- Dark mode for improved accessibility.
- Toggleable metrics display.
- Responsive design.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/xmmarcotte/LiveUpdate.git
   cd LiveUpdate/client
   ```

2. Install the dependencies:

   ```bash
   npm install
   ```

3. Set up environment variables by creating a `.env` file in the root of the `client` folder. Use the provided sample below:

   ```env
   HTTPS=true
   PORT=443
   SSL_CRT_FILE=C:/nginx/ssl/localhost.pem
   SSL_KEY_FILE=C:/nginx/ssl/localhost-key.pem
   HOST=0.0.0.0
   ```

## Usage

1. Start the development server:

   ```bash
   npm start
   ```

   The app will be running at `https://localhost:443`.

2. Open your browser and navigate to `https://localhost:443`.

## Scripts

This project comes with the following scripts:

- **start**: Starts the development server.
- **build**: Builds the app for production.
- **test**: Runs the test suite.
- **eject**: Ejects the configuration from Create React App (use with caution).

## Environment Variables

The following environment variables are used in the project:

- `HTTPS`: Set to `true` to enable HTTPS.
- `PORT`: The port on which the server will run.
- `SSL_CRT_FILE`: Path to the SSL certificate file.
- `SSL_KEY_FILE`: Path to the SSL key file.
- `HOST`: The host address (usually `0.0.0.0`).

## Dependencies

The project uses the following dependencies:

- `react`: JavaScript library for building user interfaces.
- `react-dom`: Serves as the entry point to the DOM and server renderers for React.
- `axios`: Promise-based HTTP client for the browser and Node.js.
- `socket.io-client`: Enables real-time communication between client and server.
- `@testing-library/react`: A lightweight solution for testing React components.
- `react-scripts`: Scripts and configuration used by Create React App.

## License

This project is intended for Granite Telecommunications internal use.
