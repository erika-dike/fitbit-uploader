#!/bin/bash

# Fitbit Uploader Deployment Script
# Usage: ./deploy.sh [server-ip-or-hostname]

set -e

SCRIPT_DIR="$(dirname "$0")"
PROJECT_DIR="$SCRIPT_DIR/../.."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration — set these env vars or pass server as first arg
SERVER="${1:-$DEPLOY_SERVER}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
USER="root"
APP_DIR="/opt/fitbit-uploader"
SERVICE_NAME="fitbit-uploader"

if [ -z "$SERVER" ]; then
    echo -e "${RED}Error: Pass server IP as argument or set DEPLOY_SERVER env var${NC}"
    exit 1
fi

SSH_OPTS="-i $SSH_KEY"

echo -e "${GREEN}Deploying Fitbit Uploader to $SERVER${NC}"

# Step 1: Sync project files to server
echo -e "${YELLOW}Uploading project files...${NC}"
ssh $SSH_OPTS $USER@$SERVER "mkdir -p $APP_DIR"
rsync -avz -e "ssh $SSH_OPTS" \
            --exclude='venv/' \
            --exclude='__pycache__/' \
            --exclude='.env' \
            --exclude='tokens.json' \
            --exclude='*.json' \
            --exclude='.git/' \
            --exclude='.claude/' \
            --exclude='PLAN.md' \
            "$PROJECT_DIR/" $USER@$SERVER:$APP_DIR/
echo -e "${GREEN}Upload complete${NC}"

# Step 2: Set up venv and install dependencies on server
echo -e "${YELLOW}Installing dependencies...${NC}"
ssh $SSH_OPTS $USER@$SERVER "cd $APP_DIR && python3 -m venv venv && venv/bin/pip install -r requirements.txt"
echo -e "${GREEN}Dependencies installed${NC}"

# Step 3: Restart service
echo -e "${YELLOW}Restarting service...${NC}"
ssh $SSH_OPTS $USER@$SERVER "systemctl restart $SERVICE_NAME"
echo -e "${GREEN}Service restarted${NC}"

# Step 4: Check status
echo -e "${YELLOW}Service status:${NC}"
ssh $SSH_OPTS $USER@$SERVER "systemctl status $SERVICE_NAME --no-pager" || true

# Step 5: Show recent logs
echo -e "${YELLOW}Recent logs:${NC}"
ssh $SSH_OPTS $USER@$SERVER "journalctl -u $SERVICE_NAME -n 20 --no-pager"

echo -e "${GREEN}Deployment complete!${NC}"
