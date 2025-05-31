#!/usr/bin/env python3
"""
AshourCom K8S Manifest to Helm Generator - CLI Tool
Convert Kubernetes YAML manifests to Helm charts with AI assistance
"""
import argparse
import os
import sys
import yaml
import json
from pathlib import Path
from typing import List, Dict, Any

# Import core functions from main.py
from main import validate_yaml, extract_values, generate_helm_template, generate_chart_yaml

# Import DeepSeekClient (Hugging Face client)
from deepseek_client import DeepSeekClient

# ASCII art banner
BANNER = r"""

                    _                   
    /\      _____  | |       ___ ___   _____     ______   __        _____ 
   /  \    | ____| | |___   |  ___  | | ___ | + |   ___| |  |      |_   _|
  / /\ \   |_____  | |   |  | |   | | |__ __| + |  |     |  |        |  |
 / ____ \   ____ | |  _  |  | |___| | | | \ \ + |  |___  |  |____   _|  |_
/_/    \_\ |_____| |_| |_|  |__ __ _| |_|  \_\  |______| |_______| |______|

"""

def parse_args():
    """Parse command line arguments"""
    # Print banner
    print("\033[94m" + BANNER + "\033[0m")
    print("\033[92m" + "Welcome to AshourCom K8S Manifest to Helm Generator!" + "\033[0m")
    print("\033[93m" + "Convert Kubernetes YAML manifests to Helm charts with ease" + "\033[0m")
    print()
    
    parser = argparse.ArgumentParser(
        description="AshourCom K8S Manifest to Helm Generator - Convert Kubernetes YAML to Helm charts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py -i ./kubernetes-files -o ./helm-chart
  python cli.py -i ./kubernetes-files -o ./helm-chart --use-ai
  python cli.py -i ./kubernetes-files -o ./helm-chart --dry-run

Visit: https://www.linkedin.com/in/ashour-yasser/
Contact: ashouryasser11@gmail.com
        """
    )
    
    parser.add_argument(
        "--input", "-i", 
        required=True,
        help="Input file or directory containing Kubernetes YAML files"
    )
    
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory for the generated Helm chart"
    )
    
    parser.add_argument(
        "--use-ai", "-a",
        action="store_true",
        help="Use AI for advanced templating"
    )
    
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Preview the generated Helm chart without writing files"
    )
    
    return parser.parse_args()

def read_yaml_files(input_path: str) -> Dict[str, str]:
    """
    Read YAML files from the input path
    
    Args:
        input_path: Path to a file or directory
        
    Returns:
        Dictionary mapping filenames to YAML content
    """
    input_path = Path(input_path)
    yaml_files = {}
    
    if input_path.is_file():
        # Single file input
        if input_path.suffix.lower() in ['.yaml', '.yml']:
            with open(input_path, 'r') as f:
                yaml_files[input_path.name] = f.read()
    elif input_path.is_dir():
        # Directory input
        for file_path in input_path.glob('**/*.y*ml'):
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                with open(file_path, 'r') as f:
                    yaml_files[file_path.name] = f.read()
    
    return yaml_files

def template_yaml(yaml_content, resource_key):
    """Convert Kubernetes YAML to Helm template"""
    if not isinstance(yaml_content, dict):
        return yaml_content
    
    result = yaml_content.copy()
    
    # Template metadata
    if 'metadata' in result:
        metadata = result['metadata']
        if 'name' in metadata:
            metadata['name'] = f'{{{{ .Values.{resource_key}.name | default "{metadata["name"]}" }}}}'
        if 'namespace' in metadata:
            metadata['namespace'] = f'{{{{ .Values.{resource_key}.namespace | default "{metadata["namespace"]}" }}}}'
        if 'labels' in metadata:
            # Keep original labels but allow overrides
            metadata['labels'] = f'{{{{ .Values.{resource_key}.labels | default (dict) | toYaml | nindent 4 }}}}'
    
    # Template spec
    if 'spec' in result:
        spec = result['spec']
        if 'replicas' in spec:
            spec['replicas'] = f'{{{{ .Values.{resource_key}.replicas | default {spec["replicas"]} }}}}'
        
        # Template containers
        if 'template' in spec and 'spec' in spec['template']:
            template_spec = spec['template']['spec']
            if 'containers' in template_spec:
                for i, container in enumerate(template_spec['containers']):
                    if 'image' in container:
                        image_parts = container['image'].split(':')
                        repo = image_parts[0]
                        tag = image_parts[1] if len(image_parts) > 1 else 'latest'
                        container['image'] = f'{{{{ .Values.{resource_key}.containers[{i}].repository | default "{repo}" }}}}:{{{{ .Values.{resource_key}.containers[{i}].tag | default "{tag}" }}}}'
                    
                    if 'resources' in container:
                        container['resources'] = f'{{{{ .Values.{resource_key}.containers[{i}].resources | default (dict) | toYaml | nindent 10 }}}}'
    
    # Handle ConfigMap data
    if yaml_content.get('kind') == 'ConfigMap' and 'data' in result:
        # Keep original data but allow overrides
        result['data'] = f'{{{{ .Values.{resource_key}.data | default (dict) | toYaml | nindent 2 }}}}'
    
    # Handle Secret data
    if yaml_content.get('kind') == 'Secret' and 'data' in result:
        # Keep original data but allow overrides
        result['data'] = f'{{{{ .Values.{resource_key}.data | default (dict) | toYaml | nindent 2 }}}}'
    
    # Handle Service
    if yaml_content.get('kind') == 'Service':
        if 'spec' in result:
            if 'type' in result['spec']:
                result['spec']['type'] = f'{{{{ .Values.{resource_key}.service.type | default "{result["spec"]["type"]}" }}}}'
            if 'ports' in result['spec']:
                result['spec']['ports'] = f'{{{{ .Values.{resource_key}.service.ports | default (list) | toYaml | nindent 4 }}}}'
    
    return result

def write_helm_chart(output_path: str, chart_components: Dict[str, Any]):
    """
    Write Helm chart files to the output directory
    
    Args:
        output_path: Path to the output directory
        chart_components: Dictionary containing chart components
    """
    output_path = Path(output_path)
    
    # Create output directory structure
    output_path.mkdir(parents=True, exist_ok=True)
    templates_dir = output_path / "templates"
    templates_dir.mkdir(exist_ok=True)
    
    # Write Chart.yaml
    with open(output_path / "Chart.yaml", 'w') as f:
        f.write(chart_components["chart_yaml"])
    
    # Write values.yaml
    with open(output_path / "values.yaml", 'w') as f:
        f.write(chart_components["values_yaml"])
    
    # Write templates
    for template in chart_components["templates"]:
        with open(templates_dir / template["filename"], 'w') as f:
            f.write(template["content"])

def main():
    """Main entry point for the CLI tool"""
    args = parse_args()
    
    # Read input YAML files
    yaml_files = read_yaml_files(args.input)
    if not yaml_files:
        print(f"Error: No YAML files found in {args.input}")
        sys.exit(1)
    
    # Initialize AI client if needed
    ai_client = None
    if args.use_ai:
        try:
            # Ensure HUGGINGFACE_TOKEN is available, typically via .env in the project root
            # or if the user sets it in their environment directly.
            from dotenv import load_dotenv
            load_dotenv() # Attempt to load .env if present
            
            ai_client = DeepSeekClient()
            print("\033[94m[INFO]\033[0m AI client initialized for advanced templating (using Hugging Face).")
            if not os.getenv('HUGGINGFACE_TOKEN'):
                 print("\033[93m[WARNING]\033[0m HUGGINGFACE_TOKEN not found in environment. AI features might fail if not set globally.")
        except ImportError:
            # Handle missing deepseek_client or dotenv
            missing_modules = []
            try: import dotenv
            except ImportError: missing_modules.append("'python-dotenv'")
            try: import deepseek_client
            except ImportError: missing_modules.append("'deepseek_client' (your local client module)") # Clarify which deepseek_client
            
            if missing_modules:
                print(f"\033[91m[ERROR]\033[0m The following module(s) are not found: {', '.join(missing_modules)}. AI features require these. Please install/ensure they are available.")
            else:
                # This case implies an import error within DeepSeekClient itself, or another unexpected ImportError
                print("\033[91m[ERROR]\033[0m An unexpected import error occurred while trying to initialize AI components.")
            ai_client = None
        except Exception as e:
            print(f"\033[91m[ERROR]\033[0m Failed to initialize AI client: {e}")
            ai_client = None
    
    # Process YAML files
    all_values = {}
    templates = []
    
    for filename, content in yaml_files.items():
        print(f"\033[94m[INFO]\033[0m Processing {filename}...")
        
        try:
            # Parse YAML - use safe_load_all for multi-document support
            documents = list(yaml.safe_load_all(content)) # Convert generator to list to check if empty
            if not documents or all(doc is None for doc in documents): # Handle empty or all-null documents
                print(f"\033[93m[WARNING]\033[0m No valid YAML documents found in {filename}. Skipping.")
                continue

            for i, yaml_content in enumerate(documents):
                if yaml_content is None: # Skip if a specific document in a multi-doc stream is null
                    continue
                
                # Adjust resource key and template filename for multi-document files
                original_filename_stem = Path(filename).stem
                if len(documents) > 1:
                    resource_key = f"{original_filename_stem.replace('.', '_').replace('-', '_')}_{i}"
                    template_doc_filename = f"{original_filename_stem}-{i}{Path(filename).suffix}"
                else:
                    resource_key = original_filename_stem.replace('.', '_').replace('-', '_')
                    template_doc_filename = filename
                
                print(f"\033[94m[INFO]\033[0m   Processing document {i} as resource {resource_key} (template: {template_doc_filename})")

                # Extract original values for values.yaml
                values = {}
                
                # Extract metadata
                if 'metadata' in yaml_content:
                    metadata = yaml_content['metadata']
                    if 'name' in metadata:
                        values['name'] = metadata['name']
                    if 'namespace' in metadata:
                        values['namespace'] = metadata['namespace']
                    if 'labels' in metadata:
                        values['labels'] = metadata['labels']
                
                # Extract spec details
                if 'spec' in yaml_content:
                    spec = yaml_content['spec']
                    if 'replicas' in spec:
                        values['replicas'] = spec['replicas']
                    
                    # Extract container details
                    if 'template' in spec and 'spec' in spec['template']:
                        template_spec = spec['template']['spec']
                        if 'containers' in template_spec:
                            containers = []
                            for container in template_spec['containers']:
                                container_values = {}
                                if 'name' in container:
                                    container_values['name'] = container['name']
                                if 'image' in container:
                                    image_parts = container['image'].split(':')
                                    container_values['repository'] = image_parts[0]
                                    container_values['tag'] = image_parts[1] if len(image_parts) > 1 else 'latest'
                                if 'resources' in container:
                                    container_values['resources'] = container['resources']
                                containers.append(container_values)
                            values['containers'] = containers
                
                # Extract ConfigMap data
                if yaml_content.get('kind') == 'ConfigMap' and 'data' in yaml_content:
                    values['data'] = yaml_content['data']
                
                # Extract Secret data
                if yaml_content.get('kind') == 'Secret' and 'data' in yaml_content:
                    values['data'] = yaml_content['data']
                
                # Extract Service details
                if yaml_content.get('kind') == 'Service':
                    service = {}
                    if 'spec' in yaml_content:
                        if 'type' in yaml_content['spec']:
                            service['type'] = yaml_content['spec']['type']
                        if 'ports' in yaml_content['spec']:
                            service['ports'] = yaml_content['spec']['ports']
                    if service:
                        values['service'] = service
                
                # Store values
                all_values[resource_key] = values
                
                # Generate template
                templated_yaml_doc = template_yaml(yaml_content, resource_key) # Pass single doc here
                templates.append({
                    "filename": template_doc_filename, # Use potentially indexed filename
                    "content": yaml.dump(templated_yaml_doc, default_flow_style=False)
                })
        except yaml.YAMLError as e:
            print(f"\033[91m[ERROR]\033[0m Error in {filename}: {str(e)}")
            continue
    
    chart_components = {
        "chart_yaml": """apiVersion: v2
name: ashourcom-helm-chart
description: Auto-generated Helm chart by AshourCom K8S Manifest to Helm Generator
version: 0.1.0
appVersion: "1.0.0"
""",
        "values_yaml": yaml.dump(all_values, default_flow_style=False),
        "templates": templates
    }
    
    # Preview or write the generated Helm chart
    if args.dry_run:
        print("\n\033[93m[DRY RUN]\033[0m Generated Helm Chart (Preview):")
        print("\n\033[92mChart.yaml:\033[0m")
        print(chart_components["chart_yaml"])
        print("\n\033[92mvalues.yaml:\033[0m")
        print(chart_components["values_yaml"])
        print("\n\033[92mTemplates:\033[0m")
        for template in chart_components["templates"]:
            print(f"\n\033[92m{template['filename']}:\033[0m")
            print(template["content"])
    else:
        write_helm_chart(args.output, chart_components)
        print(f"\n\033[92m[SUCCESS]\033[0m Helm chart generated successfully at {args.output}")

if __name__ == "__main__":
    main()