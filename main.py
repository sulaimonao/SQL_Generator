import os
import json
from datetime import datetime
from dotenv import load_dotenv
import openai

# Load API key from .env file
load_dotenv()
API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI client
openai.api_key = API_KEY

# Cache and memory
cache = {}
memory_file = "memory.json"

def get_input_data():
    db_name = input("Enter the name of the database (or type 'quit' to exit): ")
    if db_name.lower() == 'quit':
        return None
    
    num_schemas = input("Enter how many schemas are in the database (or type 'quit' to exit): ")
    if num_schemas.lower() == 'quit':
        return None
    num_schemas = int(num_schemas)

    schemas = {}
    for _ in range(num_schemas):
        schema_name = input("Enter the schema name (or type 'quit' to exit): ")
        if schema_name.lower() == 'quit':
            return None
        
        num_columns = input(f"How many columns are in the {schema_name} schema? (or type 'quit' to exit): ")
        if num_columns.lower() == 'quit':
            return None
        num_columns = int(num_columns)

        columns = {}
        for _ in range(num_columns):
            column_name = input("Enter column name (or type 'quit' to exit): ")
            if column_name.lower() == 'quit':
                return None

            column_type = input("Is this column values are strings, floats, or integers? (or type 'quit' to exit): ")
            if column_type.lower() == 'quit':
                return None

            columns[column_name] = column_type
        schemas[schema_name] = columns

    return db_name, schemas

def load_or_get_data():
    if os.path.exists(memory_file):
        with open(memory_file, 'r') as f:
            return json.load(f)
    else:
        data = get_input_data()
        if data is None:
            return None
        with open(memory_file, 'w') as f:
            json.dump(data, f)
        return data

def generate_sql(db_data, prompt):
    db_name, schemas = db_data

    if prompt in cache:
        return cache[prompt]

    schema_details = []
    for schema, columns in schemas.items():
        column_details = ', '.join([f"{col} ({type_})" for col, type_ in columns.items()])
        schema_details.append(f"{schema}: {column_details}")

    schema_string = '\n'.join(schema_details)

    input_messages = [{
        "role": "system",
        "content": "You are a helpful assistant."
    }, {
        "role": "user",
        "content": f"I have a database named {db_name} with the following schemas and columns:\n"
                   f"{schema_string}\n"
                   f"How can I generate an SQL query to {prompt}?"
    }]

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=input_messages
    )

    sql = response.choices[0].message['content'].strip()
    cache[prompt] = sql
    return sql

def main():
    db_data = load_or_get_data()
    if db_data is None:
        print("Exiting program...")
        return

    while True:
        prompt_text = input("Input your prompt for SQL on how you would like to group your data: ")
        sql_code = generate_sql(db_data, prompt_text)

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        with open(f"sql_output_{timestamp}.txt", 'w') as f:
            f.write(sql_code)

        print(f"Generated SQL code has been written to sql_output_{timestamp}.txt.")

        cont = input("Would you like to continue with the current input data? (yes/no/quit): ").strip().lower()
        if cont == 'quit':
            break
        elif cont == 'no':
            if os.path.exists(memory_file):
                os.remove(memory_file)  # Remove memory file to start fresh
            db_data = load_or_get_data()
            if db_data is None:
                print("Exiting program...")
                return

if __name__ == "__main__":
    main()
