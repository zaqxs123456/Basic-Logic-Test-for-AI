# Basic Logic Test for AI

A framework for testing logical reasoning capabilities of various LLM models using Ollama. This tool runs logical reasoning questions, evaluates responses, and generates comparative performance tables.

## AI Model Logical Reasoning Test Results

<!-- BEGIN_RESULTS_TABLE -->
<!-- END_RESULTS_TABLE -->

## All Questions

Click [here](questions.md) to view all questions and answers.

## Features

- Test multiple AI models on logical reasoning problems
- Automatic evaluation of answers using a reference model
- Multiple attempts per question with retry mechanism
- Response timeout handling to prevent hanging
- Detailed performance tracking and statistics
- Generates markdown-based results table for easy comparison

## Requirements

- Python 3.7+
- [Ollama](https://ollama.ai/) installed and running
- Required Python packages (see requirements.txt)

## Installation

1. Clone this repository
2. (Optional) Create a virtual environment:

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```
3. Install required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

3. Ensure Ollama is installed and running

## Usage

### Basic Usage

Test a single model:

```bash
python run_test.py llama3.2
```

### Multiple Models

Test multiple models in sequence:

```bash
python run_test.py llama3.2 gemma3 phi4 mistral-nemo
```

### Additional Options

```bash
python run_test.py <models> [options]

Options:
  --evaluator MODEL    Specify the model for answer evaluation (default: gemma3:27b)
  --max-attempts N     Maximum attempts per question (default: 5)
  --timeout SECONDS    Timeout in seconds per response (default: 60)
  --no-table          Skip generating the results table
```

### Examples

```bash
# Test phi3 with increased timeout
python run_test.py phi3 --timeout 120

# Test mistral and mpt with fewer attempts
python run_test.py mistral mpt --max-attempts 3

# Use a different evaluator model
python run_test.py llama3 --evaluator claude
```

## Understanding Results

Results are saved in two formats:

1. **JSON result files** - Stored in the `results/` directory with timestamps
2. **Results table** - Generated as `results_table.md` after tests complete

The results table provides a quick visual overview of model performance:
- ✅ 5/5 - Correct answer with max score
- ✅ 5/5(3) - Correct answer with max score, took 3 attempts
- ❌ 0/5(5) - Failed to answer correctly after all attempts

## Project Structure

- `run_test.py` - Main script for running tests
- `generate_results_table.py` - Creates the comparative results table
- `questions.json` - Test configuration file
- `questions/` - Directory containing question files
- `answers/` - Directory containing model answer files
- `results/` - Directory where test results are stored

## License

[MIT License](LICENSE)