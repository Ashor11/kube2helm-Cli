# kube2helm-Cli
# Kube2Helm CLI

**AI-Powered Kubernetes YAML to Helm Chart Converter (Command-Line Interface)**

## Overview

Kube2Helm CLI is a command-line tool designed to simplify and automate the conversion of Kubernetes YAML manifests into well-structured Helm charts. It's perfect for scripting, CI/CD pipelines, and users who prefer a terminal-based workflow.

The optional AI assistance for advanced templating is provided by open-source models accessed via the Hugging Face Inference API.

## Features

-   **Convert Kubernetes YAML to Helm Charts:** Transform individual or multiple Kubernetes YAML files into a deployable Helm chart.
-   **Handles Multi-Document YAMLs:** Correctly processes files containing multiple Kubernetes resources separated by `---`.
-   **Intelligent Value Extraction:** Automatically extracts common configurations into `values.yaml` (leveraging logic from `main.py`).
-   **Templated Resources:** Generates Helm-compliant templated Kubernetes resource files.
-   **Optional AI-Assisted Templating:** Leverage Hugging Face models to assist in the templating process (experimental, requires API token).
-   **Flexible Input/Output:** Specify input files/directories and output chart directories.
-   **Custom Chart Naming:** Define a custom name for your generated Helm chart.
-   **Dry Run Mode:** Preview the chart structure without writing any files.

## Project Files (CLI Version)

-   `ash-conv-cli.py`: The main command-line interface script.
-   `main.py`: Contains the core conversion logic shared with the CLI. (Assumed to be part of the CLI distribution)
-   `deepseek_client.py`: Client for interacting with the Hugging Face Inference API, used for the `--use-ai` feature. (Assumed to be part of the CLI distribution if AI features are included)
-   `.env`: File to store the Hugging Face API token (not committed to Git).
-   `requirements.txt`: Python package dependencies for the CLI.

## Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Ashor11/kube2helm-Cli.git # Official CLI Repository URL
    cd kube2helm-Cli
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    # source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    Ensure your `requirements.txt` for the CLI includes `python-dotenv`, `requests`, `PyYAML`, and `transformers` (if AI features are used).

4.  **Set Up Environment Variables (for AI-assisted templating):**
    If you plan to use the `--use-ai` feature, create a file named `.env` in the root directory of the cloned project (`kube2helm-Cli/.env`).
    Add your Hugging Face API token to this file:
    ```
    HUGGINGFACE_TOKEN=your_actual_huggingface_api_token
    ```
    Replace `your_actual_huggingface_api_token` with your real token.

## Usage

The `ash-conv-cli.py` script is the entry point for all CLI operations.

1.  **Basic Conversion:**
    ```bash
    python ash-conv-cli.py -i /path/to/your/kubernetes-files -o /path/to/your/helm-chart
    ```
    -   `-i` or `--input`: Path to the input directory containing Kubernetes YAML files or a single YAML file. (Required)
    -   `-o` or `--output`: Path to the output directory where the Helm chart will be generated. (Required)

2.  **Using AI-Assisted Templating (Experimental):**
    Ensure your `HUGGINGFACE_TOKEN` is set in the `.env` file or as a system environment variable.
    ```bash
    python ash-conv-cli.py -i /path/to/kubernetes-files -o /path/to/output/chart --use-ai
    ```
    -   `--use-ai` or `-a`: Flag to enable AI-assisted templating via Hugging Face.

3.  **Dry Run (Preview):**
    To see what the chart would look like without writing any files:
    ```bash
    python ash-conv-cli.py -i /path/to/kubernetes-files -o /path/to/output/chart --dry-run
    ```
    -   `--dry-run`: Enables preview mode; no files are written.

4.  **Custom Chart Name:**
    Specify a custom name for your Helm chart:
    ```bash
    python ash-conv-cli.py -i ./input-yamls -o ./output-chart-dir --chart-name my-custom-chart
    ```
    -   `--chart-name <name>`: Sets the name of the generated Helm chart.

5.  **Getting Help:**
    For a full list of CLI options and their descriptions:
    ```bash
    python ash-conv-cli.py -h
    ```
    or
    ```bash
    python ash-conv-cli.py --help
    ```

## Requirements

-   Python 3.7+
-   `python-dotenv`
-   `requests`
-   `PyYAML`
-   `transformers` (Required if using the `--use-ai` feature)
    (See `requirements.txt` for specific versions)

## License

MIT  
