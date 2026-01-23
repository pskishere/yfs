import { api, handleResponse, handleError } from '../../services/api';
import type { AnalysisResult, SubscriptionStock, OptionsData, ApiResponse } from '../../types';

/**
 * 技术分析 - 获取数据并保存到数据库（不包含AI分析）
 * @param symbol - 股票代码
 * @param duration - 数据周期，默认 '5y'
 * @param barSize - K线周期，默认 '1 day'
 * @param modules - 需要加载的模块列表 (可选)
 */
export const analyze = async (
  symbol: string,
  duration: string = '5y',
  barSize: string = '1 day',
  modules: string[] = []
): Promise<AnalysisResult> => {
  try {
    const params = new URLSearchParams({
      duration: duration,
      bar_size: barSize,
    });
    
    if (modules && modules.length > 0) {
      params.append('modules', modules.join(','));
    }

    const response = await api.get<AnalysisResult>(
      `/api/stocks/${symbol.toUpperCase()}/?${params.toString()}`,
      {
        timeout: 60000, // 数据获取超时时间60秒
      }
    );
    return handleResponse<AnalysisResult>(response) as AnalysisResult;
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 查询分析状态
 */
export const getAnalysisStatus = async (
  symbol: string,
  duration: string = '5y',
  barSize: string = '1 day'
): Promise<AnalysisResult> => {
  try {
    const params = new URLSearchParams({
      duration: duration,
      bar_size: barSize,
    });
    const response = await api.get<AnalysisResult>(
      `/api/stocks/${symbol.toUpperCase()}/status/?${params.toString()}`
    );
    return handleResponse<AnalysisResult>(response) as AnalysisResult;
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 获取订阅股票列表（仅美股）
 */
export const getSubscriptions = async (): Promise<ApiResponse<SubscriptionStock[]>> => {
  try {
    const response = await api.get<ApiResponse<SubscriptionStock[]>>(
      `/api/stocks/subscriptions/`
    );
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 删除股票缓存数据
 */
export const deleteStock = async (symbol: string): Promise<ApiResponse> => {
  try {
    const response = await api.delete<ApiResponse>(`/api/stocks/${symbol.toUpperCase()}`);
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 刷新分析 - 强制重新获取数据，不使用缓存（不包含AI分析）
 * @param symbol - 股票代码
 * @param duration - 数据周期，默认 '5y'
 * @param barSize - K线周期，默认 '1 day'
 */
export const refreshAnalyze = async (
  symbol: string,
  duration: string = '5y',
  barSize: string = '1 day'
): Promise<AnalysisResult> => {
  try {
    const params = new URLSearchParams({
      duration: duration,
      bar_size: barSize,
    });

    const response = await api.post<AnalysisResult>(
      `/api/stocks/${symbol.toUpperCase()}/refresh/?${params.toString()}`,
      {},
      {
        timeout: 60000, // 刷新超时时间60秒
      }
    );
    return handleResponse<AnalysisResult>(response) as AnalysisResult;
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 获取期权数据
 */
export const getOptions = async (symbol: string): Promise<ApiResponse<OptionsData>> => {
  try {
    const response = await api.get<ApiResponse<OptionsData>>(`/api/stocks/${symbol.toUpperCase()}/options/`);
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 搜索股票代码
 * @param query - 关键词
 */
export const searchStocks = async (query: string): Promise<{ success: boolean; results: any[] }> => {
  try {
    const params = new URLSearchParams({ q: query });
    const response = await api.get(`/api/stocks/search/?${params.toString()}`);
    const data = handleResponse(response);
    return { success: data.success, results: data.results || [] };
  } catch (error) {
    handleError(error);
    throw error;
  }
};
