from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.prompts import PromptTemplate
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.llms import CTransformers
from langchain.chains import RetrievalQA
import chainlit as cl

DB_FAISS_PATH = 'vectorstore/db_faiss'

# Custom prompt template
custom_prompt_template = """Use the following pieces of information to answer the user's question.
If you don't know the answer, just say that you don't know, don't try to make up an answer.

Context: {context}
Question: {question}

Only return the helpful answer below and nothing else.
Helpful answer:
"""

# Function to set the custom prompt
def set_custom_prompt():
    """
    Prompt template for QA retrieval for each vectorstore
    """
    prompt = PromptTemplate(
        template=custom_prompt_template,
        input_variables=['context', 'question']
    )
    return prompt

# Function to create the Retrieval QA chain
def retrieval_qa_chain(llm, prompt, db):
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type='stuff',
        retriever=db.as_retriever(search_kwargs={'k': 2}),
        return_source_documents=True,
        chain_type_kwargs={'prompt': prompt}
    )
    return qa_chain

# Function to load the LLM
def load_llm():
    """
    Load the locally downloaded model here
    """
    llm = CTransformers(
        model="llama-2-7b-chat.ggmlv3.q8_0.bin",
        model_type="llama",
        max_new_tokens=512,
        temperature=0.5
    )
    return llm

# Function to initialize the QA bot
def qa_bot():
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )
    db = FAISS.load_local(DB_FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
    llm = load_llm()
    qa_prompt = set_custom_prompt()
    qa = retrieval_qa_chain(llm, qa_prompt, db)
    return qa

# Chainlit Event: Start Chat
@cl.on_chat_start
async def start():
    try:
        # Initialize the QA bot and set it in the user session
        chain = qa_bot()
        cl.user_session.set("chain", chain)
        await cl.Message(content="Hi! I'm your Blockchain assistant. How can I help you?").send()
    except Exception as e:
        await cl.Message(content=f"Failed to initialize the bot: {str(e)}").send()

# Chainlit Event: Handle User Message
@cl.on_message
async def main(message: cl.Message):
    try:
        chain = cl.user_session.get("chain")  # Retrieve the chain from the session
        if not chain:
            await cl.Message(content="Bot not initialized. Please restart the session.").send()
            return
        
        # Combine question into query format
        query = f"Context: Some context\nQuestion: {message.content}"
        
        # Get response using acall (async version of invoke)
        response = await chain.acall({"query": query})
        answer = response["result"]
        sources = response["source_documents"]

        # Append sources if available
        if sources:
            answer += f"\n\nSources:\n" + "\n".join(str(source.metadata) for source in sources)
        else:
            answer += "\n\nNo sources found."

        # Send the answer back to the user
        await cl.Message(content=answer).send()
    except Exception as e:
        # Handle errors gracefully
        await cl.Message(content=f"An error occurred: {str(e)}").send()
