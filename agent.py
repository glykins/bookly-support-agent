import json
import os
from anthropic import Anthropic
from prompts import BOOKLY_SYSTEM_PROMPT
from tools import get_order_status, process_return_request, lookup_policy

# Load ANTHROPIC_API_KEY from .env file
from dotenv import load_dotenv
load_dotenv()

#This agent implements the ReAct pattern (Reason and Act)
client = Anthropic()

TOOLS = [
    {
        "name": "get_order_status",
        "description": "Look up the status, tracking information, and estimated delivery for a customer order. Call this whenever a customer asks about their order.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID, i.e. ORD-1234"
                }
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "process_return_request",
        "description": "Initiate a return request for an order. Only call this once you have the order ID, reason for return, and list of items to return.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to process the return for"
                },
                "reason": {
                    "type": "string",
                    "description": "The customer's reason for returning"
                },
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of item names the customer wants to return"
                }
            },
            "required": ["order_id", "reason", "items"]
        }
    },
    {
        "name": "lookup_policy",
        "description": "Retrieve Bookly's policies. Use for questions about shipping options, return windows, or password reset steps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "policy_type": {
                    "type": "string",
                    #enum restricts to specific valid values and prevents from calling with "refund_policy" or other variants that the tool doesn't know how to handle
                    "enum": ["returns", "shipping", "password_reset"],
                    "description": "The policy category to retrieve"
                }
            },
            "required": ["policy_type"]
        }
    }
]

#Bridge between tool call request and actual Python functions in tools.py
def execute_tool(tool_name: str, tool_input: dict) -> str:
    print(f"  → Tool called: {tool_name}({tool_input})")
    #Explicit routing is intentional for ease of debugging and preventing unexpected tools from being called
    if tool_name == "get_order_status":
        result = get_order_status(tool_input["order_id"])
    elif tool_name == "process_return_request":
        result = process_return_request(
            tool_input["order_id"],
            tool_input["reason"],
            tool_input["items"]
        )
    elif tool_name == "lookup_policy":
        result = lookup_policy(tool_input["policy_type"])
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    print(f"  → Tool result: {result}")
    return json.dumps(result)

#Process one customer message through the full ReAct loop (Perceive, Reason, Act, Observe, Repeat, Respond)
#and return the agent's final response along with the updated conversation history
def run_agent(conversation_history: list, user_message: str):
    updated_history = conversation_history + [
        {"role": "user", "content": user_message}
    ]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=BOOKLY_SYSTEM_PROMPT,
            tools=TOOLS,
            messages=updated_history
        )

        if response.stop_reason == "tool_use":
            updated_history.append({
                "role": "assistant",
                "content": response.content
            })

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            updated_history.append({
                "role": "user",
                "content": tool_results
            })

        else:
            final_response = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_response += block.text

            updated_history.append({
                "role": "assistant",
                "content": final_response
            })

            return final_response, updated_history