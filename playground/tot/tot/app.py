# Import libraries
import requests
import json
import random
import openai

# Define constants
openai.api_key = API_KEY

MAX_CANDIDATES = 5
MAX_STEPS = 5

# Define CoT prompts
cot_prompts = [
    "Personal information:\n",
    "Education:\n",
    "Work experience:\n",
    "Projects:\n",
    "Skills:\n"
]

# Define verdicts
verdicts = ["sure", "maybe", "impossible"]

# Define markdown template
md_template = """
# {personal_information}

## Education

{education}

## Work Experience

{work_experience}

## Projects

{projects}

## Skills

{skills}
"""

# Define ToT functions

# Generate candidates using CoT prompts
def generate_candidates(step, context):
    prompt = cot_prompts[step].format(**context)
    
    response = openai.Completion.create(
        engine="davinci-codex",
        prompt=prompt,
        max_tokens=128,
        n=1,
        stop=None,
        temperature=1,
    )

    print(response)
    output = response.choices[0].text
    candidates = output.split("\n\n")
    candidates = [c.strip() for c in candidates if c.strip()]
    candidates = candidates[:MAX_CANDIDATES]
    return candidates

# Evaluate candidates using verdicts
def evaluate_candidates(step, context, candidates):
    prompt = "Rate each candidate as sure/maybe/impossible with regard to reaching the final goal.\n"
    prompt += "\n".join([f"{i+1}. {c}" for i, c in enumerate(candidates)])
    prompt += "\n\n"
    response = requests.post(API_URL + "/generate", headers={"Authorization": API_KEY}, json={"prompt": prompt, "max_tokens": 32})
    output = response.json()["output"]
    ratings = output.split("\n")
    ratings = [r.strip() for r in ratings if r.strip()]
    ratings = ratings[:len(candidates)]
    return ratings

# Perform breadth-first search using ToT controller
def breadth_first_search(step, context):
    # Check termination condition
    if step == MAX_STEPS:
        return context
    # Generate candidates
    candidates = generate_candidates(step, context)
    # Evaluate candidates
    ratings = evaluate_candidates(step, context, candidates)
    # Loop over candidates
    for i in range(len(candidates)):
        # Check rating
        if ratings[i] == "sure":
            # Update context
            context[cot_prompts[step].split()[0][:-1]] = candidates[i]
            # Recurse to the next step
            result = breadth_first_search(step + 1, context)
            # Check result
            if result:
                return result
        elif ratings[i] == "maybe":
            # Update context
            context[cot_prompts[step].split()[0][:-1]] = candidates[i]
            # Recurse to the next step with a lower depth limit
            result = breadth_first_search(step + 1, context, depth - 1)
            # Check result
            if result:
                return result
        else:
            # Skip candidate
            continue
    # Return None if no solution found
    return None

# Display the final resume text using markdown
def display_resume(context):
    md = md_template.format(**context)
    print(md)

# Run ToT for resume writing task
context = {}
resume = breadth_first_search(0, context)
if resume:
    display_resume(resume)
else:
    print("No resume found.")