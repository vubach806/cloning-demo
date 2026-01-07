# Project 100 FR - Multi-Agent Sales System

A sophisticated multi-agent system built with PydanticAI for intelligent sales conversations, customer profiling, and automated workflow orchestration.

## 📋 Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [System Flow](#system-flow)
- [Agents Overview](#agents-overview)
- [Database Schema](#database-schema)
- [Setup & Installation](#setup--installation)
- [Usage](#usage)
- [Project Structure](#project-structure)

## 🎯 Overview

This system implements an intelligent sales assistant that:

- **Understands customer intent** through natural language processing
- **Profiles customers** based on historical data
- **Predicts requirements** (explicit and implicit)
- **Suggests products** through up-sell/cross-sell opportunities
- **Manages sales conversations** through structured sales nodes
- **Validates content** before storage (Guardrail)
- **Manages memory** across multiple storage layers (Redis, PostgreSQL, Milvus)

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Input                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Reception & Memory Management                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Redis - Conversation Buffer (Short-term Memory)      │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Initial Analysis (Parallel)                      │
│  ┌──────────────┐         ┌──────────────────┐            │
│  │ Intent Agent │         │ Analyse Handoff   │            │
│  │              │         │ Agent             │            │
│  └──────┬───────┘         └────────┬──────────┘            │
│         │                          │                        │
│         └──────────┬───────────────┘                        │
│                    ▼                                         │
│         ┌──────────────────────┐                            │
│         │ Orchestrator Agent    │                            │
│         │ (Task Selection)      │                            │
│         └───────────┬───────────┘                            │
└─────────────────────┼────────────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
┌─────────────────┐      ┌──────────────────┐
│  sales_task     │      │  human_handle     │
│  (Sales Flow)   │      │  (Escalate)       │
└────────┬────────┘      └───────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│              Sales Workflow                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Predict      │  │ Classify     │  │ Profile      │    │
│  │ Requirement  │  │ Step         │  │ Agent        │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                  │                  │             │
│         └──────────┬───────┴──────────────────┘            │
│                    ▼                                         │
│         ┌──────────────────────┐                            │
│         │ Up Sales / Cross     │                            │
│         │ Sales Agent          │                            │
│         └───────────┬──────────┘                            │
│                     │                                        │
│                     ▼                                        │
│         ┌──────────────────────┐                            │
│         │ Sales Agent           │                            │
│         │ (Response Generation) │                            │
│         └───────────┬──────────┘                            │
└─────────────────────┼──────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Guardrail Agent                                 │
│  (Content Validation & Moderation)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Memory Storage                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Redis       │  │ PostgreSQL   │  │ Milvus       │      │
│  │ (Short-term)│  │ (Episodic)   │  │ (Semantic)   │      │
│  └─────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 System Flow

### Phase 1: Initial Reception & Analysis

1. **User Input Reception**
   - User message received via Chainlit interface
   - Stored in Redis Conversation Buffer (short-term memory)

2. **Parallel Analysis** (Intent Agent + Analyse Handoff Agent)
   - **Intent Agent**: Extracts and clarifies user intent
   - **Analyse Handoff Agent**: Analyzes emotion, policy flags, determines if human handoff needed
   - Both run in parallel for efficiency

3. **Orchestration**
   - **Orchestrator Agent**: Takes results from both agents
   - Decides next task: `sales_task` or `human_handle`
   - If `human_handle`: Updates PostgreSQL with handoff reason

### Phase 2: Sales Workflow (if `sales_task`)

1. **Requirement Prediction**
   - **Predict Requirement Agent**: Analyzes latest message + conversation history
   - Extracts explicit and implicit requirements
   - Determines service type

2. **Step Classification**
   - **Classify Step Agent**: Determines current sales node
   - Identifies allowed next nodes based on sales graph
   - Updates PostgreSQL session with current stage

3. **Customer Profiling**
   - **Profile Agent**: Analyzes historical data (orders, spend, recency)
   - Assigns customer label (VIP, tiềm năng, bình thường, etc.)
   - Calculates priority score

4. **Product Recommendation**
   - **Up Sales / Cross Sales Agent**: Matches requirements with available combos
   - Considers stock availability
   - Selects best combo and provides reason

5. **Response Generation**
   - **Sales Agent**: Generates natural conversation response
   - Uses customer label, sales node, requirements, selected combo
   - Maintains appropriate tone (professional_warm, friendly, etc.)
   - Predicts next expected input type

### Phase 3: Content Validation

1. **Guardrail Check**
   - **Guardrail Agent**: Validates response text
   - Checks content accuracy, business rules, sales claims
   - Modifies text if needed
   - Flags sales content for double-check if necessary

2. **Memory Storage**
   - Approved content stored in Redis Conversation Buffer
   - Older messages moved to PostgreSQL (sliding window)
   - Summary generated every 50 messages

## 🤖 Agents Overview

### Core Analysis Agents

#### 1. Intent Agent
**Purpose**: Extracts and clarifies user intent from raw messages

**Input**:
- `user_id`, `session_id`, `raw_message`, `language`

**Output**:
- `clean_intent_text`: Clarified intent statement
- `intent_code`: Classification code (purchase_consultation, product_inquiry, etc.)
- `confidence`: Confidence score (0-1)

**Key Features**:
- Handles ambiguous user queries
- Classifies intent into predefined categories
- Provides confidence scoring

---

#### 2. Analyse Handoff Agent
**Purpose**: Analyzes user emotion and determines if human intervention is needed

**Input**:
- `user_id`, `session_id`, `raw_message`, `language`

**Output**:
- `policy_flags`: Legal, medical, financial, technical flags
- `emotion_score`: Frustration, anger, sadness, joy, fear, neutral
- `handoff_required`: Boolean flag
- `handoff_reason`: Reason if handoff needed
- `risk_level`: low, medium, high
- `confidence`: Confidence score

**Key Features**:
- Emotion detection and scoring
- Policy compliance checking
- Risk assessment
- Handoff decision making

---

#### 3. Orchestrator Agent
**Purpose**: Central decision maker that selects the main task based on analysis results

**Input**:
- Results from Intent Agent and Analyse Handoff Agent

**Output**:
- `task`: `sales_task` or `human_handle`
- `task_reason`: Explanation for task selection
- All relevant flags and scores

**Key Features**:
- Combines multiple agent outputs
- Makes high-level routing decisions
- Updates session metadata in PostgreSQL

---

### Sales Workflow Agents

#### 4. Predict Requirement Agent
**Purpose**: Predicts customer requirements (explicit and implicit) from messages

**Input**:
- `latest_message`: Most recent user message
- `short_memory`: 20 most recent conversation segments (from Redis)
- `sales_node`: Current sales stage

**Output**:
- `explicit_requirements`: Directly stated requirements
- `implicit_requirements`: Inferred requirements
- `service_type`: product_purchase, consultation, support, etc.

**Key Features**:
- Extracts both explicit and implicit needs
- Considers conversation context
- Classifies service type

---

#### 5. Classify Step Agent
**Purpose**: Classifies the current step in the sales process

**Input**:
- `clean_intent_text`: Clarified intent
- `sales_graph`: Sales graph with nodes and current node

**Output**:
- `current_sales_node`: Classified current node
- `allowed_next_nodes`: Valid next steps
- `reason`: Classification reason
- `confidence`: Confidence score

**Key Features**:
- Respects sales graph transitions
- Determines valid next steps
- Updates PostgreSQL session stage

---

#### 6. Profile Agent
**Purpose**: Profiles customers based on historical purchase data

**Input**:
- `user_id`: User identifier
- `historical_data`: Total orders, total spend, last purchase days
- `label_definitions`: Available labels (VIP, tiềm năng, bình thường, etc.)

**Output**:
- `customer_label`: Assigned label
- `confidence`: Confidence score
- `priority_score`: Priority score (0-5)

**Key Features**:
- Customer segmentation
- Priority scoring
- Historical data analysis

---

#### 7. Up Sales / Cross Sales Agent
**Purpose**: Identifies up-sell and cross-sell opportunities

**Input**:
- `requirements`: Explicit and implicit requirements
- `available_combos`: Product combos with stock information
- `short_memory`: Recent conversation history
- `summary_conversation`: Conversation summary (optional)

**Output**:
- `selected_combo`: Best matching combo ID
- `reason`: Selection reason
- `response_text`: Usually empty (used by Sales Agent)

**Key Features**:
- Matches requirements with products
- Considers stock availability
- Provides selection reasoning

---

#### 8. Sales Agent
**Purpose**: Generates natural sales conversation responses

**Input**:
- `customer_label`: Customer profile label
- `sales_node`: Current sales stage
- `requirements`: Customer requirements
- `selected_combo`: Recommended combo
- `tone_policy`: professional_warm, friendly, formal, consultative
- `short_memory`: Recent conversation history

**Output**:
- `response_text`: Natural conversation response (Vietnamese)
- `next_expected_input`: Expected user input type
- `stay_in_sales_node`: Whether to stay in current node

**Key Features**:
- Natural language generation
- Tone adaptation
- Conversation flow management
- Next step prediction

---

### Content Management Agents

#### 9. Guardrail Agent
**Purpose**: Validates and moderates content before memory storage

**Input**:
- `response_text`: Text to validate
- `product_data`: Product information (optional)

**Output**:
- `approved`: Approval status
- `modified_text`: Corrected text (if needed)
- `sales_doublecheck`: Flag for human review
- `reason_recheck`: Reason for recheck

**Key Features**:
- Content accuracy validation
- Business rules compliance
- Sales claims verification
- Automatic text correction
- Human review flagging

---

#### 10. Summary Agent
**Purpose**: Generates conversation summaries for long-term memory

**Input**:
- Conversation history
- User information

**Output**:
- Summary text
- Tags
- Key topics
- Extracted user information

**Key Features**:
- Automatic summarization
- Topic extraction
- User information extraction
- Tag generation

---

## 💾 Database Schema

### PostgreSQL (Episodic Memory)

#### Sessions Table
- `id`: UUID (Primary Key)
- `user_id`: UUID (Foreign Key)
- `title`: Session title
- `handoff_reason`: Reason for human handoff
- `current_stage_id`: Current sales stage
- `created_at`, `updated_at`: Timestamps
- `session_metadata`: JSONB (Additional metadata)

#### Messages Table
- `id`: UUID (Primary Key)
- `session_id`: UUID (Foreign Key → Sessions)
- `role`: user, assistant, system, tool
- `content`: Message content
- `tool_calls`: JSONB (Tool usage data)
- `token_count`: Token count
- `created_at`: Timestamp

#### Other Tables
- `shops`: Shop information
- `products`: Product catalog
- `customers`: Customer profiles
- `documents`: Document storage
- `sales_pipelines`: Sales pipeline tracking

### Redis (Short-term Memory)

#### Conversation Buffer
- Linked list structure
- Stores recent messages (last 20-50)
- Fast access for agent context
- Sliding window mechanism moves old messages to PostgreSQL

#### Active Context
- Hash structure
- `current_goal`: Current conversation goal
- `extracted_entities`: Named entities
- `last_tool_used`: Last tool usage
- `user_mood`: Detected user mood
- `total_tokens`: Token count

### Milvus (Semantic Memory)

#### Vector Collection
- Stores embeddings of important messages
- Enables semantic search
- Used for context retrieval
- Similarity-based search

---

## 🚀 Setup & Installation

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- Gemini API Key ([Get one here](https://aistudio.google.com/app/apikey))

### 1. Clone Repository

```bash
git clone <repository-url>
cd project-100-fr
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

### 3. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp env.example .env
```

Edit `.env` and set:

```env
GEMINI_API_KEY=your_api_key_here
DEBUG=true  # Optional: enables debug output
```

### 4. Start Docker Services

Start PostgreSQL, Milvus (with etcd and minio), and Redis:

```bash
docker-compose up -d
```

Wait for services to be ready (about 30 seconds).

### 5. Initialize Database

Create PostgreSQL tables:

```bash
python init_db.py
```

### 6. Run Application

Start Chainlit demo:

```bash
chainlit run app.py
```

Open browser to `http://localhost:8000`

---

## 📖 Usage

### Basic Workflow

1. **Start the application** (see Setup above)
2. **Open Chainlit interface** at `http://localhost:8000`
3. **Send a message** - The system will:
   - Analyze your intent
   - Check if handoff is needed
   - Route to sales workflow if appropriate
   - Generate a response
   - Validate content
   - Store in memory

### Debug Mode

Set `DEBUG=true` in `.env` to see:
- Agent outputs in console
- Memory operations
- Database operations
- Flow debugging information

### Memory Management

- **Short-term**: Stored in Redis (last 20-50 messages)
- **Episodic**: Older messages moved to PostgreSQL
- **Semantic**: Important messages indexed in Milvus
- **Summary**: Generated every 50 messages

### Agent Integration

Agents can be used independently or as part of the workflow:

```python
from agents import IntentAgent, SalesAgent, GuardrailAgent

# Use agents independently
intent_agent = IntentAgent()
result = await intent_agent.run(input_data)
```

---

## 📁 Project Structure

```
project-100-fr/
├── agents/                      # Agent implementations
│   ├── intent_agent.py         # Intent extraction
│   ├── analyse_handoff_agent.py # Handoff analysis
│   ├── orchestrator_agent.py   # Task orchestration
│   ├── predict_requirement_agent.py  # Requirement prediction
│   ├── classify_step_agent.py  # Step classification
│   ├── profile_agent.py        # Customer profiling
│   ├── up_sales_cross_sales_agent.py  # Product recommendation
│   ├── sales_agent.py          # Sales conversation
│   ├── guardrail_agent.py     # Content validation
│   ├── summary_agent.py        # Conversation summarization
│   ├── base_agent.py          # Base agent class
│   └── models.py              # Pydantic models
│
├── workflow/                   # Workflow orchestration
│   ├── orchestrator.py        # Main workflow orchestrator
│   ├── memory_manager.py      # Memory management
│   └── debug.py               # Debug utilities
│
├── database/                   # Database connections
│   ├── connection.py          # Database manager
│   ├── debug.py               # Database debug utilities
│   ├── postgres/              # PostgreSQL
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── schema.py          # Schema management
│   │   ├── client.py          # Connection client
│   │   └── session_service.py # Session services
│   ├── redis/                 # Redis
│   │   ├── models.py          # Redis models
│   │   ├── schema.py          # Redis schema
│   │   └── client.py          # Redis client
│   └── milvus/                # Milvus vector DB
│       ├── models.py          # Milvus models
│       ├── schema.py          # Collection schema
│       └── client.py          # Milvus client
│
├── tests/                      # Test suite
│   ├── test_agents.py
│   └── test_database.py
│
├── app.py                      # Chainlit application
├── init_db.py                  # Database initialization
├── docker-compose.yml          # Docker services
├── pyproject.toml              # Project configuration
└── README.md                   # This file
```

---

## 🔧 Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
ruff check .
```

### Debug Mode

Enable debug output by setting `DEBUG=true` in `.env`. This will show:
- Agent execution results
- Memory operations
- Database queries
- Flow debugging

---

## 📝 Notes

- All agents use **Gemini 2.5 Flash** model by default
- Memory uses **sliding window** mechanism (moves old messages to PostgreSQL)
- **Guardrail** ensures content compliance before storage
- **Parallel execution** for Intent and Handoff agents for efficiency
- **Vietnamese language** support (default)

---

## 🤝 Contributing

Contributions are welcome! Please ensure:
- Code follows existing patterns
- Tests are added for new features
- Documentation is updated
- Code is formatted with black and ruff

---

## 📄 License

[Your License Here]

---

## 🙏 Acknowledgments

- Built with [PydanticAI](https://github.com/pydantic/pydantic-ai)
- UI powered by [Chainlit](https://chainlit.io)
- Vector search with [Milvus](https://milvus.io)
