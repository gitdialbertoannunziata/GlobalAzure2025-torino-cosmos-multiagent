import json
import config

from openai import AsyncAzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from agents import set_default_openai_client

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)


  
openai_client = AsyncAzureOpenAI(  
    azure_endpoint=config.AZURE_OPENAI_ENDPOINT,  
    azure_ad_token_provider=token_provider,  
    api_version="2024-05-01-preview",  
)  

#Preparare la richiesta di chat 
chat_prompt = [
  {"role": "system", "content": "You are a helpful assistant."},
  {"role": "user", "content": "Can you tell me about the Global Azure event in 2025?"}
]
    
# Includere risultato vocale se il riconoscimento vocale è abilitato  
messages = chat_prompt  


print("[DEBUG] Initialized Azure OpenAI client.")
print("[DEBUG] Azure OpenAI client initialized with endpoint:", config.AZURE_OPENAI_ENDPOINT)
print("[DEBUG] Azure OpenAI client initialized with deployment:", config.AZURE_OPENAI_GPT_DEPLOYMENT)

# Set the default OpenAI client to the Azure OpenAI client
set_default_openai_client(openai_client)
print("[DEBUG] Set default OpenAI client to Azure OpenAI client.") 
print("[DEBUG] Initialized Azure OpenAI client.")

async def generate_embedding(text):
    print("[DEBUG] Generating embedding for text:", text)
    response = await openai_client.embeddings.create(input=text, model=config.AZURE_OPENAI_EMBEDDING_DEPLOYMENT)
    json_response = response.model_dump_json(indent=2)
    parsed_response = json.loads(json_response)
    return parsed_response['data'][0]['embedding']