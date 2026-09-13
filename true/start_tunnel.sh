#!/usr/bin/env bash
pkill -f "cloudflared tunnel" 2>/dev/null
sleep 2
cloudflared tunnel run 20e68f9f-2a5f-4dd6-bbd9-5e5341507dfe > /tmp/cfd_run.log 2>&1
