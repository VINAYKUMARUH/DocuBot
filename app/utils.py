import os
import json
import logging
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.models import Document

# Load environment variables from .env file
load_dotenv()

# Set the OpenAI API key from the environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Extract text from PDF function
def extract_text_from_pdf(pdf_path):
    raw_text = ''
    pdf_reader = PdfReader(pdf_path)
    for page in pdf_reader.pages:
        content = page.extract_text()
        if content:
            raw_text += content
    return raw_text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Chroma function
def initialize_chroma(folder_path, new_files):
    embedding_function = OpenAIEmbeddings(model="text-embedding-ada-002")
    db = Chroma(persist_directory='./Testing', embedding_function=embedding_function)
    
    if new_files:
        all_text = ""
        for pdf_file in new_files:
            text = extract_text_from_pdf(pdf_file)
            all_text += text
        text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=500,
            chunk_overlap=50,
            length_function=len)
        texts = text_splitter.split_text(all_text)
        
        # Embedding function
        embedding_function = OpenAIEmbeddings(model="text-embedding-ada-002")
        
        # Load text chunks into Chroma
        db = Chroma.from_texts(texts, embedding_function, persist_directory='./Testing')

    retriever = db.as_retriever(
        search_type="similarity", 
        search_kwargs={"k": 10}
    )
    
    return retriever


# Check for new PDF files and saves if do not exist
def check_for_new_files(folder_path, uploaded_file, user_email):
    file_path = os.path.join(folder_path, uploaded_file.filename)

    # Check if the document already exists
    if not Document.document_exists(uploaded_file.filename):
        uploaded_file.save(file_path)
        new_doc = Document(filename=uploaded_file.filename, owner_email=user_email)
        new_doc.save()
        return [file_path]
    
    return []


# Initialize retrievers
def initialize_retrievers():
    logger.info("Initializing retrievers")
    retriever = initialize_chroma('./uploads', [])
    llm = ChatOpenAI(temperature=0, model='gpt-3.5-turbo', openai_api_key=OPENAI_API_KEY)
    compressor = LLMChainExtractor.from_llm(llm)
    compression_retriever = ContextualCompressionRetriever(base_compressor=compressor, base_retriever=retriever)
    

    # initialize Contextualize question prompt
    # This system prompt helps the AI understand that it should reformulate the question
    # based on the chat history to make it a standalone question
    contextualize_question_system_prompt = (
        "Given a chat history and the latest user question "
        "which might reference context in the chat history, "
        "formulate a standalone question which can be understood "
        "without the chat history. Do NOT answer the question, just "
        "reformulate it as needed and otherwise return it as is."
    )
    
    # Create a prompt template for contextualizing questions
    contextualize_question_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_question_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    
    # Create a history-aware retriever
    # This reformulates user questions based on chat history before retieving relevant documents
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_question_prompt
    )
    
    # Answer question prompt
    # This system prompt helps the AI understand that it should provide concise answers
    # based on the retrieved context and say don't know if the answer is unknown
    qa_system_prompt = (
        "You are an assistant for question-answering tasks. Use "
        "the following pieces of retrieved context to answer the "
        "question. If you don't know the answer, just say that you "
        "don't know. Use three sentences maximum and keep the answer "
        "concise."
        "\n\n"
        "{context}"
    )
    
    # Create a prompt template for answering questions by combining 
    # system prompt, retrieved context and user quesiton
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", qa_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
     
    # Create a chain to combine documents for question answering
    # `create_stuff_documents_chain` feeds all retrieved context into the 
    # LLM using qa_prompt and AI uses this chain to answer questions
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

    # Create a retrieval chain that combines the history-aware retriever and the question answering chain
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    
    return rag_chain, retriever