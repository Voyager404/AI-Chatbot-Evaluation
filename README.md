# AI-Chatbot-Evaluation

This code explores the implementation of a chatbot in a medium-sized car dealership. A technical proof of concept is conducted to validate the developed application examples using a previously selected model.

The implementation is divided into three files:
create_embeddings_for_documents.py – This file populates the database with vector embeddings using Retrieval-Augmented Generation (RAG). The stored information serves as the knowledge base for the chatbot.
get_relevant_data.py – This script prompts the user to enter a query. The input is then compared with the stored information in the database to retrieve relevant context.
run_llama.py – This file, executes get_relevant_data.py in a subprocess and generates the chatbot's response using the contextual information retrieved in the second step.

To run this code, it is necessary to first populate the database by executing create_embeddings_for_documents.py (File 1). Once the database is set up, run_llama.py (File 3) should be started, which will automatically call get_relevant_data.py (File 2) to handle user input and generate responses.
