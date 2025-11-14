import type { Client } from '@modelcontextprotocol/sdk/client/index.js';
import type { Prompt, ResourceTemplate, Tool } from '@modelcontextprotocol/sdk/types.js';

export let discover = async (client: Client) => {
  let tools: Tool[] = [];
  let resourceTemplates: ResourceTemplate[] = [];
  let prompts: Prompt[] = [];

  try {
    let toolsRes = await client.listTools();
    tools.push(...toolsRes.tools);
    while ((toolsRes._meta as any)?.progressToken) {
      toolsRes = await client.listTools({
        progressToken: toolsRes._meta!.progressToken
      } as any);
      tools.push(...toolsRes.tools);
    }
  } catch (e) {}

  try {
    let resourceTemplatesRes = await client.listResourceTemplates();
    resourceTemplates.push(...resourceTemplatesRes.resourceTemplates);
    while ((resourceTemplatesRes._meta as any)?.progressToken) {
      resourceTemplatesRes = await client.listResourceTemplates({
        pageToken: resourceTemplatesRes._meta!.progressToken
      } as any);
      resourceTemplates.push(...resourceTemplatesRes.resourceTemplates);
    }
  } catch (e) {}

  try {
    let promptsRes = await client.listPrompts();
    prompts.push(...promptsRes.prompts);
    while ((promptsRes._meta as any)?.progressToken) {
      promptsRes = await client.listPrompts({
        pageToken: promptsRes._meta!.progressToken
      } as any);
      prompts.push(...promptsRes.prompts);
    }
  } catch (e) {}

  return {
    tools,
    resourceTemplates,
    prompts,
    instructions: client.getInstructions(),
    capabilities: client.getServerCapabilities(),
    implementation: client.getServerVersion()
  };
};
