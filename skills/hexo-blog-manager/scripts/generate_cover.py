import sys
import os
from huggingface_hub import InferenceClient

# Token should be provided via environment variable
HF_TOKEN = os.environ.get("HF_TOKEN")
DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"

def generate(prompt, output_path):
    if not HF_TOKEN:
        print("Error: HF_TOKEN environment variable not set.")
        sys.exit(1)
    
    client = InferenceClient(model=DEFAULT_MODEL, token=HF_TOKEN)
    try:
        print(f"Generating image for prompt: {prompt}")
        image = client.text_to_image(prompt)
        image.save(output_path)
        print(f"Successfully saved to {output_path}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_cover.py '<prompt>' <output_path>")
        sys.exit(1)
    
    prompt_arg = sys.argv[1]
    output_arg = sys.argv[2]
    generate(prompt_arg, output_arg)
