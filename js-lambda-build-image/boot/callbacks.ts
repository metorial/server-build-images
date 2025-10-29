import { delay } from './delay';

let getCallbacks = async () => {
  let prom = globalThis.__metorial_getCallbackHandler__();
  return await Promise.race([prom, delay(500)]);
};

export let callbacks = {
  get: getCallbacks
};
