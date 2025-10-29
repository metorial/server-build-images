import { ProgrammablePromise } from './promise';

export let currentOauth = new ProgrammablePromise();
globalThis.__metorial_setMcpAuth__ = (v: any) => currentOauth.resolve(v);
globalThis.__metorial_getMcpAuth__ = () => currentOauth.promise;

export let currentArgs = new ProgrammablePromise();
globalThis.__metorial_setArgs__ = (v: any) => currentArgs.resolve(v);
globalThis.__metorial_getArgs__ = () => currentArgs.promise;

export let currentServer = new ProgrammablePromise();
globalThis.__metorial_setServer__ = (v: any) => currentServer.resolve(v);
globalThis.__metorial_getServer__ = () => currentServer.promise;

export let currentHook = new ProgrammablePromise();
globalThis.__metorial_setCallbackHandler__ = (v: any) => currentHook.resolve(v);
globalThis.__metorial_getCallbackHandler__ = () => currentHook.promise;

declare global {
  // Define the global properties and their types
  var __metorial_setMcpAuth__: (v: any) => void;
  var __metorial_getMcpAuth__: () => Promise<any>;

  var __metorial_setArgs__: (v: any) => void;
  var __metorial_getArgs__: () => Promise<any>;

  var __metorial_setServer__: (v: any) => void;
  var __metorial_getServer__: () => Promise<any>;

  var __metorial_setCallbackHandler__: (v: any) => void;
  var __metorial_getCallbackHandler__: () => Promise<any>;
}

export {};
