import csv
import json
import time
import uuid
from azure.cosmos import CosmosClient, PartitionKey
import config

# Azure Cosmos DB configuration
endpoint = config.AZURE_COSMOSDB_ENDPOINT
key = config.AZURE_COSMOSDB_KEY
database_name = "GAB2025"
container_name = "Products"

# Initialize the Cosmos client
client = CosmosClient(endpoint, key)

# Create a database
database = client.create_database_if_not_exists(id=database_name)

# Create a container
container = database.create_container_if_not_exists(
    id=container_name,
    partition_key=PartitionKey(path="/category"),
    offer_throughput=400
)

# Path to the CSV file
csv_file_path = "shein-products.csv"

# Read the CSV file and import data into Cosmos DB
with open(csv_file_path, mode='r', encoding='utf-8') as csv_file:
    csv_reader = csv.DictReader(csv_file)
    for row in csv_reader:
        # Convert the row to JSON format
        item = json.loads(json.dumps(row))
        item["id"] = uuid.uuid4().hex

        print(f"Inserting item: {item['id']} - {item['category']}")
        # wait 1 second
        time.sleep(1)
        # Insert the item into the container
        container.create_item(body=item)

print("Data import completed successfully.")