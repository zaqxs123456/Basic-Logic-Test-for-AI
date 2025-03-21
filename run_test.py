import argparse
import json
import os
from tqdm import tqdm
from ollama import generate, list, pull
import time
import sys
import signal
from contextlib import contextmanager
import threading
import re
import subprocess

# Import table generation functionality
try:
    from generate_results_table import generate_table, update_readme_with_table
except ImportError as e:
    print(f"Warning: Could not import table generation module: {e}")
    generate_table = None
    update_readme_with_table = None

def strip_thinking(response, thinking_start_tag, thinking_end_tag):
    """Remove thinking section from response if tags are provided"""
    if not thinking_start_tag or not thinking_end_tag or not response:
        return response
    
    try:
        # Create pattern to match content between tags (including the tags)
        pattern = re.compile(f'{re.escape(thinking_start_tag)}.*?{re.escape(thinking_end_tag)}', 
                             re.DOTALL)
        
        # Replace the matched content with empty string
        stripped_response = pattern.sub('', response)
        
        # Clean up any resulting double newlines
        stripped_response = re.sub(r'\n{3,}', '\n\n', stripped_response)
        
        return stripped_response.strip()
    except Exception as e:
        print(f"⚠️ Error stripping thinking section: {str(e)}")
        return response

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
    response = list()
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

def ask_question(model, question_content, timeout_seconds=60, is_evaluator=False, system_prompt=None, thinking_start_tag=None, thinking_end_tag=None):
    """Ask a question to the model with timeout (only for test models)"""
    try:
        # Set up options dictionary (only for context size and performance parameters)
        options = {"num_ctx": 4096}
        
        # For evaluator models, don't apply timeout
        if is_evaluator:
            response = generate(
                model=model,
                prompt=question_content,
                options=options,
                keep_alive=False
            )
            return response['response']
        
        # For test models, apply timeout and system prompt if provided
        with time_limit(timeout_seconds):
            response = generate(
                model=model,
                prompt=question_content,
                system=system_prompt if system_prompt else "",  # Pass system as direct parameter
                options=options,
                keep_alive=False
            )
            
            # Strip thinking section if tags are provided
            answer = strip_thinking(response['response'], thinking_start_tag, thinking_end_tag)
            return answer
    
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

First determine if the answer is Correct or Wrong:
- Wrong (score 0): The answer is fundamentally incorrect or misses the point
- Correct (score 1-5): The answer has the right idea

For scoring:
- If Wrong, the score must be 0
- If Correct, score from 1-5 based on quality and completeness
- For multiple choice questions, only use scores 0 (Wrong) or 5 (Correct)

Return your response in this exact JSON format:
{{
  "explanation": "Your brief explanation here",
  "mc_chosen_by_the_LLM_model": "A/B/C/D",  # Only include this for multiple choice questions, options: A, B, C, D.
  "assessment": "Correct or Wrong", # only these two options are allowed, no typos or extra characters. If is multiple choice question, make sure the LLM model's choice is same with the model answer if you want to mark it as correct.
  "score": 0-5 (just the number)
}}

Do not include any other text, Markdown formatting, or code blocks.
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
        # Try parsing as JSON first
        try:
            import json
            # Check if this might be a JSON response
            if '{' in evaluation and '}' in evaluation:
                # Extract potential JSON section (between first { and last })
                json_section = evaluation[evaluation.find('{'):evaluation.rfind('}')+1]
                eval_data = json.loads(json_section)
                
                # Extract assessment and score from JSON
                if 'assessment' in eval_data:
                    # Extract only alphabet characters and lowercase
                    raw_assessment = ''.join(c for c in eval_data['assessment'] if c.isalpha()).lower()
                    if raw_assessment in ('correct', 'right', 'true', 'yes'):
                        assessment = "correct"
                    elif raw_assessment in ('wrong', 'incorrect', 'false', 'no', 'wong'):
                        assessment = "wrong"
                
                if 'score' in eval_data:
                    score = int(eval_data['score'])
                
                # Skip further processing if JSON was parsed successfully
                if assessment and score is not None:
                    return assessment, score
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            # If JSON parsing fails, continue with text-based parsing
            pass
            
        # Fall back to text-based parsing
        # Extract assessment (correct/wrong)
        assessment_line = [line for line in evaluation.split('\n') if line.startswith('Assessment:')]
        if assessment_line:
            raw_text = assessment_line[0].split(':')[1].strip()
            # Extract only alphabetic characters and convert to lowercase
            raw_assessment = ''.join(c for c in raw_text if c.isalpha()).lower()
            
            # Expanded list of matching terms
            if raw_assessment in ("wong", "wrong", "incorrect", "false", "no"):
                assessment = "wrong"
            elif raw_assessment in ("correct", "right", "true", "yes"):
                assessment = "correct"
            else:
                print(f"⚠️ Unknown assessment: '{raw_text}' (cleaned: '{raw_assessment}'), defaulting to 'wrong'")
                assessment = "wrong"
        
        # Extract score
        score_line = [line for line in evaluation.split('\n') if line.startswith('Score:')]
        if score_line:
            try:
                # Extract digits only
                score_text = score_line[0].split(':')[1].strip()
                score_digits = ''.join(c for c in score_text if c.isdigit())
                if score_digits:
                    score = int(score_digits)
            except ValueError:
                print(f"⚠️ Could not parse score from: '{score_line[0]}', defaulting to 0")
                score = 0
            
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

def evaluate_with_double_check(evaluator1_model, evaluator2_model, user_answer, model_answer, question, max_retry=3):
    """Evaluate an answer using two evaluators for consensus"""
    print(f"⚖️ Double-evaluating with {evaluator1_model} and {evaluator2_model}...")
    
    for attempt in range(1, max_retry + 1):
        if attempt > 1:
            print(f"🔄 Retry #{attempt-1} for evaluation consensus...")
            
        # Get first evaluation
        evaluation1 = evaluate_answer(
            evaluator1_model,
            user_answer,
            model_answer,
            question
        )
        assessment1, score1 = parse_evaluation(evaluation1)
        
        # Get second evaluation
        evaluation2 = evaluate_answer(
            evaluator2_model,
            user_answer,
            model_answer,
            question
        )
        assessment2, score2 = parse_evaluation(evaluation2)
        
        # Check if assessments agree
        if assessment1 == assessment2:
            print(f"✅ Evaluators agree: {assessment1}")
            # Use the highest score
            final_score = max(score1, score2)
            print(f"📊 Using highest score: {final_score}/5")
            return {
                "evaluation": f"CONSENSUS:\n{evaluation1}\n\n---SECOND EVALUATOR---\n{evaluation2}",
                "assessment": assessment1,  # They're the same
                "score": final_score,
                "consensus": True
            }
        else:
            print(f"⚠️ Evaluators disagree: {evaluator1_model}={assessment1}, {evaluator2_model}={assessment2}")
            if attempt == max_retry:
                print(f"⚠️ After {max_retry} attempts, evaluators still disagree. Using first evaluator.")
                return {
                    "evaluation": f"NO CONSENSUS:\n{evaluation1}\n\n---SECOND EVALUATOR---\n{evaluation2}",
                    "assessment": assessment1,  # Fall back to first evaluator
                    "score": score1,
                    "consensus": False
                }
    
    # Should not reach here, but just in case
    return {
        "evaluation": "ERROR: Evaluation loop exited unexpectedly",
        "assessment": "wrong",
        "score": 0,
        "consensus": False
    }

def process_question_attempt(test_model, evaluator1_model, evaluator2_model, question_content, model_answer_content, 
                             attempt_num=1, timeout_seconds=60, system_prompt=None, 
                             thinking_start_tag=None, thinking_end_tag=None):
    """Process a single attempt at answering a question"""
    print(f"\n📝 {f'Attempt {attempt_num}/5' if attempt_num > 1 else 'First attempt'}")
    
    # Ask the question with timeout for test model
    print(f"⏳ Asking {test_model}... (timeout: {timeout_seconds}s)")
    user_answer = ask_question(test_model, question_content, timeout_seconds=timeout_seconds, 
                             system_prompt=system_prompt, thinking_start_tag=thinking_start_tag, 
                             thinking_end_tag=thinking_end_tag)
    
    # Check if it was a timeout
    if user_answer.startswith("[TIMEOUT ERROR:"):
        print("⏱️ Response timed out - will be treated as incorrect")
    else:
        print(f"\n📢 {test_model}'s answer:\n{user_answer}\n")
    
    # For timeout or error responses, force "wrong" assessment
    if user_answer.startswith("[TIMEOUT ERROR:") or user_answer.startswith("[ERROR:"):
        print("⚠️ Timeout or error occurred - forcing incorrect assessment")
        return {
            "answer": user_answer,
            "evaluation": "[TIMEOUT/ERROR - No evaluation performed]",
            "assessment": "wrong",
            "score": 0,
            "consensus": True  # Mark as consensus to avoid retries
        }
    
    # Use double evaluation if second evaluator is provided
    if evaluator2_model:
        result = evaluate_with_double_check(
            evaluator1_model,
            evaluator2_model,
            user_answer,
            model_answer_content,
            question_content
        )
        result["answer"] = user_answer
    else:
        # Fall back to single evaluator if no second evaluator
        evaluation = evaluate_answer(
            evaluator1_model,
            user_answer,
            model_answer_content,
            question_content
        )
        
        # Parse the evaluation
        assessment, score = parse_evaluation(evaluation)
        
        result = {
            "answer": user_answer,
            "evaluation": evaluation,
            "assessment": assessment,
            "score": score,
            "consensus": True  # Mark as consensus since only one evaluator
        }
    
    # Display results
    result_emoji = "✅" if result["assessment"] == "correct" else "❌"
    consensus_icon = "🤝" if result.get("consensus", False) else "⚔️"
    print(f"\n{result_emoji} Assessment: {result['assessment']} {consensus_icon}")
    print(f"🏅 Score: {result['score']}/5 {get_difficulty_stars(result['score'])}")
    print(f"📊 Evaluation summary:\n{result['evaluation'].split('\n')[0]}...")
    
    return result

def handle_question(test_model, evaluator1_model, evaluator2_model, question_data, q_index, total_questions, 
                   max_attempts=5, timeout_seconds=60, system_prompt=None, 
                   thinking_start_tag=None, thinking_end_tag=None):
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
    is_timeout = False
    
    # Combined first attempt and retry logic in a single loop
    for attempt in range(1, max_attempts + 1):
        # Process the attempt
        result = process_question_attempt(
            test_model, 
            evaluator1_model, 
            evaluator2_model, 
            question_content, 
            model_answer_content,
            attempt,
            timeout_seconds=timeout_seconds,
            system_prompt=system_prompt,
            thinking_start_tag=thinking_start_tag,
            thinking_end_tag=thinking_end_tag
        )
        
        # Record results
        test_subject_answers.append(result["answer"])
        evaluations.append(result["evaluation"])
        scores.append(result["score"])
        assessments.append(result["assessment"])
        attempts = attempt
        
        # Check if successful
        if result["assessment"] == "correct":
            success = True
            attempts_until_success = attempt
            if attempt == 1:
                print("✅ Success on first attempt!")
            else:
                print(f"✅ Success on attempt {attempts_until_success}!")
            break
        
        # Check for timeout in the response
        is_timeout = result["answer"].startswith("[TIMEOUT ERROR:")
        if is_timeout:
            if attempt == 1:
                print("⏱️ First attempt timed out - skipping retries.")
            else:
                print("⏱️ Timeout occurred - stopping further attempts.")
            break
            
        # For unsuccessful attempts
        if attempt == 1:
            print("❌ Incorrect. Will retry later.")
        elif attempt < max_attempts:
            print(f"❌ Still incorrect. Trying again...")
        else:
            print(f"❌ Still incorrect. No more attempts.")
    
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
        "best_score": best_score,
        "timeout": is_timeout  # Add timeout flag
    }
    
    return final_result

def run_test(test_model, evaluator1_model, evaluator2_model=None, max_attempts=5, timeout_seconds=60, 
             system_prompt=None, display_name=None, thinking_start_tag=None, thinking_end_tag=None):
    """Run the test with questions from json file"""
    questions = load_questions("questions.json")
    results = []
    
    print(f"\n🧠 Running test with {test_model}, evaluated by {evaluator1_model}" + 
          (f" and {evaluator2_model}" if evaluator2_model else "") + " 🧠\n")
    
    if thinking_start_tag and thinking_end_tag:
        print(f"💭 Will strip thinking sections between '{thinking_start_tag}' and '{thinking_end_tag}'")
    
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
            evaluator1_model,
            evaluator2_model, 
            question_data, 
            i, 
            len(questions),
            max_attempts,
            timeout_seconds,
            system_prompt,
            thinking_start_tag,
            thinking_end_tag
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
    
    # Set display name for results if provided
    model_name = display_name if display_name else test_model
    
    # Create metadata
    metadata = {
        "test_model": test_model,  # Keep original model name
        "display_name": model_name,  # Add display name
        "evaluator1_model": evaluator1_model,
        "evaluator2_model": evaluator2_model,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_score": total_score,
        "max_possible_score": max_score,
        "score_percentage": percentage,
        "correct_answers": correct_count,
        "total_questions": len(questions),
        "correct_percentage": correct_percentage,
        "total_attempts": total_attempts,
        "avg_attempts": total_attempts / len(questions),
        "max_attempts_allowed": max_attempts,
        "system_prompt": system_prompt,  # Store system prompt used
        "thinking_tags_used": bool(thinking_start_tag and thinking_end_tag),  # Record if thinking tags were used
        "dual_evaluator_used": bool(evaluator2_model)  # Record if dual evaluation was used
    }
    
    return results, metadata, model_name

def get_model_link(model_name):
    """Ask user for a link or source to pull a missing model"""
    print(f"\n⚠️ Model '{model_name}' not found in Ollama.")
    print(f"Please provide a source to pull the model from (or enter 'skip' to exit):")
    print("Examples:")
    print("  - llama3 (pull from default library)")
    print("  - llama3:8b (specific size from default library)")
    print("  - https://huggingface.co/mistralai/Mistral-7B-v0.1 (HuggingFace URL)")
    print("  - skip (exit program)")
    
    while True:
        source = input(f"Source for {model_name}: ").strip()
        
        if not source:
            print("Please enter a valid source or 'skip'.")
            continue
            
        if source.lower() == 'skip':
            print(f"Skipping model {model_name}. Exiting program.")
            sys.exit(1)
            
        return source

def check_and_prepare_models(test_models, evaluator1, evaluator2=None):
    """Check if all required models exist and ask for links if they don't"""
    all_models = test_models.copy()
    if evaluator1:
        all_models.append(evaluator1)
    if evaluator2:
        all_models.append(evaluator2)
    
    # First check which models are missing
    missing_models = {}
    for model in all_models:
        if not check_model_exists(model):
            missing_models[model] = None
    
    # If any models are missing, ask for links
    if missing_models:
        print(f"\n🔍 Found {len(missing_models)} missing model(s) that need to be pulled:")
        for model in missing_models:
            print(f"  - {model}")
        
        print("\nYou need to provide sources for these models before testing can begin.")
        
        # Ask for links for each missing model
        for model in missing_models:
            source = get_model_link(model)
            missing_models[model] = source
        
        # Try to pull each missing model
        for model, source in missing_models.items():
            try:
                if source == model:
                    # If source is same as model name, use default pull
                    print(f"Pulling {model} from default library...")
                    pull_model_with_progress(model)
                else:
                    # Otherwise pull from provided source
                    print(f"Pulling {model} from {source}...")
                    pull_model_with_progress(source)
                    
                    # If model name is different from source, we need to tag it
                    if model != source and ":" not in source and "http" not in source:
                        print(f"Tagging {source} as {model}...")
                        subprocess.run(["ollama", "cp", source, model], check=True)
            except Exception as e:
                print(f"❌ Failed to pull model {model}: {str(e)}")
                print("Cannot proceed with testing without required models. Exiting.")
                sys.exit(1)
    else:
        print("✅ All required models are already available in Ollama.")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Run Basic Logic Test for AI')
    parser.add_argument('test_models', nargs='+', help='One or more models to test (e.g. llama3 gemma3 phi3)')
    parser.add_argument('--evaluator', '-e', default='deepseek-r1:14b', help='Primary evaluator model (default: deepseek-r1:14b)')
    parser.add_argument('--evaluator2', '-e2', default="mistral-small",help='Second evaluator model for consensus (default: mistral-small)')
    parser.add_argument('--no-table', '-n', action='store_true', help='Skip generating results table')
    parser.add_argument('--max-attempts', '-m', type=int, default=5, help='Maximum attempts per question (default: 5)')
    parser.add_argument('--timeout', '-t', type=int, default=60, help='Timeout in seconds for each model response (default: 60)')
    parser.add_argument('--system-prompt', '-s', help='System prompt to use for the test model')
    parser.add_argument('--display-name', '-d', help='Custom display name for the test model (default: model name)')
    parser.add_argument('--thinking-start-tag', '-ts', help='Tag marking the start of thinking section to remove')
    parser.add_argument('--thinking-end-tag', '-te', help='Tag marking the end of thinking section to remove')
    args = parser.parse_args()
    
    print("🔍 Checking for required models...")
    # Check for all models upfront and ask for links if any are missing
    check_and_prepare_models(args.test_models, args.evaluator, args.evaluator2)
    
    # Process each test model sequentially
    for test_model in args.test_models:
        print(f"\n\n{'='*80}")
        model_display = args.display_name if args.display_name else test_model
        print(f"🚀 Starting test for model: {model_display} ({test_model})")
        
        if args.evaluator2:
            print(f"⚖️ Using dual evaluator mode: {args.evaluator} + {args.evaluator2}")
            
        if args.system_prompt:
            print(f"📝 Using system prompt: {args.system_prompt}")
        if args.thinking_start_tag and args.thinking_end_tag:
            print(f"🧠 Will strip thinking sections between '{args.thinking_start_tag}' and '{args.thinking_end_tag}'")
        print(f"{'='*80}\n")
        
        # Run test for current model (pass all parameters)
        results, metadata, model_name = run_test(
            test_model, 
            args.evaluator,
            args.evaluator2,
            args.max_attempts, 
            args.timeout, 
            args.system_prompt, 
            args.display_name,
            args.thinking_start_tag,
            args.thinking_end_tag
        )
        
        # Save results to dedicated folder
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)
        
        # Use model_name (which could be display name if provided) for the filename
        results_file = f"{results_dir}/results_{model_name}_{timestamp}.json"
        
        # Combine results and metadata
        final_results = {
            "metadata": metadata,
            "results": results
        }
        
        with open(results_file, 'w') as f:
            json.dump(final_results, f, indent=2)
        
        print(f"\n💾 Results saved to {results_file}")
        
        print(f"\n{'='*80}")
        print(f"✅ Test completed for model: {model_name}")
        print(f"{'='*80}")
    
    # Generate results table after all tests are complete
    if not args.no_table:
        try:
            print("\n📊 Generating updated results table...")
            # Run the generate_results_table.py script as a subprocess
            result = subprocess.run([sys.executable, "generate_results_table.py"], 
                                    capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                print("✅ Results table generated successfully")
                for line in result.stdout.splitlines():
                    if line.startswith("✅"):
                        print(line)
            else:
                print("❌ Failed to generate results table")
                print(f"Error: {result.stderr}")
        except Exception as e:
            print(f"❌ Error generating results table: {e}")
    
    print("\n🏁 All models have been tested successfully! 🏁")

if __name__ == "__main__":
    main()