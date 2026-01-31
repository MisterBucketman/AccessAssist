import ollama
import json

model = "llama3"


def get_llm_response(website_data, user_query):
    prompt = f"""
    You are an accessibility assistant that chooses html components from the query that match the user's request. Analyze this website structure and select the appropriate components and their respective actions.

    WEBSITE STRUCTURE:
    {json.dumps(website_data['elements'], indent=2)}

    USER REQUEST: "{user_query}"

    Output JSON with:
    - "action_sequence": List of action objects with:
        • "action": "click" | "fill" | "navigate"
        • "target": select elements from website structure which align with user request
        • "value": text to input (for "fill" actions)
    - "verbal_guide": Step-by-step instructions in plain English

    IMPORTANT: Only select targets that are present in the website structure and do not generate them on your own. They have to be genuine scrapped data and prioritize class or id.

    Example for login:
    {{
      "action_sequence": [
        {{"action": "fill", "target": "email", "value": "user@example.com"}},
        {{"action": "fill", "target": "password", "value": "securepassword123"}},
        {{"action": "click", "target": "Sign In"}}
      ],
      "verbal_guide": "First enter your email, then your password, then click Sign In"
    }}
    """

    print("\nSending prompt to LLM:")
    #print(prompt[:1000] + "..." if len(prompt) > 1000 else prompt)
    print(prompt)

    response = ollama.chat(
        model='llama3',
        messages=[{'role': 'user', 'content': prompt}],
        format='json',
        options={'temperature': 0.2}
    )

    print("\nReceived LLM response:")
    print(response['message']['content'])

    try:
        return json.loads(response['message']['content'])
    except json.JSONDecodeError:
        return {
            "error": "Invalid JSON response from LLM",
            "raw_response": response['message']['content']
        }