# 🤖 BandhanAI - AI-Powered Customer Relationship Management Agent

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-green.svg)](https://github.com/langchain-ai/langgraph)
[![LangChain](https://img.shields.io/badge/LangChain-Latest-yellow.svg)](https://github.com/langchain-ai/langchain)
[![License](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)

BandhanAI is an intelligent customer service and marketing automation agent designed specifically for Indian e-commerce platforms. Built with LangGraph and LangChain, it leverages AI to understand customer behavior, create targeted marketing campaigns, and automate customer communications through email and Slack integrations.

## ✨ Features

### 🎯 **Smart Customer Analytics**
- **Customer Segmentation**: Automatically categorize customers based on behavior, purchase history, and engagement
- **Churn Risk Analysis**: Identify at-risk customers and proactively engage them
- **Purchase Pattern Recognition**: Understand customer preferences and buying cycles

### 📧 **Advanced Email Marketing**
- **Personalized Campaigns**: Create highly targeted email campaigns based on customer data
- **HTML Email Templates**: Send beautifully formatted HTML emails
- **Campaign Types**: Support for 9 different campaign types (loyalty, referral, re-engagement, etc.)
- **Gmail Integration**: Seamless email sending through MCP Gmail server (Pinedream)

### 💬 **Slack Integration**
- **Real-time Updates**: Share campaign status and insights with your team
- **Error Reporting**: Automatic error notifications and issue reporting
- **Success Celebrations**: Share milestones and achievements

### 🔄 **Intelligent Automation**
- **LangGraph Workflows**: Advanced AI agent workflows with human-in-the-loop capabilities
- **Database Integration**: Direct connection to Supabase PostgreSQL for real-time data access
- **MCP Architecture**: Modular Component Protocol for extensible integrations

## 🏗️ Architecture

```
BandhanAI/
├── 📁 .langgraph_api/          # LangGraph API configurations
├── 📄 config.py               # Environment and path configuration
├── 📄 main.py                 # Main application entry point
├── 📄 prompts.py              # AI agent system prompts
├── 📄 server.py               # MCP marketing server
├── 📄 graph.py                # LangGraph workflow definitions
├── 📄 frontend.py             # Web interface (if applicable)
├── 📄 example_mcp_config.json # MCP server configuration template
├── 📄 langgraph.json          # LangGraph project configuration
└── 📄 requirements.txt        # Python dependencies
```

## 🚀 Quick Start

### Prerequisites

- Python 3.13 or higher
- PostgreSQL database (Supabase recommended)
- Gmail account for email sending
- Slack workspace for notifications
- Google Gemini API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/MohammedMusharraf11/BandhanAI.git
   cd BandhanAI
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Setup**
   
   Create a `.env` file in the root directory:
   ```env
   # Database Configuration
   SUPABASE_URI=postgresql://your_username:your_password@your_host:5432/your_database
   
   # Google Gemini API
   GOOGLE_API_KEY=your_gemini_api_key
   
   # Slack Integration
   SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
   SLACK_CHANNEL_ID=your_channel_id
   
 
   ```

4. **Database Setup**
   
   Ensure your PostgreSQL database has the required tables:
   ```sql
   -- Customer data table
   CREATE TABLE public.crm (
     customer_id bigint NOT NULL,
     name text NOT NULL,
     email text NOT NULL,
     region text,
     age bigint,
     income bigint,
     segment text,
     last_purchase timestamp without time zone,
     total_spend double precision,
     product_category text,
     churn_risk double precision,
     feedback_score double precision,
     products text[],
     CONSTRAINT crm_pkey PRIMARY KEY (customer_id)
   );
   
   -- Marketing campaigns table
   CREATE TABLE public.marketing_campaigns (
     id uuid NOT NULL DEFAULT gen_random_uuid(),
     name text NOT NULL,
     type text CHECK (type = ANY (ARRAY['loyalty'::text, 'referral'::text, 're-engagement'::text, 'at risk'::text, 'new customer'::text, 'champion'::text, 'about to sleep'::text, 'lost'::text, 'potential loyalist'::text])),
     description text,
     status text DEFAULT 'draft'::text,
     created_at timestamp without time zone DEFAULT now(),
     CONSTRAINT marketing_campaigns_pkey PRIMARY KEY (id)
   );
   
   -- Campaign emails table
   CREATE TABLE public.campaigning_emails (
     id bigserial NOT NULL,
     campaign_id uuid NOT NULL REFERENCES public.marketing_campaigns(id),
     customer_id bigint NOT NULL,
     email text NOT NULL,
     subject text NOT NULL,
     body text NOT NULL,
     sent_at timestamp without time zone DEFAULT now(),
     status text DEFAULT 'sent'::text,
     opened boolean NOT NULL DEFAULT false,
     CONSTRAINT campaigning_emails_pkey PRIMARY KEY (id)
   );
   ```

5. **Configure MCP Servers**
   
   Copy `example_mcp_config.json` to `mcp_config.json` and update with your settings:
   ```json
   {
    "mcpServers": {


      "postgres": {
        "command": "npx",
        "args": [
          "-y",
          "@modelcontextprotocol/server-postgres",
          "${SUPABASE_URI}"
        ],
        "transport": "stdio"
      },


      "marketing": {
        "command": "python",
        "args": [
            "server.py"
        ],
        "transport": "stdio"
      },

      
      "slack": {
        "command": "npx",
        "args": [
          "-y",
          "@modelcontextprotocol/server-slack"
        ],
        "env": {
          "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}",
          "SLACK_TEAM_ID": "${SLACK_TEAM_ID}",
          "SLACK_CHANNEL_IDS": "CHANNEL-ID"
        },
        "transport": "stdio"
      },

      "pd": {
      "command": "npx",
      "args": [
        "-y",
        "supergateway",
        "--sse"
        
      ],
      "transport": "sse",
      "url": "https://mcp.pipedream.net/API-KEY/gmail"
   
    }
    }
    ```


### Running the Application

1. **Start the main application**
   ```bash
   python main.py
   ```

2. **Interact with Ralph (the AI agent)**
   ```
   ---- 🤖 Assistant ----
   
   Hello! I'm Ralph, your AI-powered customer service and marketing automation agent for BandhanAI...
   
   User: Analyze our high-value customers and create a loyalty campaign
   ```

## 🎯 Campaign Types

BandhanAI supports 9 different marketing campaign types:

| Campaign Type | Description | Target Audience |
|---------------|-------------|-----------------|
| **Loyalty** | Thank high-value customers | Long-term, high-spending customers |
| **Referral** | Encourage customer referrals | Satisfied, engaged customers |
| **Re-engagement** | Win back inactive customers | Customers with no recent purchases |
| **At Risk** | Prevent customer churn | High churn risk score customers |
| **New Customer** | Welcome and onboard | Recently acquired customers |
| **Champion** | Reward best customers | Top-tier customers |
| **About to Sleep** | Re-activate before churn | Declining engagement customers |
| **Lost** | Win back churned customers | Churned customers |
| **Potential Loyalist** | Nurture promising customers | New customers with high potential |

## 💡 Usage Examples

### Creating a Customer Segment Analysis
```
User: Analyze our customers who haven't purchased in the last 3 months and have a high churn risk
```

### Launching a Re-engagement Campaign
```
User: Create a re-engagement campaign for customers in the Mumbai region who haven't bought anything in 60 days
```

### Sending Personalized Emails
```
User: Send a loyalty email to our top 10 customers thanking them for their continued support
```

### Slack Reporting
```
User: Post a summary of today's campaign performance to our marketing Slack channel
```

## 🛠️ Technology Stack

- **AI Framework**: LangGraph + LangChain for intelligent workflows
- **LLM**: Google Gemini for natural language processing
- **Database**: Supabase (PostgreSQL) for customer data
- **Email Service**: Gmail via MCP (Pinedream)
- **Communication**: Slack API for team notifications
- **Architecture**: MCP (Model Context Protocol) for modular integrations

## 🔧 Configuration

### MCP Server Configuration

The application uses MCP servers for external integrations:

- **Marketing Server**: Handles campaign creation and email sending
- **Gmail Server**: Manages email delivery through Pinedream MCP
- **Slack Server**: Handles team notifications and updates

### Agent Configuration

Ralph (the AI agent) can be configured through `prompts.py`:

- **System Prompt**: Defines the agent's personality and capabilities
- **Database Schema**: Provides context about available data
- **Campaign Types**: Defines available marketing campaign types
- **Email Templates**: Configures email formatting and personalization

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by [crm-agent](https://github.com/kenneth-liao/crm-agent) by Kenneth Liao
- Built with [LangGraph](https://github.com/langchain-ai/langgraph) and [LangChain](https://github.com/langchain-ai/langchain)
- Email integration powered by [Pinedream MCP](https://mcp.pipedream.com/app/gmail)

## 📞 Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/MohammedMusharraf11/BandhanAI/issues) page
2. Create a new issue with detailed information
3. Join our community discussions

---

**Built with ❤️ for the Indian e-commerce ecosystem**
