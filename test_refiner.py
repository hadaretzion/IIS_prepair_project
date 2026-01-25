"""Test the question refiner."""
from backend.services.llm_client import call_llm

text = "Write a function to convert Roman numerals to integers."
q_type = "code"

prompt = f"""Task: Translate and Refine Interview Question.
Target Language: Hebrew (Ivrit).
Instructions:
1. Translate the following technical interview question to professional, natural Hebrew.
2. EXPAND on the question to provide a RICH, DETAILED SCENARIO.
3. Instead of just asking the question, wrap it in a real-world engineering context.
4. Make the question feel like a discussion with a senior engineer.
5. Ensure the technical requirements are clear and detailed.
6. Output ONLY the final Hebrew question text (Scenario + Question).

Original Question: "{text}"
Question Type: {q_type}

Hebrew Question:"""

print("Sending prompt...")
try:
    result = call_llm("You are an expert Hebrew technical interviewer.", prompt, prefer="groq")
    print("RAW RESULT:")
    print(repr(result))
    print()
    print("FORMATTED:")
    print(result)
except Exception as e:
    print("ERROR:", e)
    import traceback
    traceback.print_exc()
