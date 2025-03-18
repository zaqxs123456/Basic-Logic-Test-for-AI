# Manual Testing Mode Guide

The manual testing mode allows you to evaluate online/cloud LLMs that cannot be run locally through Ollama. This guide explains how to use the manual testing script.

## Requirements

- Python 3.6+
- Access to the model you want to test (e.g., web interface, API)
- Local installation of Ollama (for the evaluator models only)

## Basic Usage

```bash
python run_test_manual.py --model-name "GPT-4" --evaluator mistral-small --evaluator2 phi3
```

## Command Line Arguments

- `--model-name` or `-m`: Name of the model being tested (required)
- `--evaluator` or `-e`: Primary evaluator model (default: deepseek-r1-jp:14b-8k)
- `--evaluator2` or `-e2`: Secondary evaluator model for consensus (default: mistral-small)
- `--attempts` or `-a`: Maximum attempts allowed per question (default: 5)
- `--no-table` or `-n`: Skip generating the results table

## How It Works

The script will:

1. Display each question for you to copy
2. Allow you to paste the model's response
3. Evaluate the response using the evaluator model(s)
4. Track results for generating statistics

## Instructions During Testing

1. When prompted with a question, copy it and paste it to your model
2. Copy the model's complete response
3. Paste the response back into the terminal
4. Type `END` on a new line to finish input
5. Type `SKIP` to skip an attempt or question
6. Follow prompts for saving results

## Tips

- You can choose specific questions to test instead of running all questions
- Results are saved after each question if you choose to
- You can interrupt the test at any time with Ctrl+C and save partial results
- The final results will be in the same format as automated tests and will appear in the results table

## Example Session

```
$ python run_test_manual.py --model-name "Claude-3-Opus" --evaluator phi3

================================================================================
🚀 Starting manual test for model: Claude-3-Opus
================================================================================

🧠 Running manual test for Claude-3-Opus, evaluated by phi3 🧠

📋 INSTRUCTIONS:
1. Copy each question and paste it to your model
2. Copy the model's response and paste it back here
3. Type 'END' on a new line after pasting the response
4. Type 'SKIP' to skip an attempt

Process all questions or specific ones? Enter question numbers separated by commas, or 'all': 1,3,5

Will process 3 questions: [1, 3, 5]

================================================================================
📝 Question 1/6: Lottery System
👤 Human difficulty: 4/5 ⭐⭐⭐⭐
🤖 AI difficulty: 1/5 ⭐

❓ QUESTION TO COPY:
----------------------------------------
A lottery system assigns each participant a number from 1 to N, where N is the total number of participants. One winning number W is selected at random.

The system has a special rule: the winner is the participant with number W, and if W is not assigned to any participant, the winner is the participant with the largest number less than W. If there are no participants with numbers less than W, the winner is the participant with the largest number.

Example 1:
- Participants: 1, 3, 5
- W = 2
- Winner: 1 (largest number less than W)

Example 2:
- Participants: 2, 4, 6
- W = 5
- Winner: 4 (largest number less than W)

Now, given participants with numbers [1, 4, 6, 8, 10] and W = 7, who is the winner?
----------------------------------------

📝 First attempt

🔍 Please paste the model's response below.
Type 'END' on a new line to finish, or 'SKIP' to skip this attempt:
