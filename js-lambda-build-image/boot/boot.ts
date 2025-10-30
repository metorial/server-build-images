import './config';

import { McpError } from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';
import { callbacks } from './callbacks';
import { delay } from './delay';
import { discover } from './discover';
import { OutputInstrumentation } from './logs';
import { oauth } from './oauth';
import { getClient } from './server';

interface LambdaEvent {
  action: 'discover' | 'mcp.request' | 'mcp.batch' | 'oauth' | 'callbacks';

  messages?: string[];

  clientInfo?: {
    name: string;
    version: string;
  };

  args?: Record<string, any>;

  token?: string;

  oauthAction?: 'get' | 'authorization-url' | 'authorization-form' | 'refresh' | 'callback';
  oauthInput?: any;

  callbackAction?: 'get' | 'handle' | 'install' | 'poll';
  callbackInput?: any;
}

interface LambdaResponse {
  success: boolean;

  responses?: Array<{
    jsonrpc: '2.0';
    id?: string | number;
    result?: any;
    error?: {
      code: number;
      message: string;
      data?: any;
    };
  }>;

  discovery?: any;

  oauth?: any;

  callbacks?: any;

  logs?: Array<{
    type: 'info' | 'error';
    lines: string[];
  }>;

  error?: {
    code: string;
    message: string;
  };
}

export let handler = async (event: LambdaEvent): Promise<LambdaResponse> => {
  let args = event.args || {};
  if (typeof globalThis.__metorial_setArgs__ === 'function') {
    globalThis.__metorial_setArgs__(args);
  }

  let capturedLogs: Array<{ type: 'info' | 'error'; lines: string[] }> = [];
  let outputInstrumentation = new OutputInstrumentation(lines => {
    capturedLogs.push(...lines);
  });

  // @ts-ignore
  await import('$$ENTRY_POINT$$');

  try {
    switch (event.action) {
      case 'discover':
        return await handleDiscover(event, capturedLogs);

      case 'mcp.request':
      case 'mcp.batch':
        return await handleMcpRequests(event, capturedLogs);

      case 'oauth':
        return await handleOAuth(event, capturedLogs);

      case 'callbacks':
        return await handleCallbacks(event, capturedLogs);

      default:
        return {
          success: false,
          logs: capturedLogs,
          error: {
            code: 'invalid_action',
            message: `Unknown action: ${event.action}`
          }
        };
    }
  } catch (error: any) {
    console.error(error);

    return {
      success: false,
      logs: capturedLogs,
      error: {
        code: 'execution_error',
        message: error?.message || String(error)
      }
    };
  } finally {
    outputInstrumentation.drain();
    outputInstrumentation.restore();
  }
};

let handleDiscover = async (
  event: LambdaEvent,
  logs: Array<{ type: 'info' | 'error'; lines: string[] }>
): Promise<LambdaResponse> => {
  let client = await getClient(event.args || {}, {
    client: event.clientInfo || { name: 'Metorial Auto Discover', version: '0.1.0' },
    capabilities: {},
    notificationListener: async () => {}
  });

  let discovery = await discover(client);

  return {
    success: true,
    discovery,
    logs
  };
};

let handleMcpRequests = async (
  event: LambdaEvent,
  logs: Array<{ type: 'info' | 'error'; lines: string[] }>
): Promise<LambdaResponse> => {
  if (!event.messages || event.messages.length === 0) {
    return {
      success: false,
      logs,
      error: {
        code: 'invalid_request',
        message: 'No messages provided'
      }
    };
  }

  let notifications: any[] = [];
  let client = await getClient(event.args || {}, {
    client: event.clientInfo || { name: 'Unknown', version: '0.0.0' },
    capabilities: {},
    notificationListener: async notification => {
      notifications.push(notification);
    }
  });

  let responses = await Promise.all(
    event.messages.map(async messageRaw => {
      let message = JSON.parse(messageRaw);

      try {
        if ('id' in message) {
          let result = await client.request(message as any, z.any(), {
            timeout: 30000
          });

          return {
            jsonrpc: '2.0' as const,
            id: message.id!,
            result
          };
        } else {
          await client.notification(message as any);
          return null;
        }
      } catch (error) {
        if (error instanceof McpError) {
          return {
            jsonrpc: '2.0' as const,
            id: message.id!,
            error: {
              code: error.code,
              message: error.message,
              data: error.data
            }
          };
        }

        return {
          jsonrpc: '2.0' as const,
          id: message.id!,
          error: {
            code: -32603,
            message: String(error)
          }
        };
      }
    })
  );

  await delay(100);

  return {
    success: true,
    responses: [...responses, ...notifications].filter(r => r !== null) as any,
    logs
  };
};

let handleOAuth = async (
  event: LambdaEvent,
  logs: Array<{ type: 'info' | 'error'; lines: string[] }>
): Promise<LambdaResponse> => {
  let oauthResult = await oauth.get();

  switch (event.oauthAction) {
    case 'get':
      return {
        success: true,
        oauth: {
          enabled: !!oauthResult,
          hasForm: !!oauthResult?.getAuthForm
        },
        logs
      };

    case 'authorization-url':
      if (!oauthResult) {
        return {
          success: false,
          logs,
          error: { code: 'oauth_not_configured', message: 'OAuth not configured' }
        };
      }
      try {
        let authUrlResRaw = await oauthResult.getAuthorizationUrl(event.oauthInput || {});
        let authUrlRes =
          typeof authUrlResRaw === 'string'
            ? { authorizationUrl: authUrlResRaw }
            : authUrlResRaw;
        return { success: true, oauth: authUrlRes, logs };
      } catch (error: any) {
        return {
          success: false,
          logs,
          error: {
            code: 'oauth_error',
            message: error?.message || 'Failed to get authorization URL'
          }
        };
      }

    case 'authorization-form':
      if (!oauthResult || !oauthResult.getAuthForm) {
        return {
          success: false,
          logs,
          error: { code: 'oauth_not_configured', message: 'OAuth form not available' }
        };
      }

      try {
        let authForm = await oauthResult.getAuthForm(event.oauthInput || {});
        return { success: true, oauth: { authForm }, logs };
      } catch (error: any) {
        return {
          success: false,
          logs,
          error: {
            code: 'oauth_error',
            message: error?.message || 'Failed to get authorization form'
          }
        };
      }

    case 'refresh':
      if (!oauthResult || !oauthResult.refreshAccessToken) {
        return {
          success: false,
          logs,
          error: { code: 'oauth_not_supported', message: 'Refresh not supported' }
        };
      }
      try {
        let authData = await oauthResult.refreshAccessToken(event.oauthInput || {});
        return { success: true, oauth: { authData }, logs };
      } catch (error: any) {
        return {
          success: false,
          logs,
          error: {
            code: 'oauth_error',
            message: error?.message || 'Failed to refresh access token'
          }
        };
      }

    case 'callback':
      if (!oauthResult) {
        return {
          success: false,
          logs,
          error: { code: 'oauth_not_configured', message: 'OAuth not configured' }
        };
      }
      try {
        let authData = await oauthResult.handleCallback(event.oauthInput || {});
        return { success: true, oauth: { authData }, logs };
      } catch (error: any) {
        return {
          success: false,
          logs,
          error: {
            code: 'oauth_error',
            message: error?.message || 'Failed to handle OAuth callback'
          }
        };
      }

    default:
      return {
        success: false,
        logs,
        error: { code: 'invalid_action', message: 'Invalid OAuth action' }
      };
  }
};

let handleCallbacks = async (
  event: LambdaEvent,
  logs: Array<{ type: 'info' | 'error'; lines: string[] }>
): Promise<LambdaResponse> => {
  let callbacksResult = await callbacks.get();

  switch (event.callbackAction) {
    case 'get':
      if (!callbacksResult) {
        return { success: true, callbacks: { enabled: false }, logs };
      }
      return {
        success: true,
        callbacks: {
          enabled: true,
          type: callbacksResult.installHook
            ? 'webhook'
            : callbacksResult.pollHook
            ? 'polling'
            : 'manual'
        },
        logs
      };

    case 'handle':
      if (!callbacksResult) {
        return {
          success: false,
          logs,
          error: { code: 'callbacks_not_configured', message: 'Callbacks not configured' }
        };
      }
      try {
        let input = event.callbackInput || {};
        let results = await Promise.all(
          (input.events || []).map(async (evt: any) => {
            try {
              let result = await callbacksResult.handleHook({
                callbackId: input.callbackId,
                ...evt
              });
              return { success: true, eventId: evt.eventId, result };
            } catch (error: any) {
              return {
                success: false,
                eventId: evt.eventId,
                error: error?.message || 'Failed to handle event'
              };
            }
          })
        );
        return { success: true, callbacks: { results }, logs };
      } catch (error: any) {
        return {
          success: false,
          logs,
          error: {
            code: 'callback_error',
            message: error?.message || 'Failed to handle callback'
          }
        };
      }

    case 'install':
      if (!callbacksResult || !callbacksResult.installHook) {
        return {
          success: false,
          logs,
          error: { code: 'callbacks_not_supported', message: 'Install not supported' }
        };
      }
      try {
        await callbacksResult.installHook(event.callbackInput || {});
        return { success: true, callbacks: {}, logs };
      } catch (error: any) {
        return {
          success: false,
          logs,
          error: {
            code: 'callback_error',
            message: error?.message || 'Failed to install callback'
          }
        };
      }

    case 'poll':
      if (!callbacksResult || !callbacksResult.pollHook) {
        return {
          success: false,
          logs,
          error: { code: 'callbacks_not_supported', message: 'Poll not supported' }
        };
      }
      try {
        let input = event.callbackInput || {};
        let state = input.state || null;
        let stateRef = { current: state };
        let setState = (v: any) => {
          stateRef.current = v;
        };

        let events = await callbacksResult.pollHook({
          ...input,
          state,
          setState
        });

        return {
          success: true,
          callbacks: {
            events: Array.isArray(events) ? events : [events],
            newState: stateRef.current
          },
          logs
        };
      } catch (error: any) {
        return {
          success: false,
          logs,
          error: {
            code: 'callback_error',
            message: error?.message || 'Failed to poll callbacks'
          }
        };
      }

    default:
      return {
        success: false,
        logs,
        error: { code: 'invalid_action', message: 'Invalid callback action' }
      };
  }
};

export default { handler };
