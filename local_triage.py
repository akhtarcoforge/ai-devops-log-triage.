import os
import sys
import ollama

def get_pipeline_logs(build_id):
    """Fetches log context. Drops to local Mock Mode if Azure keys aren't exported."""
    azure_pat = os.getenv("AZURE_DEVOPS_PAT")
    org_url = os.getenv("AZURE_DEVOPS_ORG_URL")
    project = os.getenv("AZURE_PROJECT_NAME")

    if not azure_pat or not org_url or not project:
        print("\n📢 [MOCK MODE] Azure environment variables not detected.")
        print("👉 Simulating a live Azure Pipeline Node.js/Docker crash log for testing...\n")

        # Real-world style Docker + Node.js error trace
        mock_log = """
        [INFO] Step 4/7 : RUN npm run build
        [INFO] ---> Running in a3ef92d1
        [ERR ] > my-app@1.0.0 build /usr/src/app
        [ERR ] > tsc
        [ERR ] src/server.ts(12,24): error TS2304: Cannot find name 'ConfigProvider'.
        [ERR ] src/db/connection.ts(4,7): error TS2307: Cannot find module './config/vault' or its corresponding type declarations.
        [ERR ] npm ERR! code ELIFECYCLE
        [ERR ] npm ERR! errno 1
        [ERR ] npm ERR! my-app@1.0.0 build: `tsc`
        [ERR ] npm ERR! Failed at the my-app@1.0.0 build script.
        [ERR ] The command '/bin/sh -c npm run build' returned a non-zero code: 1
        ##[error] Process completed with exit code 1.
        """
        return [{"step": "Build and Compile Application Container", "content": mock_log}]

    try:
        from azure.devops.connection import Connection
        from msrest.authentication import BasicAuthentication

        print(f"Connecting to Azure DevOps URL: {org_url}...")
        credentials = BasicAuthentication('', azure_pat)
        connection = Connection(base_url=org_url, creds=credentials)
        build_client = connection.clients.get_build_client()

        timeline = build_client.get_build_timeline(project=project, build_id=build_id)
        failed_logs = []

        for record in timeline.records:
            if record.result == "failed" and record.log:
                log_lines = build_client.get_build_log_lines(project=project, build_id=build_id, log_id=record.log.id)
                error_dump = "\n".join(list(log_lines)[-50:])
                failed_logs.append({"step": record.name, "content": error_dump})
        return failed_logs
    except Exception as e:
        print(f"⚠️ Failed to connect to real Azure API: {str(e)}")
        sys.exit(1)

def ask_local_llama(step_name, log_content):
    """Sends the logs to Llama 3.2 running completely locally on your Mac processor."""
    print(f"🧠 Pushing logs from '{step_name}' to local Llama 3.2 engine via Ollama...")

    prompt = f"""
    You are an elite Senior Site Reliability Engineer (SRE). Analyze this pipeline failure log for the step '{step_name}'.
    Provide a highly technical, 3-step triage assessment following exactly this layout:

    🚨 **FAILED PIPELINE STEP:** {step_name}

    ### 1. What Failed
    (Identify the exact error message, file name, line number, or syntax failure)

    ### 2. Root Cause
    (Explain technical reason why this crash happened)

    ### 3. Recommended Remediation Commands
    * Step 1: (Give the exact command line or code adjustment required to fix the issue)
    * Step 2: (Provide the validation step to ensure it is fixed)

    ---
    RAW STACK TRACE LOG:
    {log_content}
    """

    response = ollama.chat(
        model='llama3.2:3b',
        messages=[{'role': 'user', 'content': prompt}]
    )
    return response['message']['content']

def main():
    build_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1042

    logs = get_pipeline_logs(build_id)
    if not logs:
        print("✅ No pipeline step failures found in this build profile.")
        return

    for log_item in logs:
        triage_report = ask_local_llama(log_item["step"], log_item["content"])
        print("\n" + "="*60)
        print(" 🚀 LOCAL AIOPS PIPELINE TRIAGE REPORT (POWERED BY LLAMA) ")
        print("="*60)
        print(triage_report)
        print("="*60 + "\n")

if __name__ == "__main__":
    main()
