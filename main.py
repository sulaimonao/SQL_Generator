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
    while True:
        db_cache = load_db_cache()
        if db_cache:
            print("Saved databases:")
            for idx, db in enumerate(db_cache, 1):
                print(f"{idx}. {db['db_name']}")
                for schema, columns in db['schemas'].items():
                    print(f"    Schema: {schema}")
                    for column, column_type in columns.items():
                        print(f"        Column: {column} ({column_type})")

            selection = input("Enter the number of a saved database, 'new' to input a new one, 'edit' to edit an existing one, or 'quit' to exit: ").strip().lower()

            if selection == 'edit':
                db_num = int(input("Enter the number of the database you want to edit: ").strip())
                db_to_edit = db_cache[db_num - 1]
                schema_to_edit = input("Enter the schema name you want to edit or 'back' to go back: ").strip()
                if schema_to_edit in db_to_edit['schemas']:
                    column_to_edit = input("Enter the column name you want to edit or 'back' to go back: ").strip()
                    if column_to_edit in db_to_edit['schemas'][schema_to_edit]:
                        new_column_name = input("Enter the new column name: ").strip()
                        new_column_type = input("Enter the new column type: ").strip()
                        db_to_edit['schemas'][schema_to_edit][new_column_name] = new_column_type
                        # delete old column name
                        del db_to_edit['schemas'][schema_to_edit][column_to_edit]
                        save_db_cache(db_cache)
                continue

            elif selection.isdigit() and 0 < int(selection) <= len(db_cache):
                index = int(selection) - 1
                return db_cache[index]['db_name'], db_cache[index]['schemas']
            elif selection == 'quit':
                return None, None
            elif selection == 'new':
                continue
            else:
                print("Invalid choice. Please enter a valid number, 'new', 'edit', or 'quit'.")
                continue

        # This code block is for entering new database information
        while True:  # Added loop to allow re-entering information
            db_name = input("Enter the name of the database: ")

            try:
                num_schemas = int(input("Enter how many schemas are in the database (or type 'quit' to exit): "))
            except ValueError:
                print("Please enter a valid number.")
                continue  # Continue looping until valid input is entered

            schemas = {}
            for _ in range(num_schemas):
                schema_name = input("Enter the schema name (or type 'quit' to exit): ")
                if schema_name.lower() == 'quit':
                    return None, None

                while True:
                    try:
                        num_columns = int(input(f"How many columns are in the {schema_name} schema? (or type 'quit' to exit): "))
                        break
                    except ValueError:
                        print("Please enter a valid number.")

                columns = {}
                for _ in range(num_columns):
                    while True:  # Added loop to ensure valid column type is entered
                        column_name = input("Enter column name (or type 'quit' to exit): ")
                        if column_name.lower() == 'quit':
                            return None, None

                        column_type = input("Are this column's values strings, floats, dates, or integers? (or type 'quit' to exit): ")
                        if column_type.lower() not in ['strings', 'floats', 'integers', 'dates']:
                            print("Invalid type.")
                            continue
                        columns[column_name] = column_type
                        break
                schemas[schema_name] = columns

            save_db = input("Would you like to save this database information for frequent use? (yes/no): ").strip().lower()
            if save_db == "yes":
                save_db_cache({"db_name": db_name, "schemas": schemas})

            return db_name, schemas

def generate_sql(db_data, prompt):
    while True:
        if prompt in pycache:
            cached_sql = pycache[prompt]
            use_cached = input(f"Use cached SQL? (yes/no): {cached_sql}\n").strip().lower()
            if use_cached == 'yes':
                return cached_sql
            elif use_cached == 'no':
                del pycache[prompt]
                modify_prompt = input("Would you like to modify the prompt? (yes/no): ").strip().lower()
                if modify_prompt == 'yes':
                    prompt = input("Please enter the new prompt: ")
                    continue

        db_name, schemas = db_data
        schema_details = [f"{schema}: {', '.join([f'{col} ({type_})' for col, type_ in columns.items()])}" for schema, columns in schemas.items()]
        schema_string = '\n'.join(schema_details)

        try:
            input_messages = [{
                "role": "system",
                "content": "You are a helpful assistant that understands SQL syntax and semantics perfectly."
            }, {
                "role": "user",
                "content": f"I have a database named {db_name} with the following schemas and columns, and their exact data types:\n{schema_string}\nGenerate an exact SQL query to {prompt}. Ensure the syntax and semantics are correct."
            }]
            response = openai.ChatCompletion.create(model="gpt-4", messages=input_messages)
            match = re.search(r'```sql\n(.*?)\n```', response.choices[0].message['content'], re.DOTALL)
            if not match:
                raise Exception("SQL extraction failed. The response did not contain the expected SQL format.")
            sql = match.group(1).strip()
            is_correct = input(f"Is this SQL correct? (yes/no): {sql}\n").strip().lower()
            if is_correct == 'yes':
                save_to_pycache(prompt, sql)
            elif is_correct == 'no':
                del pycache[prompt]
                modify_prompt = input("Would you like to modify the prompt? (yes/no): ").strip().lower()
                if modify_prompt == 'yes':
                    prompt = input("Please enter the new prompt: ")
                    continue
            return sql
            
        except openai.error.OpenAIError as e:
            print(f"OpenAI library error: {str(e)}")
        except Exception as e:
            print(f"General error generating SQL: {str(e)}")
    
def main():
    while True:
        db_data = get_input_data()
        if db_data is None or db_data[0] is None:
            print("Exiting program...")
            break

        while True:
            prompt_text = input("Input your prompt for SQL on how you would like to group your data (or type 'quit' to exit): ")
            if prompt_text.lower() == 'quit':
                break

            sql_code = generate_sql(db_data, prompt_text)
            
            # Check if SQL generation was successful
            if "error" in sql_code.lower():
                print(f"An error occurred: {sql_code}")
                print("Please provide more information or try a different query.")
                continue  # Skip the rest and go back to asking for a new prompt

            print("Generated SQL Query:")
            print(sql_code)
            satisfaction = input("Does this SQL query meet your requirements? (yes/no/quit): ").strip().lower()
            
            if satisfaction == 'yes':
                timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                with open(f"sql_output_{timestamp}.sql", 'w') as f:
                    f.write(sql_code)
                print(f"Generated SQL code has been written to sql_output_{timestamp}.sql.")
            elif satisfaction == 'quit':
                return
            elif satisfaction == 'no':
                print("Let's refine the query. Please provide more information.")
                # Here you can add more code to handle query refinement

            cont = input("Would you like to continue with the current input data? (yes/no/quit): ").strip().lower()
            if cont == 'quit':
                return
            elif cont == 'no':
                break

if __name__ == "__main__":
    pycache = load_pycache()
    main()
