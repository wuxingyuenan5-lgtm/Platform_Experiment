import { resultSuccess } from '../_util';
import { MockMethod } from 'vite-plugin-mock';

const getTarget = (() => {
  const result: any = {
    location: '@integer(1,100000)',
    keep: '@integer(1,100)',
    init: '@integer(1,100)',
  };
  return result;
})();

export default [
  {
    url: '/basic-api/strategy/target',
    timeout: 100,
    method: 'get',
    response: () => {
      return resultSuccess(getTarget);
    },
  },
] as MockMethod[];
