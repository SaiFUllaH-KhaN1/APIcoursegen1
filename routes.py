from flask import Flask, render_template, request, Response, jsonify, session, send_from_directory, flash, redirect, url_for
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_community.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_community.llms import OpenAI
from langchain_community.chat_models import ChatOpenAI
import os
import openai
from openai import OpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv
import requests
import json
import langchaindemoBlock_22_april as LCD
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain.chains import ConversationChain
from flask_caching import Cache
import uuid
import shutil 
from bs4 import BeautifulSoup
import urllib.request
from werkzeug.datastructures import FileStorage
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from langchain_community.document_loaders import YoutubeLoader
from flask_basicauth import BasicAuth
import base64
import time
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask_cors import CORS

load_dotenv(dotenv_path="HUGGINGFACEHUB_API_TOKEN.env") # This is for render hosting service
# Set the API key for OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')
api_key = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=api_key)
client = OpenAI()

import io
import os


app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuration for the cache directory
cache_dir = 'cache'

# Check if the cache directory exists, and create it if it does not
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
    print(f"Cache directory '{cache_dir}' was created.")
else:
    print(f"Cache directory '{cache_dir}' already exists.")

app.config['BASIC_AUTH_REALM'] = 'realm'
app.config['BASIC_AUTH_USERNAME'] = os.getenv('BASIC_AUTH_USERNAME')
app.config['BASIC_AUTH_PASSWORD'] = os.getenv('BASIC_AUTH_PASSWORD')
basic_auth = BasicAuth(app)

app.config['CACHE_TYPE'] = 'FileSystemCache' 
app.config['CACHE_DIR'] = 'cache' # path to server cache folder
app.config['CACHE_THRESHOLD'] = 1000
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
cache = Cache(app)
allowed_origins = [
    "https://thinglink.local",
    "https://thinglink.local:3000",
    "https://sandbox.thinglink.com",
    "https://thinglink.com",
    "https://www.thinglink.com"
]

# Configure CORS for multiple routes with specific settings
cors = CORS(app, supports_credentials=True, resources={
    r"/process_data": {"origins": allowed_origins},
    r"/decide": {"origins": allowed_origins},
    r"/generate_course": {"origins": allowed_origins},
     r"/find_images": {"origins": allowed_origins}
})
### MANUAL DELETION OF all folders starting with faiss_index_ ###
def delete_indexes():
    """
    Deletes directories starting with 'faiss_index_' in the root directory of the app.
    """
    base_path = os.path.dirname(os.path.abspath(__file__))
    for item in os.listdir(base_path):
        dir_path = os.path.join(base_path, item)
        if os.path.isdir(dir_path) and item.startswith("faiss_index_"):
            print(f"Deleting Faiss directory: {dir_path}")
            shutil.rmtree(dir_path)
        elif os.path.isdir(dir_path) and item.startswith("imagefolder_"):
            print(f"Deleting image directory: {dir_path}")
            shutil.rmtree(dir_path)

@app.route("/cron", methods=['POST'])
@basic_auth.required
def cron():
    delete_indexes()
    print("Deleted FAISS index")
    return jsonify(message="FAISS and imagefolder index directories deleted")
###     ###     ### 

### SCHEDULED DELETION OF folders of imagefolder_ and faiss_index_ ###
def delete_old_directories():
    time_to_delete_files_older_than = timedelta(hours=6)
    print(f"Scheduler is running the delete_old_directories function to delete files older than {time_to_delete_files_older_than}.")
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    for item in os.listdir(base_path):
        dir_path = os.path.join(base_path, item)
        if os.path.isdir(dir_path) and item.startswith("faiss_index_") or item.startswith("imagefolder_"):
            # Check if directory is older than a specified time
            dir_age = datetime.fromtimestamp(os.path.getmtime(dir_path))
            if datetime.now() - dir_age > time_to_delete_files_older_than:
                print(f"Deleting directory: {dir_path}, it has modified date of {dir_age}")
                shutil.rmtree(dir_path)
###     ###     ###

@app.route("/process_data", methods=["GET", "POST"])
def process_data():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())  # Create a unique session user_id if not exists
        session_var = session['user_id']
        output_path = f"./imagefolder_{session_var}"
        if not os.path.exists(output_path):
            os.makedirs(output_path) 

    if request.method == 'POST':
        start_time = time.time() # Timer starts at the Post
        session_var = session['user_id']
        
        # getting requests from frontend
        model_type = request.args.get('model', 'openai') # to set default model
        model_name = request.args.get('modelName', 'gpt-3.5-turbo-0125') # to set default model name
        prompt = request.form.get("prompt")
        url_doc = request.form.get('url_doc')
        f = request.files.getlist('file')
        print("There is a file")


        if url_doc:
            if url_doc and ('www.youtube.com' in url_doc or 'youtu.be' in url_doc):
                loader = YoutubeLoader.from_youtube_url(
                url_doc, add_video_info=False)
                var_load = loader.load()
                raw_text = ''
                var = raw_text.join(document.page_content + '\n\n' for document in var_load)
                if var:
                    pdf_bytes = io.BytesIO()
                    c = canvas.Canvas(pdf_bytes, pagesize=A4)
                    text = c.beginText(40, 750)
                    text.setFont("Helvetica", 6)
                    lines = var.split('\n')
                    for line in lines:
                        text.textLine(line)
                    c.drawText(text)
                    c.showPage()
                    c.save()
                    pdf_bytes.seek(0)
                    # with open('extracted_content.pdf', 'wb') as pdf_file:
                    #     pdf_file.write(pdf_bytes.getvalue())
                    pdf_file_wrapper = FileStorage(stream=pdf_bytes, filename=f'extracted_content{session_var}.pdf', content_type='application/pdf') #still not unique for the same session so either url or youtube url processed at the same time
                    pdf_file_wrapper.seek(0)
                    f.append(pdf_file_wrapper)
                
            else:
                soup = BeautifulSoup(urllib.request.urlopen(url_doc).read())
                var = soup.get_text()
                print("Extracted text length:", len(var))  # Debug text length

                if var:
                    pdf_bytes = io.BytesIO()
                    c = canvas.Canvas(pdf_bytes, pagesize=A4)
                    text = c.beginText(40, 750)
                    text.setFont("Helvetica", 6)
                    lines = var.split('\n')
                    for line in lines:
                        text.textLine(line)
                    c.drawText(text)
                    c.showPage()
                    c.save()
                    pdf_bytes.seek(0)
                    # with open('extracted_content.pdf', 'wb') as pdf_file:
                    #     pdf_file.write(pdf_bytes.getvalue())
                    pdf_file_wrapper = FileStorage(stream=pdf_bytes, filename=f'extracted_content{session_var}.pdf', content_type='application/pdf')
                    pdf_file_wrapper.seek(0)
                    f.append(pdf_file_wrapper)

        filename = [f_name.filename for f_name in f]
        print("Filename is::",filename)

        base_docsearch = None
        for file in f:
            file_content = io.BytesIO(file.read())
            # file_content = [io.BytesIO(fs.read()) for fs in f]
            print("LCD initiated!")
            try:
                if model_type == 'gemini':
                    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
                else:
                    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
                print(f"Using embeddings of {embeddings}")
                docsearch = LCD.RAG(file_content,embeddings,file,session_var)
            except Exception as e:
                docsearch = None
                print("Error processing file:", str(e))
                return jsonify(error=f"Error processing file:{str(e)}")
            if base_docsearch is None:
                base_docsearch = docsearch  # For the first file
            else:
                base_docsearch.merge_from(docsearch)  # Merge subsequent indexes

        if base_docsearch:
            base_docsearch.save_local(f"faiss_index_{session['user_id']}") 
            
            cache.set(f"user_id_cache_{session['user_id']}", session['user_id'],timeout=0)
            cache.set(f"prompt_{session['user_id']}", prompt,timeout=0)
            end_time = time.time()
            execution_time = end_time - start_time
            minutes, seconds = divmod(execution_time, 60)
            formatted_time = f"{int(minutes):02}:{int(seconds):02}"
            execution_time_block = {"executionTime":f"{formatted_time}"}
            messageJson = '{"message": "Data processed!"}'
            response_with_time = json.loads(messageJson)
            response_with_time.update(execution_time_block)
            return Response(json.dumps(response_with_time), mimetype='application/json')

    else:
        f = None
        filename = None

    # Return the processed text in JSON format
    # return jsonify({"response": response['text']})
    return jsonify(error="Unexpected Fault or Interruption")

@app.route("/decide", methods=["GET", "POST"])
def decide():
    if request.method == 'POST':
        scenario = request.form.get('scenario')
        print("Scenario type:",scenario)
        model_type = request.args.get('model', 'openai') # to set default model
        model_name = request.args.get('modelName', 'gpt-3.5-turbo-0125') # to set default model name
        start_time = time.time() # Timer starts at the Post

        if scenario:
            user_id_cache = cache.get(f"user_id_cache_{session['user_id']}")
            print(user_id_cache)

            prompt = cache.get(f"prompt_{user_id_cache}")
            print("Prompt loaded!:",prompt)

            try:
                if model_type == "gemini":
                    llm = ChatGoogleGenerativeAI(model=model_name,temperature=0)
                    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
                else:
                    llm = ChatOpenAI(model=model_name, temperature=0, streaming=True, verbose= True)
                    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

                print(f"LLM is :: {llm}\n embedding is :: {embeddings}\n")

                load_docsearch = FAISS.load_local(f"faiss_index_{user_id_cache}",embeddings,allow_dangerous_deserialization=True)
                
                chain, docs_main, query = LCD.PRODUCE_LEARNING_OBJ_COURSE(prompt, load_docsearch, llm, model_type)
                print("1st Docs_main of /Decide route:",docs_main)
                response_LO_CA = chain({"input_documents": docs_main,"human_input": query})

                cache.set(f"scenario_{user_id_cache}", scenario,timeout=0)
                end_time = time.time()
                execution_time = end_time - start_time
                minutes, seconds = divmod(execution_time, 60)
                formatted_time = f"{int(minutes):02}:{int(seconds):02}"
                execution_time_block = {"executionTime":f"{formatted_time}"}
                response_with_time = json.loads(response_LO_CA['text']) 
                response_with_time.update(execution_time_block)
                return Response(json.dumps(response_with_time), mimetype='application/json')
                # return jsonify(response_LO_CA['text'])
            except Exception as e:
                print(f"An error occurred: {e}")
                return jsonify(error=f"An error occurred: {str(e)}")

        else:
            print("None")
            
        return jsonify(error="Unexpected Fault or Interruption")
    
@app.route("/generate_course", methods=["GET", "POST"])
def generate_course():
    if request.method == 'POST':
        learning_obj = request.form.get("learning_obj")
        content_areas = request.form.get("content_areas")
        model_type = request.args.get('model', 'openai') # to set default model
        model_name = request.args.get('modelName', 'gpt-3.5-turbo-0125') # to set default model name
        summarize_images = request.args.get('summarizeImages', 'on') # to set default value name
        start_route_time = time.time() # Timer starts at the Post

        if learning_obj and content_areas:
            user_id_cache = cache.get(f"user_id_cache_{session['user_id']}")

            prompt = cache.get(f"prompt_{user_id_cache}")
            print("Prompt loaded!:",prompt)

            scenario = cache.get(f"scenario_{user_id_cache}")
            print("scenario loaded!:",scenario)

            try:
                if model_type == 'gemini':
                    llm = ChatGoogleGenerativeAI(model=model_name,temperature=0.1, max_output_tokens=8000)
                    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
                else:
                    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
                    llm = ChatOpenAI(model=model_name, temperature=0.1, streaming=True, verbose= True)

                load_docsearch = FAISS.load_local(f"faiss_index_{user_id_cache}",embeddings,allow_dangerous_deserialization=True)
                combined_prompt = f"{prompt}\n{learning_obj}\n{content_areas}"
                output_path = f"./imagefolder_{user_id_cache}"

                start_RE_SIMILARITY_SEARCH_time = time.time()
                docs_main = LCD.RE_SIMILARITY_SEARCH(combined_prompt, load_docsearch, output_path, model_type, summarize_images)
                end_RE_SIMILARITY_SEARCH_time = time.time()
                execution_RE_SIMILARITY_SEARCH_time = end_RE_SIMILARITY_SEARCH_time - start_RE_SIMILARITY_SEARCH_time
                minutes, seconds = divmod(execution_RE_SIMILARITY_SEARCH_time, 60)
                formatted_RE_SIMILARITY_SEARCH_time = f"{int(minutes):02}:{int(seconds):02} with summarize_images switched = {summarize_images} " # for docs retreival and image summarizer

                print("2nd Docs_main:",docs_main)
                print("combined_prompt",combined_prompt)
            # doc_main has all the unfiltered meta image summaries appended with and not in vectorstore, however...
            # ... it has been list of images are chosen to be atleast reletive to the topic at hand
                
                start_TALK_WITH_RAG_time = time.time()
                response = LCD.TALK_WITH_RAG(scenario, content_areas, learning_obj, prompt, docs_main, llm, model_type, model_name)
                end_TALK_WITH_RAG_time = time.time()
                execution_TALK_WITH_RAG_time = end_TALK_WITH_RAG_time - start_TALK_WITH_RAG_time
                minutes, seconds = divmod(execution_TALK_WITH_RAG_time, 60)
                formatted_TALK_WITH_RAG_time = f"{int(minutes):02}:{int(seconds):02}" # for docs JSON scenario response


                cache.set(f"docs_main_{user_id_cache}", docs_main, timeout=0)
                cache.set(f"response_text_{user_id_cache}", response, timeout=0)

                end_route_time = time.time()
                execution_route_time = end_route_time - start_route_time
                minutes, seconds = divmod(execution_route_time, 60)
                formatted_route_time = f"{int(minutes):02}:{int(seconds):02}"

                execution_time_block = {"executionTime":f"""For whole Route is {formatted_route_time};\nFor document retreival &/or image summarizer is {formatted_RE_SIMILARITY_SEARCH_time};\nFor JSON scenario response is {formatted_TALK_WITH_RAG_time};"""}
                response_with_time = json.loads(response) 
                response_with_time.update(execution_time_block)

                return Response(json.dumps(response_with_time), mimetype='application/json')
                # return jsonify(message=f"""{response}""")
            except Exception as e:
                print(f"An error occurred: {e}")
                return jsonify(error=f"An error occurred: {str(e)}")

        else:
            print("None")
        
        return jsonify(error="Unexpected Fault or Interruption")
    
@app.route("/find_images", methods=["GET", "POST"])
def find_images():
    if request.method == 'POST':
        model_type = request.args.get('model', 'openai') # default select openai
        model_name = request.args.get('modelName', 'gpt-3.5-turbo-0125') # to set default model name
        
        user_id_cache = cache.get(f"user_id_cache_{session['user_id']}")
        response_text = cache.get(f"response_text_{user_id_cache}")
        docs_main = cache.get(f"docs_main_{user_id_cache}")
        output_path = f"./imagefolder_{user_id_cache}"
        if response_text and docs_main:
            try:
                if model_type == 'gemini':
                    llm = ChatGoogleGenerativeAI(model=model_name,temperature=0)
                else:
                    llm = ChatOpenAI(model=model_name, temperature=0, streaming=True, verbose= True)

                img_response = LCD.ANSWER_IMG(response_text, llm,docs_main)

                json_img_response = json.loads(img_response)
                print("json_img_response is::",json_img_response)

                def encode_image(image_path):
                    with open(image_path, "rb") as f:
                        return base64.b64encode(f.read()).decode('utf-8')
                    
                
                image_elements = []
                for key, value in json_img_response.items():
                    if 'Image' in key:  # This ensures we're only dealing with image keys
                        normalized_value = value.lower()  # Normalize as filenames may vary
                        matched = False
                        for imgfolder in os.listdir(output_path):
                            print("Image folder is ::",imgfolder)
                            imgfolder = os.path.join(output_path, imgfolder)
                            for image_file in os.listdir(imgfolder):
                                print("Image file is::",image_file)
                                if image_file.endswith(('.png', '.jpg', '.jpeg')):
                                    if normalized_value in image_file.lower():  # Case insensitive comparison
                                        image_path = os.path.join(imgfolder, image_file)
                                        encoded_image = encode_image(image_path)  # Assuming you have a function `encode_image`
                                        image_elements.append(encoded_image)
                                        matched = True
                                        break  # Stop searching once a match is found for this key
                            if not matched:
                                print(f"No match found for {value}")
                
                count_var = 0
                for r in image_elements:
                    count_var += 1
                    json_img_response[f"base64_Image{count_var}"] = r
                    print(json_img_response)

                return Response(json_img_response, mimetype='application/json')
                # return jsonify(message=f"""{str(json_img_response)}""")
            except Exception as e:
                print(f"An error occurred: {e}")
                return jsonify(error=f"An error occurred: {str(e)}")


            # shutil.rmtree(f"faiss_index_{user_id_cache}")

            # shutil.rmtree(output_path) #images store folder
            # cache.delete(f"response_text_{user_id_cache}")
            # cache.delete(f"prompt_{user_id_cache}")
            # cache.delete(f"scenario_{user_id_cache}")
            # cache.delete("user_id_cache")

        else:
            print("None")
        
        return jsonify(error="Unexpected Fault or Interruption")

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(delete_old_directories, 'interval', hours=6)
    scheduler.start()

    try:
        app.run(use_reloader=False)  # use_reloader=False to avoid duplicate jobs
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
