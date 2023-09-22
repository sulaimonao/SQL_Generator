# SQL_Generator
This code uses the OpenAI API to generate SQL code from user database information, based on your request to group the data.

Requirements:
- Python 3.8+
- openai Python library
- python-dotenv library

Setup:
1. Install required libraries:
   pip install openai python-dotenv

2. Create a .env file in the root directory with the following content:
   OPENAI_API_KEY=<Your OpenAI API Key> ##example OPENAI_API_KEY=sk-

3. Run main.py:
   python main.py

Follow the on-screen instructions to provide details about your database, schemas, and columns. Then, provide a prompt for SQL generation, and the script will use GPT-4 to generate SQL code based on your inputs.

Generated SQL code will be saved in a .txt file named with the current date and time.

You have the option to continue generating SQL with the current data or provide new data or quit the program.
