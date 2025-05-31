"""
Kube2Helm-Q - AI-Powered Kubernetes to Helm Chart Converter
Main entry point for the application
"""
import os
import sys
import yaml
import json
import argparse
from pathlib import Path
from deepseek_client import DeepSeekClient


def setup_directories():
    """Create necessary project directories if they don't exist"""
    dirs = [
        "src/backend",
        "src/frontend",
        "src/cli",
        "templates",
        "tests",
        "docs",
        "output"
    ]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    print("Project directories created successfully")

def validate_yaml(file_path):
    """Validate YAML syntax and basic Kubernetes schema"""
    try:
        # Handle multiple YAML documents in a single file
        with open(file_path, 'r') as f:
            yaml_content_list = list(yaml.safe_load_all(f))
        
        if not yaml_content_list:
            return False, "No valid YAML documents found"
        
        # For simplicity, we'll just use the first document for now
        # In a more complete implementation, you'd process all documents
        yaml_content = yaml_content_list[0]
            
        # Basic validation - check for required Kubernetes fields
        if not isinstance(yaml_content, dict):
            return False, "YAML does not parse to a dictionary"
        
        required_fields = ['apiVersion', 'kind']
        for field in required_fields:
            if field not in yaml_content:
                return False, f"Missing required field: {field}"
                
        return True, yaml_content
    except yaml.YAMLError as e:
        return False, f"YAML syntax error: {str(e)}"
    except Exception as e:
        return False, f"Error validating YAML: {str(e)}"

def extract_values(yaml_content):
    """Extract values that should be parameterized in values.yaml"""
    values = {}
    
    # Extract common fields that should be parameterized
    if 'metadata' in yaml_content:
        if 'name' in yaml_content['metadata']:
            values['name'] = yaml_content['metadata']['name']
        if 'namespace' in yaml_content['metadata']:
            values['namespace'] = yaml_content['metadata']['namespace']
    
    # Extract container image if present
    if 'spec' in yaml_content:
        if 'template' in yaml_content['spec']:
            if 'spec' in yaml_content['spec']['template']:
                if 'containers' in yaml_content['spec']['template']['spec']:
                    containers = yaml_content['spec']['template']['spec']['containers']
                    if containers and 'image' in containers[0]:
                        values['image'] = {
                            'repository': containers[0]['image'].split(':')[0],
                            'tag': containers[0]['image'].split(':')[1] if ':' in containers[0]['image'] else 'latest'
                        }
    
    return values

def generate_helm_template(yaml_content, values):
    """Generate Helm template from Kubernetes YAML"""
    # Create a copy of the YAML to modify
    template = yaml_content.copy()
    
    # Replace values with Helm template variables
    if 'metadata' in template:
        if 'name' in template['metadata'] and 'name' in values:
            template['metadata']['name'] = "{{ .Values.name }}"
        if 'namespace' in template['metadata'] and 'namespace' in values:
            template['metadata']['namespace'] = "{{ .Values.namespace }}"
    
    # Replace container image if present
    if 'spec' in template:
        if 'template' in template['spec']:
            if 'spec' in template['spec']['template']:
                if 'containers' in template['spec']['template']['spec']:
                    containers = template['spec']['template']['spec']['containers']
                    if containers and 'image' in containers[0] and 'image' in values:
                        containers[0]['image'] = "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
    
    return template

def generate_chart_yaml(name="generated-chart", version="0.1.0"):
    """Generate Chart.yaml content"""
    return {
        "apiVersion": "v2",
        "name": name,
        "description": "Auto-generated Helm chart by Kube2Helm-Q",
        "type": "application",
        "version": version,
        "appVersion": "1.0.0"
    }

def process_yaml_documents(file_path):
    """Process YAML file that might contain multiple documents"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Try to load all documents
        documents = list(yaml.safe_load_all(content))
        return documents
    except yaml.YAMLError as e:
        print(f"YAML parsing error in {file_path}: {str(e)}")
        # Try to handle the error by splitting the file manually
        try:
            # Split by document separator and parse each document separately
            yaml_docs = content.split("---")
            documents = []
            for doc in yaml_docs:
                if doc.strip():  # Skip empty documents
                    parsed_doc = yaml.safe_load(doc)
                    if parsed_doc:  # Only add non-None documents
                        documents.append(parsed_doc)
            return documents
        except Exception as e2:
            print(f"Failed to recover from YAML error in {file_path}: {str(e2)}")
            return []

def convert_kubernetes_to_helm(input_path, output_path):
    """Convert Kubernetes YAML to Helm chart"""
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    # Create output directory structure
    templates_dir = output_path / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    # Process all YAML files in the input directory
    all_values = {}
    yaml_files = list(input_path.glob("*.yaml")) + list(input_path.glob("*.yml"))
    
    if not yaml_files:
        print(f"No YAML files found in {input_path}")
        return False
    
    for yaml_file in yaml_files:
        print(f"Processing {yaml_file}...")
        
        # Process all YAML documents in the file
        documents = process_yaml_documents(yaml_file)
        
        if not documents:
            print(f"No valid YAML documents found in {yaml_file}")
            continue
        
        # Process each document separately
        for i, doc in enumerate(documents):
            # Skip empty documents
            if not doc:
                continue
                
            # Basic validation
            if not isinstance(doc, dict):
                print(f"Document {i+1} in {yaml_file} is not a valid Kubernetes resource")
                continue
                
            required_fields = ['apiVersion', 'kind']
            if not all(field in doc for field in required_fields):
                print(f"Document {i+1} in {yaml_file} is missing required Kubernetes fields")
                continue
            
            # Extract values for values.yaml
            values = extract_values(doc)
            
            # Use kind and name for resource identification
            kind = doc.get('kind', '').lower()
            name = doc.get('metadata', {}).get('name', '')
            resource_name = name or f"{kind}-{i+1}" or yaml_file.stem
            
            all_values[resource_name] = values
            
            # Generate template
            template = generate_helm_template(doc, values)
            
            # Write template to file - use a unique name for each document
            template_filename = f"{resource_name}.yaml"
            if i > 0:  # Add index for multiple documents of same kind
                template_filename = f"{resource_name}-{i}.yaml"
                
            template_file = templates_dir / template_filename
            with open(template_file, 'w') as f:
                yaml.dump(template, f)
            
            print(f"Generated template: {template_file}")
    
    # Generate values.yaml
    with open(output_path / "values.yaml", 'w') as f:
        yaml.dump(all_values, f)
    
    # Generate Chart.yaml
    chart_name = output_path.name
    with open(output_path / "Chart.yaml", 'w') as f:
        yaml.dump(generate_chart_yaml(chart_name), f)
    
    print(f"Helm chart generated successfully at {output_path}")
    return True

def run_interactive_chat():
    """Runs an interactive chat session with the AI model."""
    try:
        # Ensure HUGGINGFACE_TOKEN is set (client will also check, but good to be upfront)
        if not os.getenv('HUGGINGFACE_TOKEN'):
            print("CRITICAL: The HUGGINGFACE_TOKEN environment variable is not set.")
            print("Please set it before running the chat.")
            return

        # You can customize the system prompt if you like
        # client = DeepSeekClient(system_prompt="You are a Kubernetes and Helm expert.")
        client = DeepSeekClient() 
        print(f"Initialized chat with {client.api_url}")
        print("Starting interactive chat session with AI. Type 'exit' or 'quit' to end.")
        print(f"Using system prompt: '{client.system_prompt}'")
        print("---")

        conversation_history = []

        while True:
            user_input = input("You: ")
            if user_input.lower() in ['exit', 'quit']:
                print("Exiting chat.")
                break

            if not user_input.strip():
                continue

            # Add user message to history for the API call
            messages_for_api = list(conversation_history) # Use a copy
            messages_for_api.append({"role": "user", "content": user_input})

            try:
                print("AI is thinking...")
                ai_response = client.chat(messages=messages_for_api)
                print(f"AI: {ai_response}")

                # Update conversation history with both user message and AI response
                conversation_history.append({"role": "user", "content": user_input})
                conversation_history.append({"role": "assistant", "content": ai_response})

            except Exception as e:
                print(f"Error communicating with AI: {e}")
                # Optionally, decide if you want to clear history on error or allow retry
                # For now, we'll continue with the existing history.

    except ValueError as ve: # Catches missing token from DeepSeekClient init
        print(f"Chat initialization error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred in the chat session: {e}")

def main():
    parser = argparse.ArgumentParser(description="Kube2Helm-Q: AI-Powered Kubernetes to Helm Chart Converter & AI Chat")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Subparser for the convert command (assuming this is the existing functionality)
    convert_parser = subparsers.add_parser('convert', help='Convert Kubernetes YAML to Helm chart')
    convert_parser.add_argument("--input", "-i", required=True, help="Input file or directory containing Kubernetes YAML files")
    convert_parser.add_argument("--output", "-o", required=True, help="Output directory for the generated Helm chart")
    # Add other arguments for convert if they exist (e.g., --use-ai, --dry-run from your CLI_HTML)
    # convert_parser.add_argument("--use-ai", "-a", action='store_true', help="Use AI for advanced templating (Feature for Q, adapt if needed)")
    # convert_parser.add_argument("--dry-run", "-d", action='store_true', help="Preview the generated Helm chart without writing files")

    # Subparser for the setup command
    setup_parser = subparsers.add_parser('setup', help='Create necessary project directories')
    
    # Subparser for the chat command
    chat_parser = subparsers.add_parser('chat', help='Start an interactive chat session with the AI')
    # No arguments needed for chat_parser for now, but you could add --system-prompt later

    args = parser.parse_args()

    if args.command == 'setup':
        setup_directories()
    elif args.command == 'convert':
        print(f"Converting {args.input} to {args.output}...")
        success = convert_kubernetes_to_helm(args.input, args.output)
        if success:
            print(f"Helm chart generated successfully in {args.output}")
        else:
            print("Helm chart generation failed.")
    elif args.command == 'chat':
        run_interactive_chat()
    else:
        # If no command is given, or an unknown command, print help.
        # This behavior depends on whether 'command' is made required in add_subparsers.
        # If dest is set and no command, args.command will be None.
        if args.command is None:
            parser.print_help()
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()

if __name__ == "__main__":
    main()