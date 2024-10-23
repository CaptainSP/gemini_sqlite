import os
import sqlite3
import time
import google.generativeai as genai
from dotenv import load_dotenv
import gradio as gr
import json

# Load environment variables from a .env file
load_dotenv()

# Fetch API key for GEMINI from environment variables
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Configure the GemAI API with the fetched API key
genai.configure(api_key=GEMINI_API_KEY)

# Connect to the SQLite database and create a cursor
con = sqlite3.connect("database.db", check_same_thread=False)
cur = con.cursor()

# Query to count the number of employees in the database. To test if it is working
cur.execute("SELECT COUNT(*) FROM employees")
print("Database contains", cur.fetchone()[0], "employees")

# Prompt template explaining the database schema
first_prompt = '''
You are provided with a database schema that contains multiple tables, each with specific columns and properties. Here are the details of the tables:

Table: departments
Columns:
dept_no: type char(4), primary key
dept_name: type varchar(40)

Table: dept_emp
Columns:
emp_no: type INTEGER, primary key
dept_no: type char(4), primary key, foreign key referencing departments(dept_no)
from_date: type date
to_date: type date

Table: dept_manager
Columns:
dept_no: type char(4), primary key, foreign key referencing departments(dept_no)
emp_no: type INTEGER, primary key, foreign key referencing employees(emp_no)
from_date: type date
to_date: type date

Table: employees
Columns:
emp_no: type INTEGER, primary key
birth_date: type date
first_name: type varchar(14)
last_name: type varchar(16)
gender: type TEXT
hire_date: type date

Table: salaries
Columns:
emp_no: type INTEGER, primary key, foreign key referencing employees(emp_no)
salary: type INTEGER
from_date: type date, primary key
to_date: type date

Table: titles
Columns:
emp_no: type INTEGER, primary key, foreign key referencing employees(emp_no)
title: type varchar(50)
from_date: type date, primary key
to_date: type date, nullable

Using the schema provided, you can perform operations such as querying data, inserting new records, updating existing records, and deleting records. Please ensure that all SQL operations comply with the relationships and constraints specified by the schema.
'''

# Instantiate the generative model with the given prompt and model name
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=first_prompt,
    generation_config= {
       "temperature": 1,
       "top_p": 0.99,
       "top_k": 0,
       "max_output_tokens": 4096,
    }
)

# Start a chat session with an empty history
chat = model.start_chat(
    history=[]
)

def ask(question):
    
    # Function to process the question, generate an SQL query,
    # fetch results from the database, and return a formatted message.
    

    tries = 4  # Number of attempts
    start_time = time.time()

    for attempt in range(tries):
        try:
            # Initial prompt to generate SQL query
            init_question = '''
            Make an sql query for the question: %s
            Give the result in below json format
            {
                "sqlQuery": "string",
                "description": "string"
            }
            ''' % question

            result = chat.send_message(init_question)
            resultText = result.text.split('```json')[1].split('```')[0]
            print(resultText)
            json1 = json.loads(resultText)
            query = json1["sqlQuery"]

            # Execute the generated SQL query
            cur.execute(query)
            data = cur.fetchall()
            dataText = json.dumps(data)

            # Second prompt to generate a user-friendly message
            init_question2 = '''
            The result of the query is: %s
            
            ----
            Now give user a pretty message with the below json format
            {
                "message": "string"
            }
            ''' % dataText
            print(init_question2)
            result2 = chat.send_message(init_question2)
            json2 = json.loads(result2.text.split('```json')[1].split('```')[0])
            end_time = time.time()
            print("Time taken:", end_time - start_time, "seconds")
            return json2["message"], data
        except Exception as e:
            if attempt < tries - 1:
                print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
            else:
                print(f"Attempt {attempt + 1} failed: {e}. No more retries.")
                return "Sorry, we couldn't fetch information."

# Create a Gradio interface to interact with the function
demo = gr.Interface(
    fn=ask,
    inputs=["text"],
    outputs=["text","dataframe"],
)

# Launch the Gradio interface
demo.launch()