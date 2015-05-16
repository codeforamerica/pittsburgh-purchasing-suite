echo "Writing .dockerenv file..."

# Database
echo "# DATABASE" > .dockerenv
echo "DB_NAME=postgres" >> .dockerenv
echo "DB_USER=postgres" >> .dockerenv
echo "DB_PASS=postgres" >> .dockerenv
echo "DB_HOST=db" >> .dockerenv
echo "DB_PORT=5432" >> .dockerenv

# Browserid
echo "\n" >> .dockerenv
echo "# Port and Persona config" >> .dockerenv
export PORT=9000
echo "PORT="$PORT >> .dockerenv
echo "BROWSERID_URL="$(boot2docker ip):$PORT >>.dockerenv

echo "Done! Run the server with docker-compose up and visit http://"$(boot2docker ip):$PORT" in your browser."
unset PORT
