import argparse
import json
import os
from tqdm import tqdm
from ollama import generate, ps, pull
import time
import sys
import signal
from contextlib import contextmanager
import threading

# Import table generation functionality
try:
    from generate_results_table import generate_table
except ImportError as e:
    print(f"Warning: Could not import table generation module: {e}")
    generate_table = None

class TimeoutException(Exception):
    """Exception raised when a function times out"""
    pass

@contextmanager
def time_limit(seconds):
    """Context manager for limiting execution time of a block of code"""
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    
    # Not all platforms support SIGALRM (e.g., Windows)
    if hasattr(signal, 'SIGALRM'):
        # Set the timeout handler
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)  # Disable the alarm
    else:
        # Alternative implementation for platforms without SIGALRM
        timer = threading.Timer(seconds, lambda: sys.exit("Timeout occurred"))
        timer.start()
        try:
            yield
        finally:
            timer.cancel()

def check_model_exists(model_name):
    """Check if a model exists in Ollama"""
    response = ps()
    for model in response.models:
        if model.model.startswith(model_name):
            return True
    return False

def pull_model_with_progress(model_name):
    """Pull a model with progress bar"""
    print(f"Pulling {model_name}...")
    current_digest, bars = '', {}
    for progress in pull(model_name, stream=True):
        digest = progress.get('digest', '')
        if digest != current_digest and current_digest in bars:
            bars[current_digest].close()

        if not digest:
            print(progress.get('status'))
            continue

        if digest not in bars and (total := progress.get('total')):
            bars[digest] = tqdm(total=total, desc=f'pulling {digest[7:19]}', unit='B', unit_scale=True)

        if completed := progress.get('completed'):
            bars[digest].update(completed - bars[digest].n)

        current_digest = digest
    print(f"{model_name} ready")

def load_questions(file_path):
    """Load questions from json file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def read_file_content(file_path):
    """Read content from a file"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_path, file_path)
    with open(full_path, 'r') as f:
        return f.read()

def ask_question(model, question_content, timeout_seconds=60, is_evaluator=False):
    """Ask a question to the model with timeout (only for test models)"""
    try:
        # For evaluator models, don't apply timeout
        if is_evaluator:
            response = generate(
                model=model,
                prompt=question_content,
                options={"num_ctx": 8192}
            )
            return response['response']
        
        # For test models, apply timeout
        with time_limit(timeout_seconds):
            response = generate(
                model=model,
                prompt=question_content,
                options={"num_ctx": 8192}
            )
            return response['response']
    
    except TimeoutException:
        print(f"\n⏱️ Model response timed out after {timeout_seconds} seconds!")
        return f"[TIMEOUT ERROR: The model did not respond within {timeout_seconds} seconds]"
    except Exception as e:
        print(f"\n❌ Error getting model response: {str(e)}")
        return f"[ERROR: {str(e)}]"

def evaluate_answer(evaluator_model, user_answer, model_answer, question):
    """Have Gemma3 evaluate the answer"""
    prompt = f"""
You are evaluating an AI's answer to a question. DO NOT answer the question yourself.
Your job is ONLY to check if the AI's answer reasonably matches the model answer.

Question:
{question}

Model Answer:
{model_answer}

AI's Answer:
{user_answer}

First determine if the answer is CORRECT or WRONG:
- WRONG (score 0): The answer is fundamentally incorrect or misses the point
- CORRECT (score 1-5): The answer has the right idea

For scoring:
- If WRONG, the score must be 0
- If CORRECT, score from 1-5 based on quality and completeness
- For multiple choice questions, only use scores 0 (WRONG) or 5 (CORRECT)

Return your response in this format:
Assessment: [CORRECT or WRONG]
Score: [0-5]
Explanation: [Your brief explanation]
"""
    
    # Use ask_question with is_evaluator=True to bypass timeout
    return ask_question(evaluator_model, prompt, is_evaluator=True)

def get_difficulty_stars(difficulty_level):
    """Convert difficulty level to star emojis"""
    try:
        level = int(difficulty_level)
        return "⭐" * level
    except (ValueError, TypeError):
        return "⭐"  # Default to one star if conversion fails

def parse_evaluation(evaluation):
    """Parse evaluation text to extract assessment and score"""
    assessment = "wrong"  # Default - use lowercase
    score = 0  # Default
    
    try:
        # Extract assessment (correct/wrong)
        assessment_line = [line for line in evaluation.split('\n') if line.startswith('Assessment:')]
        if assessment_line:
            raw_assessment = assessment_line[0].split(':')[1].strip().lower()
            # Handle the "WONG" case too (yes, this actually happens)
            if raw_assessment in ("wong", "wrong"):
                assessment = "wrong"
            elif raw_assessment == "correct":
                assessment = "correct"
            else:
                print(f"⚠️ Unknown assessment: '{raw_assessment}', defaulting to 'wrong'")
                assessment = "wrong"
        
        # Extract score
        score_line = [line for line in evaluation.split('\n') if line.startswith('Score:')]
        if score_line:
            score = int(score_line[0].split(':')[1].strip())
            
        # Validate scores - use lowercase assessment
        if assessment == "wrong" and score != 0:
            print("⚠️ Warning: Inconsistent evaluation (wrong but score > 0). Setting score to 0.")
            score = 0
            
        if assessment == "correct" and score == 0:
            print("⚠️ Warning: Inconsistent evaluation (correct but score = 0). Setting score to 1.")
            score = 1
    
    except (IndexError, ValueError) as e:
        print(f"⚠️ Couldn't parse evaluation: {e}. Defaulting to wrong (0)")
    
    return assessment, score

def process_question_attempt(test_model, evaluator_model, question_content, model_answer_content, attempt_num=1, timeout_seconds=60):
    """Process a single attempt at answering a question"""
    print(f"\n📝 {f'Attempt {attempt_num}/5' if attempt_num > 1 else 'First attempt'}")
    
    # Ask the question with timeout for test model
    print(f"⏳ Asking {test_model}... (timeout: {timeout_seconds}s)")
    user_answer = ask_question(test_model, question_content, timeout_seconds=timeout_seconds)
    
    # Check if it was a timeout
    if user_answer.startswith("[TIMEOUT ERROR:"):
        print("⏱️ Response timed out - will be treated as incorrect")
    else:
        print(f"\n📢 {test_model}'s answer:\n{user_answer}\n")
    
    # Evaluate the answer - use is_evaluator=True for the evaluator model
    print(f"⚖️ Evaluating with {evaluator_model}...")
    evaluation = evaluate_answer(
        evaluator_model,
        user_answer,
        model_answer_content,
        question_content
    )
    
    # Parse the evaluation
    assessment, score = parse_evaluation(evaluation)
    
    # For timeout or error responses, force "wrong" assessment
    if user_answer.startswith("[TIMEOUT ERROR:") or user_answer.startswith("[ERROR:"):
        assessment = "wrong"
        score = 0
        print("⚠️ Timeout or error occurred - forcing incorrect assessment")
    
    # Display results - use lowercase assessment
    result_emoji = "✅" if assessment == "correct" else "❌"
    print(f"\n{result_emoji} Assessment: {assessment}")
    print(f"🏅 Score: {score}/5 {get_difficulty_stars(score)}")
    print(f"📊 Evaluation:\n{evaluation}")
    
    return {
        "answer": user_answer,
        "evaluation": evaluation,
        "assessment": assessment,  # Already lowercase from parse_evaluation
        "score": score
    }

def handle_question(test_model, evaluator_model, question_data, q_index, total_questions, max_attempts=5, timeout_seconds=60):
    """Handle the full process of asking and evaluating a question, with retries if needed"""
    question_path = question_data["question_path"]
    answer_path = question_data["answer_path"]
    short_name = question_data.get("short_name", f"Q{q_index}")
    
    print(f"\n{'='*80}")
    print(f"📝 Question {q_index}/{total_questions}: {short_name}")
    
    # Print difficulty info
    human_difficulty = question_data.get("human_difficulty", "N/A")
    ai_difficulty = question_data.get("ai_difficulty", "N/A")
    human_difficulty_stars = get_difficulty_stars(human_difficulty)
    ai_difficulty_stars = get_difficulty_stars(ai_difficulty)
    
    print(f"👤 Human difficulty: {human_difficulty}/5 {human_difficulty_stars}")
    print(f"🤖 AI difficulty: {ai_difficulty}/5 {ai_difficulty_stars}")
    
    # Load question and answer content
    question_content = read_file_content(question_path)
    model_answer_content = read_file_content(answer_path)
    print("❓ Question:", question_content.split("\n")[0])  # Print only the first line
    
    # Initialize result tracking
    test_subject_answers = []
    evaluations = []
    scores = []
    assessments = []
    attempts = 0
    success = False
    attempts_until_success = None
    
    # First attempt with timeout
    result = process_question_attempt(test_model, evaluator_model, question_content, model_answer_content, 
                                     timeout_seconds=timeout_seconds)
    
    # Record results
    test_subject_answers.append(result["answer"])
    evaluations.append(result["evaluation"])
    scores.append(result["score"])
    assessments.append(result["assessment"])
    attempts = 1
    
    # Check if successful on first try - use lowercase assessment
    if result["assessment"] == "correct":
        success = True
        attempts_until_success = 1
        print("✅ Success on first attempt!")
    else:
        print("❌ Incorrect. Will retry later.")
    
    # Retry logic with timeout (only retry if max_attempts > 1 and first attempt failed)
    if max_attempts > 1 and not success:
        print(f"\n🔄 Retrying Question {q_index}")
        
        # Try additional attempts with timeout
        for attempt in range(2, max_attempts + 1):
            result = process_question_attempt(
                test_model, 
                evaluator_model, 
                question_content, 
                model_answer_content,
                attempt,
                timeout_seconds=timeout_seconds
            )
            
            # Record results
            test_subject_answers.append(result["answer"])
            evaluations.append(result["evaluation"])
            scores.append(result["score"])
            assessments.append(result["assessment"])
            attempts = attempt
            
            # Check if successful - use lowercase assessment
            if result["assessment"] == "correct":
                success = True
                attempts_until_success = attempt
                print(f"✅ Success on attempt {attempts_until_success}!")
                break
            else:
                print(f"❌ Still incorrect. {'Trying again...' if attempt < max_attempts else 'No more attempts.'}")
    
    # Find best score
    best_score = max(scores) if scores else 0
    
    # Create final result object - use lowercase for setting assessment
    final_result = {
        "question_index": q_index,
        "question_path": question_path,
        "answer_path": answer_path,
        "short_name": short_name,
        "test_subject_answers": test_subject_answers,
        "evaluations": evaluations,
        "scores": scores,
        "attempts": attempts,
        "attempts_until_success": attempts_until_success,
        "assessment": "correct" if success else "wrong",  # Use lowercase
        "best_score": best_score
    }
    
    return final_result

def run_test(test_model, evaluator_model, max_attempts=5, timeout_seconds=60):
    """Run the test with questions from json file"""
    questions = load_questions("questions.json")
    results = []
    
    print(f"\n🧠 Running test with {test_model}, evaluated by {evaluator_model} 🧠\n")
    
    # Process each question
    for i, q in enumerate(questions, 1):
        # Prepare question data dictionary with all needed fields
        question_data = {
            "question_path": q["question"],
            "answer_path": q["answer"],
            "short_name": q.get("short_name", f"Q{i}"),
            "human_difficulty": q.get("human_difficulty", "3"),
            "ai_difficulty": q.get("ai_difficulty", "3")
        }
        
        # Handle the question (ask, evaluate, retry if needed)
        result = handle_question(
            test_model, 
            evaluator_model, 
            question_data, 
            i, 
            len(questions),
            max_attempts,
            timeout_seconds
        )
        
        results.append(result)
    
    # Calculate statistics based on best attempts - use lowercase assessment
    best_scores = [r["best_score"] for r in results]
    total_score = sum(best_scores)
    max_score = 5 * len(results)
    correct_count = sum(1 for r in results if r["assessment"] == "correct")
    total_attempts = sum(r["attempts"] for r in results)
    
    percentage = (total_score / max_score) * 100
    correct_percentage = (correct_count / len(questions)) * 100
    
    print(f"\n{'='*80}")
    print(f"\n🎯 Final Results for {test_model} (Best of {max_attempts} attempts):")
    print(f"📊 Correct answers: {correct_count}/{len(questions)} ({correct_percentage:.1f}%)")
    print(f"🏅 Final Score: {total_score}/{max_score} ({percentage:.1f}%) {get_difficulty_stars(round(percentage/20))}")
    print(f"🔄 Total attempts: {total_attempts} (avg: {total_attempts/len(questions):.1f} per question)")
    
    # Create metadata
    metadata = {
        "test_model": test_model,
        "evaluator_model": evaluator_model,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_score": total_score,
        "max_possible_score": max_score,
        "score_percentage": percentage,
        "correct_answers": correct_count,
        "total_questions": len(questions),
        "correct_percentage": correct_percentage,
        "total_attempts": total_attempts,
        "avg_attempts": total_attempts / len(questions),
        "max_attempts_allowed": max_attempts
    }
    
    return results, metadata

def main():
    parser = argparse.ArgumentParser(description='Run Basic Logic Test for AI')
    parser.add_argument('test_models', nargs='+', help='One or more models to test (e.g. llama3 gemma3 phi3)')
    parser.add_argument('--evaluator', default='gemma3:27b', help='The model to evaluate answers (default: gemma3:27b)')
    parser.add_argument('--no-table', action='store_true', help='Skip generating results table')
    parser.add_argument('--max-attempts', type=int, default=5, help='Maximum attempts per question (default: 5)')
    parser.add_argument('--timeout', type=int, default=60, help='Timeout in seconds for each model response (default: 60)')
    args = parser.parse_args()
    
    # Check if evaluator model exists, pull if not
    if not check_model_exists(args.evaluator):
        pull_model_with_progress(args.evaluator)
    else:
        print(f"✓ {args.evaluator} model already exists")
    
    # Process each test model sequentially
    for test_model in args.test_models:
        print(f"\n\n{'='*80}")
        print(f"🚀 Starting test for model: {test_model}")
        print(f"{'='*80}\n")
        
        # Check if current test model exists, pull if not
        if not check_model_exists(test_model):
            pull_model_with_progress(test_model)
        else:
            print(f"✓ {test_model} model already exists")
        
        # Run test for current model (pass timeout)
        results, metadata = run_test(test_model, args.evaluator, args.max_attempts, args.timeout)
        
        # Save results to dedicated folder
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)
        results_file = f"{results_dir}/results_{test_model}_{timestamp}.json"
        
        # Combine results and metadata
        final_results = {
            "metadata": metadata,
            "results": results
        }
        
        with open(results_file, 'w') as f:
            json.dump(final_results, f, indent=2)
        
        print(f"\n💾 Results saved to {results_file}")
        
        print(f"\n{'='*80}")
        print(f"✅ Test completed for model: {test_model}")
        print(f"{'='*80}")
    
    # Generate results table after all tests are complete
    if not args.no_table and generate_table is not None:
        try:
            print("\n📊 Generating updated results table...")
            table_content = generate_table()
            
            if table_content:
                with open("results_table.md", "w") as f:
                    f.write(table_content)
                print("✅ Results table updated successfully")
            else:
                print("❌ Failed to generate results table")
        except Exception as e:
            print(f"❌ Error generating results table: {e}")
    
    print("\n🏁 All models have been tested successfully! 🏁")

if __name__ == "__main__":
    main()