import config

from azure.cosmos import CosmosClient, PartitionKey, exceptions

# Initialize the Cosmos client
# reference environment variables for the values of these variables
endpoint = config.AZURE_COSMOSDB_ENDPOINT
client = CosmosClient(endpoint, config.AZURE_COSMOSDB_KEY)
print("Cosmos client initialized")

# Create global variables for the database and containers
global DATABASE_NAME, USERS_CONTAINER_NAME, PURCHASE_HISTORY_CONTAINER_NAME, PRODUCTS_CONTAINER_NAME
global DATABASE, USERS_CONTAINER, PURCHASE_HISTORY_CONTAINER, PRODUCTS_CONTAINER

# Database and container names
DATABASE_NAME = "GAB2025"
USERS_CONTAINER_NAME = "Users"
PURCHASE_HISTORY_CONTAINER_NAME = "PurchaseHistory"
PRODUCTS_CONTAINER_NAME = "Products"

# Database and container references (hydrated in create_database)
DATABASE = None
USERS_CONTAINER = None
PURCHASE_HISTORY_CONTAINER = None
PRODUCTS_CONTAINER = None

# Create database and containers if they don't exist
def create_database():
    global DATABASE, USERS_CONTAINER, PURCHASE_HISTORY_CONTAINER, PRODUCTS_CONTAINER
    
    try:
        DATABASE = client.create_database_if_not_exists(id=DATABASE_NAME)
        
        USERS_CONTAINER = DATABASE.create_container_if_not_exists(
            id=USERS_CONTAINER_NAME,
            partition_key=PartitionKey(path="/user_id")
        )
        
        PURCHASE_HISTORY_CONTAINER = DATABASE.create_container_if_not_exists(
            id=PURCHASE_HISTORY_CONTAINER_NAME,
            partition_key=PartitionKey(path="/user_id")
        )

        PRODUCTS_CONTAINER = DATABASE.create_container_if_not_exists(
            id=PRODUCTS_CONTAINER_NAME,
            partition_key=PartitionKey(path="/category")
        )
        
    except exceptions.CosmosHttpResponseError as e:
        print(f"Database creation failed: {e}")

def add_user(user_id, first_name, last_name, email, phone):  
    
    user = {
        "id": str(user_id),
        "user_id": user_id,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone
    }
    try:
        USERS_CONTAINER.create_item(body=user)
    except exceptions.CosmosResourceExistsError:
        print(f"User with user_id {user_id} already exists.")

def add_purchase(user_id, date_of_purchase, item_id, amount):
    
    purchase = {
        "id": f"{user_id}_{item_id}_{date_of_purchase}",
        "user_id": user_id,
        "date_of_purchase": date_of_purchase,
        "item_id": item_id,
        "amount": amount
    }
    try:
        PURCHASE_HISTORY_CONTAINER.create_item(body=purchase)
    except exceptions.CosmosResourceExistsError:
        print(f"Purchase already exists for user_id {user_id} on {date_of_purchase} for item_id {item_id}.")
    


def preview_table(container_name):
    
    container = DATABASE.get_container_client(container_name)
    
    items = container.query_items(
        query="SELECT TOP 5 * FROM c",
        enable_cross_partition_query=True
    )
    
    # Clean up the items for display
    for item in items:
        item.pop("_rid", None)
        item.pop("_self", None)
        item.pop("_etag", None)
        item.pop("_attachments", None)
        item.pop("_ts", None)
        if (container_name == PRODUCTS_CONTAINER_NAME):
            # redact the vectors for the product description
            item.pop("productVector", None)
            item.pop("hash", None)
       # print(item)

# Initialize and load database
def initialize_database():
    
    # Create the database and containers if not exists (legacy, rerun azd up if needed)
    create_database()

    # Add some initial users
    initial_users = [
        (1, "Alice", "Smith", "alice@test.com", "123-456-7890"),
        (2, "Bob", "Johnson", "bob@test.com", "234-567-8901"),
        (3, "Sarah", "Brown", "sarah@test.com", "555-567-8901"),
        # Add more initial users here
    ]

    for user in initial_users:
        add_user(*user)

    # Add some initial purchases
    initial_purchases = [
        (1, "2024-01-01", "40460214", 99.99),
        (2, "2023-12-25", "40460214", 39.99),
        (3, "2023-11-14", "40460214", 49.99),
    ]

    for purchase in initial_purchases:
        add_purchase(*purchase)