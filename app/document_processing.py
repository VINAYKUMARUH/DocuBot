import os
from app.utils import initialize_chroma

def process_uploaded_files(upload_folder):
    db, retriever = initialize_chroma(upload_folder)
    return db, retriever