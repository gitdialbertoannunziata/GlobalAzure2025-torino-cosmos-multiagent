import asyncio
import gradio as gr
from gradio import ChatMessage
# Import all agents
from multi_agent import triage_agent, sales_agent, refunds_agent, product_agent
from agents import  Runner, MessageOutputItem, HandoffOutputItem, ToolCallItem, ToolCallOutputItem, ItemHelpers

# Map agent names to agent objects
agent_map = {
    "Triage Agent": triage_agent,
    "Sales Agent": sales_agent,
    "Refunds Agent": refunds_agent,
    "Product Agent": product_agent,
}



# Input from user comes here, put breakpoint here to debug the agent workflow
async def chat_interface(user_input, agent_name="Triage Agent", messages=None):
    if messages is None:
        messages = []

    # Update messages with user input
    messages.append({"role": "user", "content": user_input})

    # Get the current agent object from the map
    agent = agent_map.get(agent_name, triage_agent)
    next_agent = agent_name
    
    try:
       
       result = await Runner.run(agent, messages)

       for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    print(f"{agent_name}: {ItemHelpers.text_message_output(new_item)} - {user_input}")
                    messages.append({"role": "assistant", "content": ItemHelpers.text_message_output(new_item)})

                elif isinstance(new_item, HandoffOutputItem):
                    print(
                        f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}"
                    )
                elif isinstance(new_item, ToolCallItem):
                    print(f"{agent_name}: Calling a tool")
                elif isinstance(new_item, ToolCallOutputItem):
                    print(f"{agent_name}: Tool call output: {new_item.output}")
                else:
                    print(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")
                user_input = result.input
        

       # Update agent state
       

    except Exception as e:
        print(f"Error: {e}")



    return messages, next_agent, messages





# Define Gradio UI
with gr.Blocks(css=".chatbox { background-color: #f9f9f9; border-radius: 10px; padding: 10px; }",) as demo:

     agent_name = gr.State("Triage Agent")
     history = gr.State([])
    
     gr.Markdown(
         """
         # Personal Shopping AI Assistant
         Welcome to your Personal Shopping AI Assistant. 
         Get help with shopping, refunds, product information, and more!
         """,
         elem_id="header",
     )

     with gr.Row():
         chatbot = gr.Chatbot(
             label="Chat with the Assistant",
             elem_classes=["chatbox"],
             type="messages",
         )

     with gr.Row():
         user_input = gr.Textbox(
             placeholder="Enter your message here...",
             label="Your Message",
             lines=1,
             elem_id="user_input",
         )

    
     # Chat interaction
     user_input.submit(
        fn=lambda *args: asyncio.run(chat_interface(*args)),
        inputs=[user_input, agent_name, history],
        outputs=[chatbot, agent_name, history],
     ).then(
        lambda: "", inputs=None, outputs=user_input
     )  # Clear the input box after submission

demo.launch()