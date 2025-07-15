# How to Update Your Local Database Schema

This guide explains how to update your PostgreSQL database to add the timezone column to the user table. This is required for the new timezone functionality in the technician scheduler application.

## Option 1: Using the SQL Script (Recommended)

1. Make sure you have `psql` (PostgreSQL client) installed on your system.

2. Set your database connection information in the `.env` file or export it as an environment variable:
   ```bash
   export DATABASE_URL="postgresql://username:password@hostname:port/database_name"
   ```

3. Run the SQL update script:
   ```bash
   psql $DATABASE_URL -f update_timezone_field.sql
   ```

Alternatively, you can use the shell script which handles more configuration details:
```bash
chmod +x update_timezone_field.sh
./update_timezone_field.sh
```

## Option 2: Using the Python Script

1. Make sure your virtual environment is activated (if you're using one).

2. Set your database connection information in the `.env` file or export it as an environment variable:
   ```bash
   export DATABASE_URL="postgresql://username:password@hostname:port/database_name"
   ```

3. Run the Python update script:
   ```bash
   python update_timezone_field.py
   ```

## Option 3: Using Docker (If Running in Docker)

If your application is running in Docker using the provided docker-compose configuration:

1. Navigate to your project directory where docker-compose.yml is located.

2. Execute the SQL script through the PostgreSQL container:
   ```bash
   docker-compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -f /tmp/update_timezone_field.sql
   ```

   You might need to copy the SQL file to the container first:
   ```bash
   docker cp update_timezone_field.sql <container_name>:/tmp/
   ```

## Verification

After running any of these update methods, you can verify the schema change by:

1. Connecting to your database:
   ```bash
   psql $DATABASE_URL
   ```

2. Checking the user table columns:
   ```sql
   \d "user"
   ```

3. You should see `timezone` listed as one of the columns with a default value of 'America/Los_Angeles'.

## Troubleshooting

- If you get a permission error, make sure your database user has permission to alter the table.
- If the database connection fails, double-check your DATABASE_URL or individual PostgreSQL environment variables.
- If the script runs but no changes happen, the column might already exist, which is fine.

For further assistance, refer to the PostgreSQL documentation or contact your system administrator.