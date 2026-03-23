# Bookly Support Agent
AI customer support agent for Bookly, a fictional online bookstore.
Built for the Decagon Solutions Engineering take-home assignment.

## What It Does
Conversational AI agent that handles:
- **Order status inquiries** — looks up real-time order status and tracking
- **Return requests** — multi-turn flow to collect info and process returns
- **Policy questions** — shipping options, return windows, password reset

## Architecture
ReAct (Reason + Act) agent loop built on Claude's tool-use API. The agent:
1. Receives a customer message with full conversation history
2. Decides whether to respond, ask a clarifying question, or call a tool
3. If a tool is needed, executes it and incorporates the result
4. Loops until it has enough information to give a final response

- **Tools:** `get_order_status`, `process_return_request`, `lookup_policy`
- **Model:** claude-sonnet-4-6 via Anthropic API
- **Frontend:** Simple web chat (Flask + vanilla JS)

## Project Structure
```
bookly-support-agent/
├── app.py          # Flask web server, session management
├── agent.py        # ReAct agent loop, tool execution, Claude API calls
├── tools.py        # Mock tool functions (order lookup, returns, policies)
├── prompts.py      # System prompt encoding all business rules (the AOP layer)
├── static/
│   └── index.html  # Chat UI
├── DESIGN.md       # One-page architecture and design decisions
└── requirements.txt
```

## Setup

### Prerequisites
- Python 3.11+
- Anthropic API key (get one at console.anthropic.com)

### Installation
```bash
git clone https://github.com/glykins/bookly-support-agent.git
cd bookly-support-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration
Create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=your_key_here
```

### Run
```bash
python app.py
```
Open http://127.0.0.1:5000 in your browser.

## Demo Scenarios
Use these order IDs to test:
- **ORD-1234** — shipped order with tracking number, eligible for return
- **ORD-5678** — processing order, not yet shipped, return will be rejected

Use the **↺ button** in the chat to reset between scenarios.

**Try these conversations:**

**Scenario 1 — ORD-1234 (Shipped order, full return flow):**
1. Type `hi I need help with my order` → agent asks for your order ID (clarifying question)
2. Type `ORD-1234` → agent calls `get_order_status` and returns shipped status with tracking number
3. Type `what's your return policy?` → agent calls `lookup_policy` and explains the 30-day window
4. Type `I want to return one of the books` → agent asks which book and why (multi-turn collection)
5. Type `Atomic Habits, it was a duplicate gift` → agent calls `process_return_request` and confirms with a return ID

**Scenario 2 — ORD-5678 (Processing order, business rule rejection):**
1. Type `what is the status of order ORD-5678` → agent calls `get_order_status`, returns processing status with no tracking yet
2. Type `I want to return Dune, I ordered the wrong edition` → agent calls `process_return_request`, tool rejects it because order hasn't shipped, agent communicates the restriction

**Scenario 3 — Policy question (single tool call):**
1. Type `how much does expedited shipping cost?` → agent calls `lookup_policy` and returns shipping options and pricing

Watch the terminal while chatting — every tool call prints in real time:
```
→ Tool called: get_order_status({'order_id': 'ORD-1234'})
→ Tool result: {'success': True, 'order': {...}}
```

## Design Decisions
See the one-page design document: [DESIGN.md](DESIGN.md)