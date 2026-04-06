#!/usr/bin/env python3
"""
OpenClaw Memory Setup — One-command setup for persistent AI memory.

Usage:
    python3 setup.py              # Interactive setup
    python3 setup.py --guided     # Step-by-step for beginners
    python3 setup.py --check      # Check if already configured
"""

import json
import os
import sys
import subprocess
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SKILL_DIR, "config.json")
MEMORY_ID_FILE = os.path.join(SKILL_DIR, ".memory-id")
LIB_DIR = os.path.expanduser("~/.openclaw/lib/python")
TAILER_SCRIPT = os.path.join(SKILL_DIR, "scripts", "session_tailer.py")
SYSTEMD_DIR = os.path.expanduser("~/.config/systemd/user")


def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)


def check_aws_credentials():
    """Check if AWS credentials are configured."""
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity", "--output", "json"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            identity = json.loads(result.stdout)
            log.info(f"✅ AWS credentials found: {identity['Arn']}")
            return identity
        return None
    except Exception:
        return None


def check_sdk_installed():
    """Check if AgentCore SDK is installed."""
    try:
        sys.path.insert(0, LIB_DIR)
        from bedrock_agentcore.memory import MemoryClient
        log.info("✅ AgentCore SDK installed")
        return True
    except ImportError:
        return False


def install_sdk():
    """Install the AgentCore SDK."""
    log.info("📦 Installing AgentCore Memory SDK...")
    os.makedirs(LIB_DIR, exist_ok=True)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--target", LIB_DIR,
         "--upgrade", "amazon-bedrock-agentcore-client", "boto3"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        # Try with --break-system-packages for Ubuntu 24.04
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--break-system-packages",
             "--target", LIB_DIR, "--upgrade",
             "amazon-bedrock-agentcore-client", "boto3"],
            capture_output=True, text=True,
        )
    if result.returncode == 0:
        log.info("✅ SDK installed to %s", LIB_DIR)
        return True
    else:
        log.error("❌ SDK install failed: %s", result.stderr[-200:])
        return False


def create_memory_resource(config):
    """Create the AgentCore Memory resource."""
    sys.path.insert(0, LIB_DIR)
    from bedrock_agentcore.memory import MemoryClient
    from bedrock_agentcore.memory.constants import StrategyType

    client = MemoryClient(region_name=config["region"])
    assistant_name = config.get("memory_name", "OpenClawMemory")

    # Build strategies from config
    strategies = []
    for key, strat in config["strategies"].items():
        stype = strat["type"]
        ns = strat["namespace"].replace("{assistant}", assistant_name.lower())

        if stype == "custom_semantic":
            strategies.append({
                StrategyType.CUSTOM.value: {
                    "name": strat["name"],
                    "description": strat["description"],
                    "namespaces": [ns],
                    "configuration": {
                        "semanticOverride": {
                            "extraction": {
                                "appendToPrompt": strat.get("extraction_prompt", ""),
                                "modelId": strat.get("model", "us.anthropic.claude-sonnet-4-20250514-v1:0"),
                            },
                            "consolidation": {
                                "appendToPrompt": strat.get("consolidation_prompt", ""),
                                "modelId": strat.get("model", "us.anthropic.claude-sonnet-4-20250514-v1:0"),
                            },
                        }
                    },
                }
            })
        elif stype == "user_preference":
            strategies.append({
                StrategyType.USER_PREFERENCE.value: {
                    "name": strat["name"],
                    "description": strat["description"],
                    "namespaces": [ns],
                }
            })
        elif stype == "semantic":
            strategies.append({
                StrategyType.SEMANTIC.value: {
                    "name": strat["name"],
                    "description": strat["description"],
                    "namespaces": [ns],
                }
            })
        elif stype == "summary":
            strategies.append({
                StrategyType.SUMMARY.value: {
                    "name": strat["name"],
                    "description": strat["description"],
                    "namespaces": [ns],
                }
            })
        elif stype == "episodic":
            strategies.append({
                StrategyType.EPISODIC.value: {
                    "name": strat["name"],
                    "description": strat["description"],
                    "namespaces": [ns],
                    "reflectionConfiguration": {
                        "namespaces": [strat.get("reflection_namespace", ns).replace("{assistant}", assistant_name.lower())]
                    },
                }
            })

    # Check for execution role (needed for custom strategies)
    has_custom = any(s["type"] == "custom_semantic" for s in config["strategies"].values())
    role_arn = None

    if has_custom:
        role_arn = find_or_create_execution_role(config["region"])
        if not role_arn:
            log.warning("⚠️  No execution role found. Custom strategies will use built-in extraction.")
            # Downgrade custom to regular semantic
            for i, s in enumerate(strategies):
                if StrategyType.CUSTOM.value in s:
                    old = s[StrategyType.CUSTOM.value]
                    strategies[i] = {
                        StrategyType.SEMANTIC.value: {
                            "name": old["name"],
                            "description": old["description"],
                            "namespaces": old["namespaces"],
                        }
                    }

    log.info("🧠 Creating memory resource: %s (%d strategies)", assistant_name, len(strategies))

    kwargs = dict(
        name=assistant_name,
        strategies=strategies,
        description=f"Persistent memory for OpenClaw assistant",
        event_expiry_days=config.get("event_expiry_days", 365),
    )
    if role_arn:
        kwargs["memory_execution_role_arn"] = role_arn

    memory = client.create_or_get_memory(**kwargs)
    memory_id = memory.get("memoryId", memory.get("id"))

    with open(MEMORY_ID_FILE, "w") as f:
        f.write(memory_id)

    log.info("✅ Memory resource created: %s", memory_id)
    return memory_id


def find_or_create_execution_role(region):
    """Find existing execution role or create one."""
    import boto3
    iam = boto3.client("iam")

    role_name = "openclaw-agentcore-memory-role"
    try:
        resp = iam.get_role(RoleName=role_name)
        log.info("✅ Execution role found: %s", resp["Role"]["Arn"])
        return resp["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        pass

    log.info("🔧 Creating execution role: %s", role_name)
    try:
        resp = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }],
            }),
            Description="Execution role for AgentCore Memory custom strategies",
        )
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName="BedrockInvoke",
            PolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                    "Resource": "*",
                }],
            }),
        )
        log.info("✅ Execution role created: %s", resp["Role"]["Arn"])
        return resp["Role"]["Arn"]
    except Exception as e:
        log.warning("⚠️  Could not create execution role: %s", e)
        return None


def install_tailer():
    """Install the session tailer as a systemd user service."""
    os.makedirs(SYSTEMD_DIR, exist_ok=True)
    service_path = os.path.join(SYSTEMD_DIR, "memory-tailer.service")

    service_content = f"""[Unit]
Description=AgentCore Memory Session Tailer
After=openclaw-gateway.service

[Service]
ExecStart={sys.executable} {TAILER_SCRIPT}
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
"""
    with open(service_path, "w") as f:
        f.write(service_content)

    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
    subprocess.run(["systemctl", "--user", "enable", "memory-tailer"], capture_output=True)
    subprocess.run(["systemctl", "--user", "start", "memory-tailer"], capture_output=True)

    log.info("✅ Session tailer installed and started as systemd service")


def check_status():
    """Check if memory is already set up."""
    log.info("🔍 Checking OpenClaw Memory status...\n")

    # AWS credentials
    identity = check_aws_credentials()
    if not identity:
        log.info("❌ AWS credentials not configured")
        return False

    # SDK
    if not check_sdk_installed():
        log.info("❌ AgentCore SDK not installed")
        return False

    # Memory resource
    if os.path.exists(MEMORY_ID_FILE):
        with open(MEMORY_ID_FILE) as f:
            memory_id = f.read().strip()
        log.info(f"✅ Memory resource: {memory_id}")
    else:
        log.info("❌ Memory resource not created")
        return False

    # Tailer service
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "memory-tailer"],
        capture_output=True, text=True,
    )
    if result.stdout.strip() == "active":
        log.info("✅ Session tailer running")
    else:
        log.info("❌ Session tailer not running")
        return False

    log.info("\n✅ OpenClaw Memory is fully configured!")
    return True


def guided_setup():
    """Step-by-step setup for beginners."""
    log.info("""
╔══════════════════════════════════════════════════╗
║     OpenClaw Memory — Guided Setup              ║
║     Give your AI assistant real memory           ║
╚══════════════════════════════════════════════════╝
""")

    # Step 1: AWS credentials
    log.info("Step 1: AWS Credentials")
    log.info("─" * 40)
    identity = check_aws_credentials()
    if not identity:
        log.info("""
Your assistant needs an AWS account to store memories.

Option A — Quick setup (recommended):
  1. Go to https://aws.amazon.com and create a free account
  2. Go to IAM → Users → Create user
  3. Attach policy: search "AgentCore" or create inline policy with:
     {"Statement":[{"Effect":"Allow","Action":["bedrock-agentcore:*","bedrock-agentcore-control:*"],"Resource":"*"}]}
  4. Create access key → copy the key ID and secret
  5. Run: aws configure
     - Enter your access key ID and secret
     - Region: us-west-2
     - Output: json

Option B — One-click CloudFormation:
  See aws/cloudformation.yaml in this directory.

Once configured, run this setup again.
""")
        return False

    # Step 2: SDK
    log.info("\nStep 2: Installing SDK")
    log.info("─" * 40)
    if not check_sdk_installed():
        if not install_sdk():
            return False

    # Step 3: Memory resource
    log.info("\nStep 3: Creating Memory Resource")
    log.info("─" * 40)
    config = load_config()
    memory_id = create_memory_resource(config)
    if not memory_id:
        return False

    # Step 4: Tailer
    log.info("\nStep 4: Installing Session Tailer")
    log.info("─" * 40)
    install_tailer()

    log.info("""
╔══════════════════════════════════════════════════╗
║  ✅ Setup Complete!                              ║
║                                                  ║
║  Your assistant now has persistent memory.        ║
║  Restart the gateway to activate:                ║
║    openclaw gateway restart                      ║
║                                                  ║
║  Memory ID: %-36s  ║
╚══════════════════════════════════════════════════╝
""" % memory_id)
    return True


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Memory Setup")
    parser.add_argument("--guided", action="store_true", help="Step-by-step setup for beginners")
    parser.add_argument("--check", action="store_true", help="Check if already configured")
    args = parser.parse_args()

    if args.check:
        check_status()
    elif args.guided:
        guided_setup()
    else:
        # Quick setup — assumes AWS credentials are already configured
        config = load_config()
        identity = check_aws_credentials()
        if not identity:
            log.error("❌ AWS credentials not found. Run with --guided for step-by-step setup.")
            sys.exit(1)
        if not check_sdk_installed():
            install_sdk()
        create_memory_resource(config)
        install_tailer()
        log.info("\n✅ Done! Session tailer is running — memory sync is active.")


if __name__ == "__main__":
    main()
