import os
import json
from datetime import datetime
from dotenv import load_dotenv
import openai
import re

# Load API key from .env file
load_dotenv()
API_KEY = os.getenv('OPENAI_API_KEY')

if not API_KEY:
    raise ValueError("OPENAI_API_KEY is missing. Make sure it's set in the .env file.")

# Initialize OpenAI client
openai.api_key = API_KEY

# Memory and caching
pycache_file = "pycache.json"
db_cache_file = "db_cache.json"
pycache = {}

def load_json_file(file_name):
    try:
        with open(file_name, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_json_file(file_name, data):
    with open(file_name, 'w') as f:
        json.dump(data, f)

def load_pycache():
    return load_json_file(pycache_file)

def save_to_pycache(key, value):
    pycache[key] = value
    save_json_file(pycache_file, pycache)

def load_db_cache():
    return load_json_file(db_cache_file)

def save_db_cache(db_data):
    db_cache = load_db_cache()
    db_cache.append(db_data)
    save_json_file(db_cache_file, db_cache)

def get_input_data():
    db_cache = load_db_cache()
    if db_cache:
        print("Saved databases:")
        for idx, db in enumerate(db_cache, 1):
            print(f"{idx}. {db['db_name']}")

        selection = input("Enter the number of a saved database, 'new' to input a new one, or 'quit' to exit: ").strip().lower()

        if selection.isdigit() and 0 < int(selection) <= len(db_cache):
            index = int(selection) - 1
            return db_cache[index]['db_name'], db_cache[index]['schemas']
        elif selection == 'quit':
            return None, None
        elif selection != 'new':
            print("Invalid choice. Please enter a valid number, 'new', or 'quit'.")

    db_name = input("Enter the name of the database: ")

    try:
        num_schemas = int(input("Enter how many schemas are in the database (or type 'quit' to exit): "))
    except ValueError:
        print("Please enter a valid number.")
        return None, None

    schemas = {}
    for _ in range(num_schemas):
        schema_name = input("Enter the schema name (or type 'quit' to exit): ")
        if schema_name.lower() == 'quit':
            return None, None

        try:
            num_columns = int(input(f"How many columns are in the {schema_name} schema? (or type 'quit' to exit): "))
        except ValueError:
            print("Please enter a valid number.")
            return None, None

        columns = {}
        for _ in range(num_columns):
            column_name = input("Enter column name (or type 'quit' to exit): ")
            if column_name.lower() == 'quit':
                return None, None

            column_type = input("Is this column values are strings, floats, or integers? (or type 'quit' to exit): ")
            if column_type.lower() not in ['strings', 'floats', 'integers']:
                print("Invalid type.")
                return None, None
            columns[column_name] = column_type
        schemas[schema_name] = columns

    save_db = input("Would you like to save this database information for frequent use? (yes/no): ").strip().lower()
    if save_db == "yes":
        save_db_cache({"db_name": db_name, "schemas": schemas})

    return db_name, schemas

def generate_sql(db_data, prompt):
    if prompt in pycache:
        return pycache[prompt]

    db_name, schemas = db_data
    schema_details = [f"{schema}: {', '.join([f'{col} ({type_})' for col, type_ in columns.items()])}" for schema, columns in schemas.items()]
    schema_string = '\n'.join(schema_details)

    input_messages = [{
        "role": "system",
        "content": "You are a helpful assistant that understands SQL syntax and semantics perfectly."
    }, {
        "role": "user",
        "content": f"I have a database named {db_name} with the following schemas and columns, and their exact data types:\n{schema_string}\nGenerate an exact SQL query to {prompt}. Ensure the syntax and semantics are correct."
    }]

    try:
        response = openai.ChatCompletion.create(model="gpt-4", messages=input_messages)

        match = re.search(r'```sql\n(.*?)\n```', response.choices[0].message['content'], re.DOTALL)
        sql = match.group(1).strip() if match else "Failed to extract SQL."

        save_to_pycache(prompt, sql)
        return sql

    except Exception as e:
        return f"Error generating SQL: {str(e)}"

def main():
    while True:
        db_data = get_input_data()
        if db_data[0] is None:
            print("Exiting program...")
            break

        while True:
            prompt_text = input("Input your prompt for SQL on how you would like to group your data (or type 'quit' to exit): ")
            if prompt_text.lower() == 'quit':
                break

            sql_code = generate_sql(db_data, prompt_text)
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            with open(f"sql_output_{timestamp}.sql", 'w') as f:
                f.write(sql_code)
            print(f"Generated SQL code has been written to sql_output_{timestamp}.sql.")
            cont = input("Would you like to continue with the current input data? (yes/no/quit): ").strip().lower()
            if cont == 'quit':
                return
            elif cont == 'no':
                break

if __name__ == "__main__":
    pycache = load_pycache()
    main()
