#!/bin/bash

host="0.0.0.0"
port=""

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    -h|--host)
      host="$2"
      shift 2
      ;;
    -p|--port)
      port="$2"
      shift 2
      ;;
    -https|--https)
      enable_https=${HTTPS_ENABLED}
      shift
      ;;
    -test|--test)
      test_mode="true"
      shift
      ;;
    *)
      echo "Invalid option: $1"
      echo "Usage: $0 [-h host] [-p port] [-https --https]"
      exit 1
      ;;
  esac
done

if [ "$test_mode" != true ]; then
  echo -e "\nStarting Uvicorn on $host:$port..."
  unset TEST_MODE
  if [ "$enable_https" = true ]; then
    echo -e "HTTPS is enabled.\n"
    exec uvicorn webhooks.main:app --reload --host "$host" --port "$port" --ssl-keyfile /app/certs/server.key --ssl-certfile /app/certs/server.crt
  else
    echo -e "HTTPS is disabled.\n"
    exec uvicorn webhooks.main:app --reload --host "$host" --port "$port"
  fi
else
  echo -e "Running Tests...\n"
  export TEST_MODE=true
  exec `which python || which python3` -m pytest ./test/test_main.py ./test/test_chargebee.py -W ignore::DeprecationWarning
fi
