#!/bin/bash
# OCI ARM Instance Retry Script - For OCI Cloud Shell
# Retries launching a VM.Standard.A1.Flex instance every 60 seconds until capacity is available
#
# Usage (in OCI Cloud Shell):
#   chmod +x oci-arm-retry-cloudshell.sh
#   ./oci-arm-retry-cloudshell.sh
#
# To run in background (survives Cloud Shell tab close):
#   nohup ./oci-arm-retry-cloudshell.sh > retry.log 2>&1 &
#   tail -f retry.log
#
# Cloud Shell limits:
#   - 20 min idle timeout (script activity keeps it alive)
#   - 24 hour max session (restart daily if needed)
#   - 5 GB persistent home storage
#   - OCI CLI pre-authenticated (no config needed!)

COMPARTMENT_ID="ocid1.tenancy.oc1..aaaaaaaaq66c2kxwcqcb747nghth75fsoxbqwsoqv3i2l3ovorxgjcfvwqea"
AVAILABILITY_DOMAIN="AFcd:AP-MELBOURNE-1-AD-1"
SUBNET_ID="ocid1.subnet.oc1.ap-melbourne-1.aaaaaaaayy3qb77k5wj5cv4l6mztxwtblh2qsenpu3hb6p4dljahnxjhnc2a"
IMAGE_ID="ocid1.image.oc1.ap-melbourne-1.aaaaaaaae5qwh6tn4nhgkb6nm32tzbieqnv773k5diy2g66lbf62agscisoq"
SHAPE="VM.Standard.A1.Flex"
DISPLAY_NAME="ubuntu-arm-server"
OCPUS=4
MEMORY_GB=24
BOOT_VOLUME_SIZE_GB=200
RETRY_INTERVAL=60

SSH_KEY_PATH="$HOME/.ssh/oci_arm_key"

# Generate SSH key if not present (persists in Cloud Shell home dir)
if [ ! -f "${SSH_KEY_PATH}.pub" ]; then
    echo "[*] Generating SSH key pair at $SSH_KEY_PATH"
    ssh-keygen -t ed25519 -f "$SSH_KEY_PATH" -N "" -C "oci-arm-instance"
    if [ $? -ne 0 ]; then
        echo "[!] SSH key generation failed."
        exit 1
    fi
    echo "[*] Key generated. Save this public key:"
    cat "${SSH_KEY_PATH}.pub"
    echo ""
fi

echo ""
echo "====================================="
echo "  OCI ARM Instance Retry (Cloud Shell)"
echo "====================================="
echo "Shape:    $SHAPE ($OCPUS OCPU, ${MEMORY_GB}GB RAM)"
echo "Image:    Ubuntu 24.04 Minimal aarch64"
echo "Boot:     ${BOOT_VOLUME_SIZE_GB}GB"
echo "AD:       $AVAILABILITY_DOMAIN"
echo "SSH Key:  $SSH_KEY_PATH"
echo "Retry:    Every ${RETRY_INTERVAL}s"
echo "====================================="
echo ""
echo "Press Ctrl+C to stop."
echo ""

# Check if instance already exists
echo "[*] Checking for existing instances..."
EXISTING=$(oci compute instance list \
    --compartment-id "$COMPARTMENT_ID" \
    --lifecycle-state RUNNING \
    --display-name "$DISPLAY_NAME" \
    --output json 2>/dev/null)

if [ -n "$EXISTING" ] && [ "$EXISTING" != "[]" ] && echo "$EXISTING" | grep -q '"id"'; then
    echo "[!] Instance '$DISPLAY_NAME' already exists and is RUNNING!"
    echo "$EXISTING" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, dict):
    data = data.get('data', [])
for inst in data:
    print(f\"  ID: {inst['id']}\")
    print(f\"  State: {inst['lifecycle-state']}\")
" 2>/dev/null || echo "$EXISTING"
    echo ""
    echo "Delete it first if you want to re-create, or Ctrl+C to exit."
    exit 0
fi

ATTEMPT=0

while true; do
    ATTEMPT=$((ATTEMPT + 1))
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo -n "[$TIMESTAMP] Attempt #$ATTEMPT ..."

    # Launch instance
    RESULT=$(oci compute instance launch \
        --compartment-id "$COMPARTMENT_ID" \
        --availability-domain "$AVAILABILITY_DOMAIN" \
        --subnet-id "$SUBNET_ID" \
        --image-id "$IMAGE_ID" \
        --shape "$SHAPE" \
        --shape-config "{\"ocpus\":$OCPUS,\"memoryInGBs\":$MEMORY_GB}" \
        --boot-volume-size-in-gbs "$BOOT_VOLUME_SIZE_GB" \
        --display-name "$DISPLAY_NAME" \
        --ssh-authorized-keys-file "${SSH_KEY_PATH}.pub" \
        --assign-public-ip true \
        --output json 2>&1)

    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ] && echo "$RESULT" | grep -q '"id"'; then
        echo " LAUNCHED!"
        echo ""

        # Parse instance details
        INSTANCE_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null)
        echo "Instance ID: $INSTANCE_ID"
        echo "Waiting for RUNNING state..."

        WAITED=0
        MAX_WAIT=300

        while [ $WAITED -lt $MAX_WAIT ]; do
            sleep 15
            WAITED=$((WAITED + 15))

            STATE_JSON=$(oci compute instance get --instance-id "$INSTANCE_ID" --output json 2>/dev/null)
            STATE=$(echo "$STATE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['lifecycle-state'])" 2>/dev/null)
            echo "  [${WAITED}s] State: $STATE"

            if [ "$STATE" = "RUNNING" ]; then
                break
            fi
            if [ "$STATE" = "TERMINATED" ] || [ "$STATE" = "TERMINATING" ]; then
                echo "  Instance terminated unexpectedly."
                break
            fi
        done

        if [ "$STATE" = "RUNNING" ]; then
            # Get public IP
            VNICS=$(oci compute vnic-attachment list \
                --compartment-id "$COMPARTMENT_ID" \
                --instance-id "$INSTANCE_ID" \
                --output json 2>/dev/null)
            VNIC_ID=$(echo "$VNICS" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['vnic-id'])" 2>/dev/null)

            PUBLIC_IP=""
            if [ -n "$VNIC_ID" ]; then
                VNIC_DATA=$(oci network vnic get --vnic-id "$VNIC_ID" --output json 2>/dev/null)
                PUBLIC_IP=$(echo "$VNIC_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['public-ip'])" 2>/dev/null)
            fi

            echo ""
            echo "====================================="
            echo "  SUCCESS! Instance is RUNNING!"
            echo "====================================="
            echo "  Instance: $INSTANCE_ID"
            if [ -n "$PUBLIC_IP" ]; then
                echo "  IP:       $PUBLIC_IP"
                echo "  Connect:  ssh -i $SSH_KEY_PATH ubuntu@$PUBLIC_IP"
            fi
            echo "  SSH Key:  $SSH_KEY_PATH"
            echo "====================================="

            # Save connection details to file for easy reference
            cat > "$HOME/oci-instance-details.txt" <<DETAILS
OCI ARM Instance Details
========================
Instance ID: $INSTANCE_ID
Public IP:   $PUBLIC_IP
SSH Command: ssh -i $SSH_KEY_PATH ubuntu@$PUBLIC_IP
Created:     $(date)
DETAILS
            echo ""
            echo "Details saved to ~/oci-instance-details.txt"
            break
        fi
    else
        # Check error type
        if echo "$RESULT" | grep -qi "Out of host capacity\|InternalError"; then
            echo " Out of capacity. Waiting ${RETRY_INTERVAL}s..."
        elif echo "$RESULT" | grep -qi "LimitExceeded\|TooManyRequests"; then
            echo " Rate limited. Waiting ${RETRY_INTERVAL}s..."
        else
            echo " Error:"
            echo "$RESULT" | head -5
            echo "Retrying in ${RETRY_INTERVAL}s..."
        fi

        sleep "$RETRY_INTERVAL"
    fi
done
