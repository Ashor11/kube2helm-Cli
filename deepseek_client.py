import os
import requests
from typing import Dict, List, Optional

class DeepSeekClient:
    def __init__(self, system_prompt: Optional[str] = None):
        # Using HuggingFaceH4/zephyr-7b-beta as suggested by user
        self.api_url = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
        # Updated default system prompt for better context
        default_prompt = ("You are Ashour AI Assist, an expert assistant for the Kube2Helm application. "
                          "This application helps users convert Kubernetes YAML files into Helm charts. "
                          "Users can upload their YAML files through the GUI. "
                          "You can answer questions about Kubernetes, Helm, the conversion process, "
                          "and help users understand the generated Helm chart components (like Chart.yaml, values.yaml, and templates). "
                          "You cannot directly read the user's local files, but you can discuss the YAML they might upload "
                          "or the Helm charts the application generates.")
        self.system_prompt = system_prompt if system_prompt is not None else default_prompt
        
        token = os.getenv('HUGGINGFACE_TOKEN')
        if not token:
            raise ValueError("Hugging Face token not provided. Set HUGGINGFACE_TOKEN environment variable.")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _format_messages_for_zephyr(self, messages: List[Dict[str, str]]) -> str:
        """Formats messages for Zephyr models, including a system prompt."""
        prompt_str = f"<|system|>\n{self.system_prompt}</s>\n"
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "").strip()
            if role == "user":
                prompt_str += f"<|user|>\n{content}</s>\n"
            elif role == "assistant":
                prompt_str += f"<|assistant|>\n{content}</s>\n"
            # Other roles could be ignored or handled differently if needed
        
        # Ensure the prompt ends with the turn for the assistant to speak
        if not prompt_str.endswith("<|assistant|>\n"):
             prompt_str += "<|assistant|>\n"
        return prompt_str

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 250, temperature: float = 0.7) -> str:
        print(f"Attempting to use API URL: {self.api_url}")
        if self.headers.get("Authorization"):
            token_preview = self.headers["Authorization"][:12] # "Bearer " is 7 chars + 5 for token
            print(f"Using token: {token_preview}...")
        else:
            print("Authorization header not found.")
            
        prompt = self._format_messages_for_zephyr(messages)
        
        payload = {
            "inputs": prompt, 
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False, # Important for chat-like interaction
                # Zephyr specific parameters can be added if needed, e.g., top_p, top_k
            },
            "options": {
                "wait_for_model": True,
                "use_cache": False
            }
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status() # Raise HTTP errors (4xx or 5xx)
            json_response = response.json()

            if isinstance(json_response, list) and len(json_response) > 0 and "generated_text" in json_response[0]:
                # Zephyr might sometimes leave the assistant prompt token at the beginning of its reply
                generated_text = json_response[0]["generated_text"].strip()
                # Remove a leading <|assistant|> if present, as we add it to prompt.
                # This might not be strictly necessary if return_full_text=False handles it, but good for robustness.
                if generated_text.startswith("<|assistant|>"):
                    generated_text = generated_text[len("<|assistant|>"):].strip()
                return generated_text
            elif isinstance(json_response, dict) and "generated_text" in json_response:
                 return json_response["generated_text"].strip()
            elif isinstance(json_response, str):
                return json_response.strip()
            else:
                raise ValueError(f"Unexpected API response format: {json_response}")

        except requests.exceptions.RequestException as e:
            error_detail = ""
            try:
                if e.response is not None:
                    error_detail = e.response.json() if e.response.headers.get('content-type') == 'application/json' else e.response.text
            except ValueError:
                error_detail = e.response.text if e.response is not None else "No response body"
            raise Exception(f"API request failed: {e}. Detail: {error_detail}")
        except Exception as e:
            raise Exception(f"An error occurred during chat processing: {e}")

# Test
if __name__ == "__main__":
    try:
        token = os.getenv('HUGGINGFACE_TOKEN')
        if token:
            print(f"Using HUGGINGFACE_TOKEN: '{token[:5]}...'")
        else:
            print("CRITICAL: HUGGINGFACE_TOKEN environment variable is not set.")
        
        # You can customize the system prompt when creating the client
        # client = DeepSeekClient(system_prompt="You are a pirate chatbot who says 'Arrr!' a lot.")
        client = DeepSeekClient() # Uses default system prompt
        print(f"Client initialized. API URL: {client.api_url}")
        print(f"System Prompt: {client.system_prompt}")
        
        print("\n--- Test 1: Simple Question (Zephyr) ---")
        test_messages_1 = [
            {"role": "user", "content": "What is Hugging Face known for in the AI community?"}
        ]
        print(f"Sending messages: {test_messages_1}")
        response_text_1 = client.chat(test_messages_1, max_tokens=150)
        print(f"\nAssistant's Raw Response:\n{response_text_1}")

        print("\n--- Test 2: Conversation (Zephyr) ---")
        conversation_history = [
            {"role": "user", "content": "What is the capital of Spain?"},
            {"role": "assistant", "content": "The capital of Spain is Madrid."},
            {"role": "user", "content": "Can you recommend a good dish to try there?"}
        ]
        print(f"Sending conversation: {conversation_history}")
        response_text_2 = client.chat(conversation_history, max_tokens=100)
        print(f"Assistant's Raw Response:\n{response_text_2}")

    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}")
        import traceback
        traceback.print_exc() 