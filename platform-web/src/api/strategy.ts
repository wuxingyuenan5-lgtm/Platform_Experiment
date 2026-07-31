import { defHttp } from '@/utils/http/axios';

enum Api {
  EXECUTIONHISTORY = '/strategy/api/v1/executionHistory/',
  EXECUTIONFEEDBACK = '/strategy/api/v1/executionFeedback/',
  INSTRUCTION = '/strategy/api/v1/instruction/',
  ISSUEINSTRUCTION = '/strategy/api/v1/issueInstruction/',
  EXECUTEINSTRUCTION = '/strategy/api/v1/executeInstruction/',
}
export const getExecutionHistory = (params?: any) =>
  defHttp.get({ url: Api.EXECUTIONHISTORY, params });

export const getExecutionfeedback = (params?: any) =>
  defHttp.get({ url: Api.EXECUTIONFEEDBACK, params });

export const getInstruction = (params?: any) => defHttp.get({ url: Api.INSTRUCTION, params });

export const postInstruction = (data?: any) => defHttp.post({ url: Api.INSTRUCTION, data });

export const getExecuteInstruction = (params?: any) =>
  defHttp.get({ url: Api.EXECUTEINSTRUCTION, params });

export const postExecuteInstruction = (data?: any) =>
  defHttp.post({ url: Api.EXECUTEINSTRUCTION, data });

export const getIssueInstruction = (params?: any) =>
  defHttp.get({ url: Api.ISSUEINSTRUCTION, params });

export const postIssueInstruction = (data?: any) =>
  defHttp.post({ url: Api.ISSUEINSTRUCTION, data });
