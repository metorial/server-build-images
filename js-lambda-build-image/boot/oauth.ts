import { delay } from './delay';

let getOauth = async () => {
  let prom = globalThis.__metorial_getMcpAuth__();
  return await Promise.race([prom, delay(500)]);
};

export let oauth = {
  get: getOauth
};
