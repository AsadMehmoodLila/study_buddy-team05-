## Deployment & Execution Guide

Follow this step-by-step guide to configure, install dependencies, and launch the Study Buddy application on your local environment.

### Prerequisites
Ensure that you have **Python 3.8+** installed on your system before proceeding.

### Step-by-Step Installation

**Step 1: Navigate to the Project Directory**
Open your terminal (or command prompt) and change the directory to the root folder of the extracted project:
```bash
cd path/to/study-buddy
```

**Step 2: Initialize a Virtual Environment**
To prevent dependency conflicts, it is highly recommended to isolate the project within a virtual environment:
```bash
python -m venv .venv
```

**Step 3: Activate the Virtual Environment**
Run the appropriate activation command based on your operating system:

**Windows:**
```bash
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

**Step 4: Install Project Dependencies**
With the virtual environment active, install all required Python packages listed in the requirements file:
```bash
pip install -r requirements.txt
```

**Step 5: Configure Environment Variables**
This project relies on environment variables to securely manage API keys.

Locate the .env.example file in the root directory.

Duplicate this file and rename the copy to strictly .env.

Open the .env file and populate the variables with your active credentials:

```Plaintext
OPENROUTER_API_KEY=your_actual_api_key_here
OPENROUTER_MODEL=openrouter/free
```

**Step 6: Launch the Application**
Start the Streamlit server to boot up the application interface:

```bash
streamlit run app.py
```