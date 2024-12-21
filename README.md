DocuBot
DocuBot: Get Smart Answers from Your Documents

DocuBot is a web-based application designed to provide intelligent document processing and retrieval capabilities. Leveraging the power of Natural Language Processing (NLP) and advanced AI technologies, DocuBot allows users to upload PDF documents, query their content through a chatbot interface, and receive accurate and context-aware responses.

Features
User-Friendly Interface:

Simple and intuitive platform for uploading and managing documents.
Responsive design using HTML, CSS, and Bootstrap for seamless accessibility.
Document Processing:

Automated text extraction from PDFs using PyPDF2.
Text embedding and storage in Chroma for efficient retrieval.
Smart Querying:

Interactive chatbot built with LangChain for contextual question answering.
Multi-session chat history management.
User Authentication:

Secure user authentication with Flask-Login and Google OAuth.
Password management with Flask-Bcrypt and Flask-Mail for password reset functionality.
Database Integration:

MongoDB Atlas for user data, document metadata, and chat history storage.
Chroma-Vector database for efficient text retrieval.
Deployment:

Hosted on AWS EC2 for scalable and reliable access.
Technology Stack
Backend: Flask, Flask-Login, Flask-WTF, Flask-Mail, Flask-Bcrypt
Frontend: HTML, CSS, Bootstrap, JavaScript
Database: MongoDB Atlas, Chroma (Vector Store)
Document Processing: PyPDF2, LangChain, OpenAI API
Hosting: AWS EC2 (Ubuntu)
