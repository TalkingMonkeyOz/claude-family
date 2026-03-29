#!/usr/bin/env node
/**
 * Claude Family Channel Messaging MCP Server
 *
 * Real-time inter-Claude messaging via PostgreSQL LISTEN/NOTIFY.
 * Runs as a channel MCP server (stdio transport) that listens for
 * database notifications and pushes them into the Claude session.
 *
 * Environment variables:
 *   DATABASE_URL - PostgreSQL connection string
 *   CLAUDE_PROJECT - Project name (auto-detected from CLAUDE_PROJECT_DIR or cwd)
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { ListToolsRequestSchema, CallToolRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import pg from 'pg';
import path from 'path';

const { Client } = pg;

// Detect project name from environment or current directory
const projectName = process.env.CLAUDE_PROJECT
  || path.basename(process.env.CLAUDE_PROJECT_DIR || process.cwd());

// Normalize project name for pg channel (lowercase, underscores)
const pgChannel = 'claude_msg_' + projectName.toLowerCase().replace(/-/g, '_');
const pgBroadcastChannel = 'claude_msg_broadcast';

// Database connection config
const dbConfig = process.env.DATABASE_URL
  ? { connectionString: process.env.DATABASE_URL }
  : {
      host: 'localhost',
      port: 5432,
      database: 'ai_company_foundation',
      user: 'postgres',
      password: process.env.PGPASSWORD || ''
    };

// Track connection state
let pgClient = null;
let isConnected = false;

// Create MCP server with channel capability — matches official docs pattern exactly
const mcp = new Server(
  { name: 'channel-messaging', version: '0.2.0' },
  {
    capabilities: {
      experimental: { 'claude/channel': {} },
      tools: {},
    },
    instructions: `You are receiving real-time messages from other Claude Family members via the messaging channel. Messages appear as <channel source="channel-messaging" ...> tags. When you receive a message: read it carefully, assess priority. For task_request or question types, respond using send_message() or reply_to(). For notifications, acknowledge with acknowledge(). Currently listening as project: ${projectName}`,
  },
);

// Register status tool
mcp.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [{
    name: 'channel_status',
    description: 'Check the real-time messaging channel connection status',
    inputSchema: {
      type: 'object',
      properties: {},
      required: []
    }
  }]
}));

mcp.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === 'channel_status') {
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          connected: isConnected,
          project: projectName,
          listening_channels: [pgChannel, pgBroadcastChannel],
          database: dbConfig.host || 'via DATABASE_URL'
        }, null, 2)
      }]
    };
  }
  throw new Error(`Unknown tool: ${request.params.name}`);
});

// Step 1: Connect MCP FIRST (official pattern — must be connected before notifications)
await mcp.connect(new StdioServerTransport());
process.stderr.write(`[channel-messaging] MCP connected for project: ${projectName}\n`);

// Step 2: THEN connect to PostgreSQL and start listening
try {
  pgClient = new Client(dbConfig);

  pgClient.on('notification', async (msg) => {
    process.stderr.write(`[channel-messaging] PG NOTIFY received on ${msg.channel}: ${msg.payload}\n`);
    try {
      const payload = JSON.parse(msg.payload);
      const from = payload.from_project || 'unknown';
      const subject = payload.subject ? `: ${payload.subject}` : '';
      const type = payload.message_type || 'notification';
      const content = `New ${type} from ${from}${subject}. Use check_inbox() to read the full message.`;

      process.stderr.write(`[channel-messaging] Sending notification to Claude: ${content}\n`);

      await mcp.notification({
        method: 'notifications/claude/channel',
        params: {
          content: content,
          meta: {
            from_project: from,
            message_type: type,
            priority: payload.priority || 'normal',
            message_id: payload.message_id
          }
        }
      });

      process.stderr.write(`[channel-messaging] Notification sent successfully\n`);
    } catch (err) {
      process.stderr.write(`[channel-messaging] ERROR sending notification: ${err.message}\n${err.stack}\n`);
    }
  });

  pgClient.on('error', (err) => {
    process.stderr.write(`[channel-messaging] PostgreSQL error: ${err.message}\n`);
    isConnected = false;
  });

  await pgClient.connect();
  isConnected = true;

  await pgClient.query(`LISTEN ${pgChannel}`);
  await pgClient.query(`LISTEN ${pgBroadcastChannel}`);

  process.stderr.write(`[channel-messaging] PostgreSQL connected, listening on ${pgChannel} and ${pgBroadcastChannel}\n`);

} catch (err) {
  process.stderr.write(`[channel-messaging] Failed to connect to PostgreSQL: ${err.message}\n`);
}

// Cleanup
process.on('SIGINT', async () => {
  if (pgClient) await pgClient.end().catch(() => {});
  process.exit(0);
});
process.on('SIGTERM', async () => {
  if (pgClient) await pgClient.end().catch(() => {});
  process.exit(0);
});
