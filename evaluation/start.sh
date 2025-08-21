#!/usr/bin/env bash

# Make sure pwd is the directory of the script
cd "$(dirname "$0")"

export REACT_APP_API_BASE_URL="https://dev.inty.sxwl.ai/api/v1"

if ! command -v npm &> /dev/null
then
    read -p "npm is not installed. Do you want to install nodejs and npm? (y/n)" choice
    case "$choice" in
      y|Y )
        echo "Installing nvm..."
        export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
        source ~/.bashrc
        nvm install --lts
        nvm use --lts;;
      n|N )
        echo "Nodejs and npm will not be installed."
        exit;;
      * )
        echo "Invalid option. Nodejs and npm will not be installed."
        exit;;
    esac
fi

echo "Installing Node Modules..."
npm i --no-audit --no-fund --loglevel=error --no-progress

# Check if :3000 is already in use
if lsof -i :3000; then
    echo "Try to kill the process using port 3000 ..."
    kill -9 $(lsof -t -i :3000)
fi

if lsof -i :3000; then
    echo "Port 3000 is already in use. Please stop the server and try again."
    echo "Only http://localhost:3000 is white listed on the server side, you must open this on :3000."
    echo "Ask Yaxiong Zhao for help if you need to open this on :3000."
    exit 1
fi

echo "Starting Inty-Eval Development Server..."
npm run start
