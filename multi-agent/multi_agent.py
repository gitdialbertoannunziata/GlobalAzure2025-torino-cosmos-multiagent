import datetime
import random

# Replace Swarm impor
from agents import Agent, OpenAIChatCompletionsModel,  function_tool
import config
import azure_cosmos_db
import azure_open_ai


@function_tool
def refund_item(user_id, item_id):
    """Initiate a refund based on the user ID and item ID.
    Takes as input arguments in the format '{"user_id":1,"item_id":3}'
    """
    
    try:
        container = azure_cosmos_db.PURCHASE_HISTORY_CONTAINER
        
        query = "SELECT c.amount FROM c WHERE c.user_id=@user_id AND c.item_id=@item_id"
        parameters = [
            {"name": "@user_id", "value": int(user_id)},
            {"name": "@item_id", "value": int(item_id)}
        ]
        items = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
        
        if items:
            amount = items[0]['amount']
            # Refund the amount to the user
            refund_message = f"Refunding ${amount} to user ID {user_id} for item ID {item_id}."
            return refund_message
        else:
            refund_message = f"No purchase found for user ID {user_id} and item ID {item_id}. Refund initiated."
            return refund_message
    
    except Exception as e:
        print(f"An error occurred during refund: {e}")

@function_tool
def notify_customer(user_id, method):
    """Notify a customer by their preferred method of either phone or email.
    Takes as input arguments in the format '{"user_id":1,"method":"email"}'"""
    
    try:
        container = azure_cosmos_db.USERS_CONTAINER
        
        query = "SELECT c.email, c.phone FROM c WHERE c.user_id=@user_id"
        parameters = [{"name": "@user_id", "value": int(user_id)}]
        items = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
        
        if items:
            email, phone = items[0]['email'], items[0]['phone']
            if method == "email" and email:
                print(f"Emailed customer {email} a notification.")
            elif method == "phone" and phone:
                print(f"Texted customer {phone} a notification.")
            else:
                print(f"No {method} contact available for user ID {user_id}.")
        else:
            print(f"User ID {user_id} not found.")
    
    except Exception as e:
        print(f"An error occurred during notification: {e}")

@function_tool
def order_item(user_id, product_id=None):
    """Place an order for a product based on the user ID and product ID.
    Takes as input arguments in the format '{"user_id":1,"product_id":2}'"""
    
    if not product_id:
        return "Product ID is missing. Please provide a valid product ID."

    print(f"Ordering item {product_id} for user ID {user_id}")

    try:
        # Get the current date and time for the purchase
        date_of_purchase = datetime.datetime.now().isoformat()
        # Generate a random item ID
        item_id = random.randint(1, 300)

        container = azure_cosmos_db.PRODUCTS_CONTAINER
        
        # Query the database for the product information
        query = "SELECT c.product_id, c.product_name, c.final_price FROM c WHERE c.product_id=@product_id"
        parameters = [{"name": "@product_id", "value": str(product_id)}]
        items = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
        
        if items:
            product = items[0]
            product_id, product_name, price = product['product_id'], product['product_name'], product['final_price']
            
            print(f"Ordering product {product_name} for user ID {user_id}. The price is {price}.")
            
            # Add the purchase to the database
            azure_cosmos_db.add_purchase(int(user_id), date_of_purchase, item_id, price)
            
            order_item_message = f"Order placed for product {product_name} for user ID {user_id}. Item ID: {item_id}."
            return order_item_message
        else:
            order_item_message = f"Product {product_id} not found."
            return order_item_message
    
    except Exception as e:
        print(f"An error occurred during order placement: {e}")

@function_tool
async def product_information(user_prompt):
    """Provide information about a product based on the user prompt.
    Takes as input the user prompt as a string."""
    
    # Perform a vector search on the Cosmos DB container and return results to the agent

    vectors = await azure_open_ai.generate_embedding(user_prompt)
    vector_search_results = product_vector_search(vectors)
    
    return vector_search_results

# Perform a vector search on the Cosmos DB container
def product_vector_search(vectors, num_results=3):
    
    # Execute the query
    container = azure_cosmos_db.PRODUCTS_CONTAINER
    items = []
    try:
        items = container.query_items(
            query='''
            SELECT TOP @num_results c.product_id, c.final_price, c.description, c.product_name
            FROM c
            where VectorDistance(c.productVector,@embedding) > @distance
            ORDER BY VectorDistance(c.productVector,@embedding)
            ''',
            parameters=[
                {"name": "@embedding", "value": vectors},
                {"name": "@num_results", "value": num_results},
                {"name": "@distance", "value": 0.1}
            ],
            enable_cross_partition_query=True, populate_query_metrics=True)
    except Exception as e:
        print(f"Vector search failed: {e}")
        
    print("Executed vector search in Azure Cosmos DB... \n", vectors)

    
    # Extract the necessary information from the results
    formatted_results = []   

    print('Result', items)

    for result in items:
        result['product_id'] = str(result['product_id'])
        result['description'] = "product id " + result['product_id'] + ": " + result['product_name'] + " - " + result['description']
        # add price to product_description as well

        formatted_result = {
            'product': result
        }
        formatted_results.append(formatted_result)
    
    return formatted_results


# Initialize the database
azure_cosmos_db.initialize_database()

# Preview tables
azure_cosmos_db.preview_table("Users")
azure_cosmos_db.preview_table("PurchaseHistory")
azure_cosmos_db.preview_table("Products")


@function_tool
def transfer_to_sales():
    return sales_agent

@function_tool
def transfer_to_refunds():
    return refunds_agent

@function_tool
def transfer_to_product():
    return product_agent

@function_tool
def transfer_to_triage():
    return triage_agent


# Define the agents
refunds_agent = Agent(
    name="Refunds Agent",
    tools=[transfer_to_triage, refund_item, notify_customer],
    instructions="""You are a refund agent that handles all actions related to refunds after a return has been processed.
    You must ask for both the user ID and item ID to initiate a refund. 
    If item_id is present in the context information, use it. 
    Otherwise, do not make any assumptions, you must ask for the item ID as well.
    Ask for both user_id and item_id in one message.
    Do not use any other context information to determine whether the right user id or item id has been provided - just accept the input as is.
    If the user asks you to notify them, you must ask them what their preferred method of notification is. For notifications, you must
    ask them for user_id and method in one message.
    If the user asks you a question you cannot answer, transfer back to the triage agent.""",
    model=OpenAIChatCompletionsModel(
        model=config.AZURE_OPENAI_GPT_DEPLOYMENT,
        openai_client=azure_open_ai.openai_client,
    ),
)

sales_agent = Agent(
    name="Sales Agent",
    model=OpenAIChatCompletionsModel(
        model=config.AZURE_OPENAI_GPT_DEPLOYMENT,
        openai_client=azure_open_ai.openai_client,
    ),
    tools=[transfer_to_triage, order_item, notify_customer, transfer_to_refunds],
    instructions="""You are a sales agent that handles all actions related to placing an order to purchase an item.
    Always check the context for the product ID before asking the user. 
    If the product ID is present in the context information, use it directly without asking the user. 
    Otherwise, you must ask for the product ID. 
    If the product ID is unknown to the user, do not make any assumptions about the product ID and transfer to the product agent.
    An order cannot be placed without both the user ID and product ID. Ask for both user_id and product_id in one message if they are not in the context.
    If the user asks you to notify them, you must ask them what their preferred method is. For notifications, you must
    ask them for user_id and method in one message.
    If the user asks you a question you cannot answer, transfer back to the triage agent."""
)

product_agent = Agent(
    name="Product Agent",
    model=OpenAIChatCompletionsModel(
        model=config.AZURE_OPENAI_GPT_DEPLOYMENT,
        openai_client=azure_open_ai.openai_client,
    ),
    tools=[transfer_to_triage, product_information, transfer_to_sales, transfer_to_refunds],
    instructions="""You are a product agent that provides information about products in the database.
    When calling the product_information function, do not make any assumptions 
    about the product id, or number the products in the response and the product. Instead, use the product id from the response to 
    product_information and align that product id whenever referring to the corresponding product in the database. 
    Only give the user very basic information about the product do not make any assumptions.
    If the user asks for more information about any product, provide it. 
    If the user asks you a question you cannot answer, transfer back to the triage agent.
    """
)

triage_agent = Agent(
    name="Triage Agent",
    handoffs=[sales_agent, refunds_agent, product_agent],
    tools=[transfer_to_sales, transfer_to_refunds, transfer_to_product],
    instructions="""You are to triage a users request, and call a tool to transfer to the right intent.
    Otherwise, once you are ready to transfer to the right intent, call the tool to transfer to the right intent.
    You dont need to know specifics, just the topic of the request.
    If the user asks for product information, transfer to the Product Agent.
    If the user request is about making an order or purchasing an item, transfer to the Sales Agent.
    If the user request is about getting a refund on an item or returning a product, transfer to the Refunds Agent.
    When you need more information to triage the request to an agent, ask a direct question without explaining why you're asking it.
    Do not share your thought process with the user! Do not make unreasonable assumptions on behalf of user.""",
    model=OpenAIChatCompletionsModel(
        model=config.AZURE_OPENAI_GPT_DEPLOYMENT,
        openai_client=azure_open_ai.openai_client,
    ),
)



# async def run_demo_loop(starting_agent, context_variables=None, stream=False, debug=False) -> None:
    
#     print("Starting OpenAi CLI 🐝")

#     messages = []
#     agent = starting_agent
#     result = await Runner.run(agent, input="Hello", context_variables=context_variables)


#     while True:
        
#         # Format the displayed "User:" text in grey to offset from user input
#         user_input = input("\033[90mUser\033[0m: ")
#         messages.append({"role": "user", "content": user_input})

#         if stream:
#             response = Runner.run_streamed(
#                 starting_agent,
#                 messages
#             )
#         else:
#             response = Runner.run(
#                 starting_agent,
#                 messages
#             )
        
#         print (f"Agent: {response.agent.name}")
#         print (f"Agent: {response.agent.instructions}")
#         print (f"Agent: {response.agent.tools}")
#         print (f"Agent: {response.agent.handoffs}")
        
#         if stream:
#             async for event in response.stream_events():
#                 if event.type == "raw_response_event":
#                     continue
#                 elif event.type == "agent_updated_stream_event":
#                     print(f"Agent updated: {event.new_agent.name}")
#                     continue
#                 elif event.type == "run_item_stream_event":
#                     if event.item.type == "tool_call_item":
#                         print("-- Tool was called")
#                     elif event.item.type == "tool_call_output_item":
#                         print(f"-- Tool output: {event.item.output}")
#                     elif event.item.type == "message_output_item":
#                         messages.append({ "role": "assistant", "content":  ItemHelpers.text_message_output(event.item) })
#                         print(f"-- Message output:\n {ItemHelpers.text_message_output(event.item)}")
#                     else:
#                         pass  # Ignore other event types
#         else:
#            for new_item in response.new_items:
#                 agent_name = new_item.agent.name
#                 if isinstance(new_item, MessageOutputItem):
#                     print(f"{agent_name}: {ItemHelpers.text_message_output(new_item)} - {user_input}")
#                     messages.append({"role": "assistant", "content": ItemHelpers.text_message_output(new_item)})

#                 elif isinstance(new_item, HandoffOutputItem):
#                     print(
#                         f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}"
#                     )
#                 elif isinstance(new_item, ToolCallItem):
#                     print(f"{agent_name}: Calling a tool")
#                 elif isinstance(new_item, ToolCallOutputItem):
#                     print(f"{agent_name}: Tool call output: {new_item.output}")
#                 else:
#                     print(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")

#                 print(f"Response: {response}")
#                 user_input = result.input

#         agent = response.agent

# if __name__ == "__main__":
#     # Run the demo loop
#     asyncio.run(run_demo_loop(triage_agent, debug=False))