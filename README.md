# ThermaBrain

### ThermaBrain is live on https://thermabrain.onrender.com

ThermaBrain is a cold-chain logistics assistant with separate workspaces for **Fleet / Logistics Managers** and **Truck Drivers**. It combines SQL-based shipment telemetry, SOP retrieval, an LLM agent workflow, and optional Gnani speech input/output in a Streamlit application.

## What the application includes

### Fleet / Logistics Manager
- Chat interface for asking questions about fleet telemetry, incidents, routes, and compliance.
- LangGraph agent with tools for querying the fleet SQL view, retrieving weather information for supplied coordinates, and searching SOP content in Pinecone.
- Displays tool-call inputs and raw tool outputs in the manager workspace.

### Truck Driver
- Simplified driver chat workspace.
- Requires the driver to enter a vehicle ID before sending a question.
- Uses a fixed, parameterized SQL query to retrieve up to 10 latest telemetry rows for that vehicle from `FDE_VIEWS.VW_ACTIVE_FLEET`.
- Uses the SOP retrieval tool for safety and cargo-handling guidance.
- Hides raw tool traces from the driver-facing chat.

### Security & Audit Logs
- Includes an audit-log viewer that checks the admin username and password configured in `.env` before querying `FDE_VIEWS.AgentAuditLog`.
- The application attempts to write agent and tool activity to that table.

### Voice interaction
- Optional Gnani speech-to-text using the configured Prisma model.
- Optional text-to-speech using the configured Timbre model.
- The UI exposes language selection and a speak-reply toggle.

## Architecture

```text
                 Streamlit application
             /            |             \
      Manager UI       Driver UI     Audit viewer
           |               |
       Manager agent   Driver agent
           |               |
           +------ LangGraph ------+
                         |
       +-----------------+------------------+
       |                 |                  |
   SQL telemetry     Pinecone SOP       Weather API
       |              retrieval          (Open-Meteo)
       +-----------------+------------------+
                         |
                   LLM response

       Optional Gnani STT / TTS for voice interaction
```

The manager and driver agents use separate tool lists and role-specific system prompts. The driver agent does not receive the unrestricted fleet SQL tool; it receives the fixed vehicle-specific telemetry tool instead.

## Repository structure

```text
ThermaBrain/
├── data/
│   ├── cache/                 # SOP ingestion hash caches
│   ├── policy/                # SOP and policy source documents
│   └── raw/                   # Included logistics datasets and notebook
├── scripts/
│   ├── ingest_legacy_data.py  # Loads the CSV into SQL Server
│   ├── setup_security.sql     # Creates the semantic view and read-only SQL login
│   ├── ingest_sop_pinecone.py # Parses policy files and indexes them in Pinecone
│   └── ingest.py              # Additional SOP ingestion script
├── src/
│   ├── agent.py               # Manager and driver LangGraph agents
│   ├── agent_tools.py         # SQL, weather, and SOP retrieval tools
│   ├── sql_guard.py           # Restricts manager SQL to SELECT on the fleet view
│   ├── stream_ui.py           # Streamlit application
│   ├── prompts/               # Role-specific agent instructions
│   └── voice/                 # Gnani client and voice response helpers
└── requirements.txt
```

## Requirements

- Python 3.12 (the supplied `requirements.txt` was prepared with Python 3.12.13).
- SQL Server with the Microsoft ODBC Driver 18 for SQL Server installed.
- A reachable Pinecone project and API key.
- An LLM provider configured for the selected agent mode. The default agent mode is local Ollama (`qwen2.5:7b`).
- Gnani API access is optional and is required only for voice features.

The source imports `langchain-google-genai` directly, although it is not listed in the supplied `requirements.txt`. Install it before starting the app. The SOP ingestion script also imports `langchain-text-splitters`.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install langchain-google-genai langchain-text-splitters
```

## Environment configuration

Create a `.env` file in the project root. Add only the credentials for the services and modes you intend to use.

```dotenv
# SQL Server
SQL_SERVER_HOST=localhost
SQL_SERVER_PORT=1433
SQL_AGENT_USER=USR_FDE_RO
SQL_AGENT_PASSWORD=your_read_only_sql_password
SQL_ADMIN_USER=your_sql_admin_username
SQL_ADMIN_PASSWORD=your_sql_admin_password

# Pinecone
PINECONE_API_KEY=your_pinecone_api_key

# Agent model: OLLAMA (default), DEEPSEEK, or GEMINI
Agent_llm=OLLAMA
DEEPSEEK_API_KEY=your_deepseek_api_key
GOOGLE_API_KEY=your_google_ai_api_key

# Embeddings: LOCAL (default) or GEMINI
Embeddings_model=LOCAL
Local_Embedding_Model=BAAI/bge-m3

# Gnani voice (optional)
GNANI_API_KEY=your_gnani_api_key
GNANI_STT_MODEL=prisma-v3.0
GNANI_TTS_MODEL=timbre-v3.0
GNANI_TTS_VOICE=Shivani
```

## Data and database setup

The project includes `data/raw/cold_chain_delivery_trips.csv` and `data/raw/logistics.xlsx`. The SQL ingestion script specifically reads `cold_chain_delivery_trips.csv` and maps its columns into the legacy table `dbo.TBL_SC_FLEET_HIST_RAW`.

1. Configure SQL Server connection values in `.env` and ensure the SQL admin account can create/load the target table.
2. From the project root, load the included CSV:

   ```bash
   python scripts/ingest_legacy_data.py
   ```

3. Review `scripts/setup_security.sql` before running it in SQL Server Management Studio or an equivalent SQL client. It creates `FDE_VIEWS.VW_ACTIVE_FLEET` over the raw table and creates the `USR_FDE_RO` login/user with read access to the view.
4. **Important:** `setup_security.sql` contains a sample password in its `CREATE LOGIN` statement. Replace it with a strong password before execution and make the `SQL_AGENT_PASSWORD` value in `.env` match. Do not use the sample password in a deployed environment.

The application also attempts to insert records into `FDE_VIEWS.AgentAuditLog`, and the audit viewer reads from that table. The included `setup_security.sql` does **not** create `AgentAuditLog`; create that table separately with an appropriate schema and permissions if you want audit logging to work. If it is absent, audit writes fail and are printed to the application console.

## SOP ingestion into Pinecone

The policy directory contains the supplied SOP/reference files:

- `data/policy/Temperature.pdf`
- `data/policy/Cargo.pdf`
- `data/policy/Cold_chain_sop.md`

The ingestion script scans `data/policy/` for `.md`, `.txt`, `.pdf`, `.csv`, and `.xlsx` files, extracts text/rows, splits content into chunks, and upserts the chunks into Pinecone. Configure `PINECONE_API_KEY` and the Google AI API key, then run:

```bash
python scripts/ingest_sop_pinecone.py
```

The script creates or reuses the Gemini SOP index and maintains a hash cache under `data/cache/` to skip unchanged files.

## Run the application

From the project root:

```bash
streamlit run src/stream_ui.py
```

Choose one of the workspaces in the sidebar:

- **Fleet / Logistics Manager** for fleet-level queries and visible tool traces.
- **Truck Driver** for vehicle-specific telemetry lookup and driver-oriented guidance.
- **Security & Audit Logs** for the admin-gated audit viewer (requires the audit table described above).

For driver telemetry queries, enter the vehicle ID in the driver workspace. The current implementation does not authenticate a driver or verify that the entered vehicle ID is assigned to that person.

## Important scope and limitations

- The included logistics files are static datasets. The driver telemetry tool queries the latest rows available in SQL Server; it is not a live IoT streaming connection.
- The driver enters a vehicle ID manually. The current UI does not implement driver login or a verified driver-to-vehicle assignment.
- The workspace selector is a UI choice, not production role-based authentication or authorization. Do not expose this prototype publicly without adding server-side identity and access controls.
- The corridor tool requests current weather from Open-Meteo for coordinates supplied to it. Its corridor-risk/congestion label is a simple value derived from wind speed in the code; it is not a live traffic or road-congestion feed.
- SOP answers depend on the documents successfully indexed in the configured Pinecone index. Keep the ingestion embedding configuration consistent with the application configuration.
- Gnani voice features remain unavailable until a valid `GNANI_API_KEY` is configured and the external service can be reached.
- The project is a prototype and its generated guidance should not replace dispatch procedures, approved SOPs, or emergency services.

## License

No license file is included in this project archive. Add a license file if you intend to publish or distribute the project under a specific license.
