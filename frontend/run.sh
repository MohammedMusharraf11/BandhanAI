#!/bin/bash

# BandhanAI Frontend Setup Script
# Run from inside bandhan-ai/frontend/

set -e

echo "🚀 Setting up BandhanAI Next.js frontend..."

# ── 1. Scaffold Next.js ──────────────────────────────────────────────────────


# ── 2. Install dependencies ──────────────────────────────────────────────────
npm install \
  @supabase/supabase-js \
  @supabase/ssr \
  axios \
  zustand \
  lucide-react \
  clsx \
  tailwind-merge \
  class-variance-authority \
  @radix-ui/react-dialog \
  @radix-ui/react-toast \
  @radix-ui/react-dropdown-menu \
  @radix-ui/react-avatar \
  @radix-ui/react-separator \
  react-hot-toast \
  date-fns

echo "✅ Dependencies installed"

# ── 3. Create directory structure ────────────────────────────────────────────

# lib — shared utilities and clients
mkdir -p src/lib
touch src/lib/supabase.ts          # supabase browser client
touch src/lib/supabase-server.ts   # supabase server client (SSR)
touch src/lib/api.ts               # axios instance pointing to FastAPI backend
touch src/lib/websocket.ts         # WebSocket manager for Ralph chat
touch src/lib/utils.ts             # cn() helper and misc utils

# types
mkdir -p src/types
touch src/types/tenant.ts          # Tenant, AgentPersona types
touch src/types/campaign.ts        # Campaign, CampaignEmail types
touch src/types/customer.ts        # Customer, SchemaField types
touch src/types/websocket.ts       # WebSocket message types (mirrors frontend.py)

# store — zustand global state
mkdir -p src/store
touch src/store/auth-store.ts      # user session, org_id
touch src/store/chat-store.ts      # messages, typing state, approval requests
touch src/store/tenant-store.ts    # agent name, backstory, integrations status

# hooks
mkdir -p src/hooks
touch src/hooks/use-websocket.ts   # WebSocket connection + message handling
touch src/hooks/use-auth.ts        # session helpers
touch src/hooks/use-campaigns.ts   # fetch campaign history

# components — shared UI primitives
mkdir -p src/components/ui
touch src/components/ui/button.tsx
touch src/components/ui/input.tsx
touch src/components/ui/textarea.tsx
touch src/components/ui/badge.tsx
touch src/components/ui/card.tsx
touch src/components/ui/modal.tsx
touch src/components/ui/toast.tsx
touch src/components/ui/spinner.tsx
touch src/components/ui/avatar.tsx

# components — feature components
mkdir -p src/components/chat
touch src/components/chat/chat-window.tsx        # main chat container
touch src/components/chat/message-bubble.tsx     # individual message
touch src/components/chat/input-bar.tsx          # message input + send button
touch src/components/chat/typing-indicator.tsx   # Ralph is thinking...
touch src/components/chat/approval-modal.tsx     # human-in-the-loop modal

mkdir -p src/components/dashboard
touch src/components/dashboard/campaign-table.tsx    # campaign history
touch src/components/dashboard/stats-cards.tsx       # quick stats
touch src/components/dashboard/agent-card.tsx        # Ralph persona display

mkdir -p src/components/onboarding
touch src/components/onboarding/agent-setup-form.tsx  # name + backstory
touch src/components/onboarding/csv-upload.tsx         # upload + column preview
touch src/components/onboarding/schema-preview.tsx     # LLM-detected schema

mkdir -p src/components/settings
touch src/components/settings/gmail-connect.tsx    # OAuth connect button
touch src/components/settings/slack-connect.tsx    # OAuth connect button
touch src/components/settings/integration-status.tsx

mkdir -p src/components/layout
touch src/components/layout/sidebar.tsx
touch src/components/layout/topbar.tsx
touch src/components/layout/auth-guard.tsx        # redirect if not logged in

# app routes (Next.js App Router)
# auth
mkdir -p src/app/\(auth\)/login
touch src/app/\(auth\)/login/page.tsx
mkdir -p src/app/\(auth\)/signup
touch src/app/\(auth\)/signup/page.tsx

# onboarding
mkdir -p src/app/\(app\)/onboarding
touch src/app/\(app\)/onboarding/page.tsx

# dashboard
mkdir -p src/app/\(app\)/dashboard
touch src/app/\(app\)/dashboard/page.tsx

# chat
mkdir -p src/app/\(app\)/chat
touch src/app/\(app\)/chat/page.tsx

# settings
mkdir -p src/app/\(app\)/settings
touch src/app/\(app\)/settings/page.tsx

# app layout shells
touch src/app/\(auth\)/layout.tsx
touch src/app/\(app\)/layout.tsx

# API route handlers (Next.js route handlers)
mkdir -p src/app/api/auth/callback
touch src/app/api/auth/callback/route.ts         # Supabase auth callback

mkdir -p src/app/api/oauth/gmail
touch src/app/api/oauth/gmail/route.ts           # proxies to FastAPI Gmail OAuth

mkdir -p src/app/api/oauth/slack
touch src/app/api/oauth/slack/route.ts           # proxies to FastAPI Slack OAuth

# middleware for auth protection
touch src/middleware.ts

# env file
cat > .env.local << 'EOF'
# Supabase
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# FastAPI backend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
EOF

echo "✅ Directory structure created"
echo ""
echo "📁 Structure overview:"
echo ""
find src -type f | sort
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ BandhanAI frontend ready."
echo ""
echo "Next steps:"
echo "  1. Fill in .env.local with your Supabase URL and anon key"
echo "  2. Set NEXT_PUBLIC_API_URL to your FastAPI backend URL"
echo "  3. Run: npm run dev"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"