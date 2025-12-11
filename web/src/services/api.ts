/**
 * API服务 - 封装所有后端API调用
 */
import axios, { type AxiosResponse } from 'axios';
import type {
  ApiResponse,
  Position,
  Order,
  AnalysisResult,
  HotStock,
  IndicatorInfoResponse,
} from '../types/index';

// API基础URL - 在Docker环境中使用相对路径通过nginx反向代理
// 开发环境可通过 .env 设置 VITE_API_URL 指向本地后端
// 生产环境（Docker）使用相对路径，nginx会转发到后端
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// 创建axios实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 增加默认超时时间到60秒
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 处理API响应
 * 
 * @param response - Axios响应对象
 * @returns 解析后的响应数据
 */
const handleResponse = <T = any>(response: AxiosResponse<ApiResponse<T>>): ApiResponse<T> => {
  // 如果 response.data 是字符串，尝试解析为 JSON
  if (typeof response.data === 'string') {
    try {
      return JSON.parse(response.data);
    } catch (e) {
      console.error('解析响应数据失败:', e);
      throw new Error('服务器返回的数据格式错误');
    }
  }
  return response.data;
};

/**
 * 处理API错误
 * 
 * @param error - 错误对象
 * @throws 抛出带有错误信息的Error
 */
const handleError = (error: any): never => {
  if (error.response) {
    // 服务器返回了错误状态码
    throw new Error(error.response.data?.message || `请求失败: ${error.response.status}`);
  } else if (error.request) {
    // 请求已发出但没有收到响应
    throw new Error('无法连接到服务器，请检查后端服务是否运行');
  } else {
    // 其他错误
    throw new Error(error.message || '请求失败');
  }
};

/**
 * 获取持仓列表
 */
export const getPositions = async (): Promise<ApiResponse<Position[]>> => {
  try {
    const response = await api.get<ApiResponse<Position[]>>('/api/positions');
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 获取订单列表
 */
export const getOrders = async (): Promise<ApiResponse<Order[]>> => {
  try {
    const response = await api.get<ApiResponse<Order[]>>('/api/orders');
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 买入股票
 */
export const buy = async (
  symbol: string,
  quantity: number,
  limitPrice: number | null = null
): Promise<ApiResponse> => {
  try {
    const orderData: any = {
      symbol: symbol.toUpperCase(),
      action: 'BUY',
      quantity: quantity,
      order_type: limitPrice ? 'LMT' : 'MKT',
    };

    if (limitPrice) {
      orderData.limit_price = limitPrice;
    }

    const response = await api.post<ApiResponse>('/api/order', orderData);
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 卖出股票
 */
export const sell = async (
  symbol: string,
  quantity: number,
  limitPrice: number | null = null
): Promise<ApiResponse> => {
  try {
    const orderData: any = {
      symbol: symbol.toUpperCase(),
      action: 'SELL',
      quantity: quantity,
      order_type: limitPrice ? 'LMT' : 'MKT',
    };

    if (limitPrice) {
      orderData.limit_price = limitPrice;
    }

    const response = await api.post<ApiResponse>('/api/order', orderData);
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 撤销订单
 */
export const cancelOrder = async (orderId: number): Promise<ApiResponse> => {
  try {
    const response = await api.delete<ApiResponse>(`/api/order/${orderId}`);
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 技术分析 - 获取数据并保存到数据库（不包含AI分析）
 * @param symbol - 股票代码
 * @param duration - 数据周期，默认 '5y'
 * @param barSize - K线周期，默认 '1 day'
 */
export const analyze = async (
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
      `/api/analyze/${symbol.toUpperCase()}?${params.toString()}`,
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
      `/api/analysis-status/${symbol.toUpperCase()}?${params.toString()}`
    );
    return handleResponse<AnalysisResult>(response) as AnalysisResult;
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * AI分析 - 基于已保存的数据执行AI分析
 * 需要先调用 analyze 接口获取数据并保存到数据库
 * @param symbol - 股票代码
 * @param duration - 数据周期，默认 '5y'
 * @param barSize - K线周期，默认 '1 day'
 * @param model - AI模型名称，默认 'deepseek-v3.1:671b-cloud'
 */
export const aiAnalyze = async (
  symbol: string,
  duration: string = '5y',
  barSize: string = '1 day',
  model: string = 'deepseek-v3.1:671b-cloud'
): Promise<{ success: boolean; ai_analysis?: string; model?: string; ai_available?: boolean; cached?: boolean; message?: string; status?: string }> => {
  try {
    const params = new URLSearchParams({
      duration: duration,
      bar_size: barSize,
      model: model,
    });

    const response = await api.post<{ success: boolean; ai_analysis?: string; model?: string; ai_available?: boolean; cached?: boolean; message?: string; status?: string }>(
      `/api/ai-analyze/${symbol.toUpperCase()}?${params.toString()}`,
      {},
      {
        timeout: 10000, // 缩短超时时间，因为现在会立即返回
      }
    );
    return handleResponse(response);
  } catch (error: any) {
    // 如果是 202 状态码（Accepted），表示任务已开始，返回进行中状态
    if (error?.response?.status === 202) {
      return {
        success: false,
        message: error?.response?.data?.message || 'AI分析已开始，请稍后查询结果',
        status: 'running',
      };
    }
    handleError(error);
    throw error;
  }
};

/**
 * 获取热门股票列表（仅美股）
 * @param limit - 返回数量限制，默认 20
 */
export const getHotStocks = async (limit: number = 20): Promise<ApiResponse<HotStock[]>> => {
  try {
    const params = new URLSearchParams({
      limit: limit.toString(),
    });

    const response = await api.get<ApiResponse<HotStock[]>>(
      `/api/hot-stocks?${params.toString()}`
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
 * 获取技术指标解释和参考范围
 * @param indicator - 指标名称（可选），不提供则返回所有指标信息
 */
export const getIndicatorInfo = async (indicator: string = ''): Promise<IndicatorInfoResponse> => {
  try {
    const params = new URLSearchParams();
    if (indicator) {
      params.append('indicator', indicator);
    }

    const url = indicator
      ? `/api/indicator-info?${params.toString()}`
      : '/api/indicator-info';

    const response = await api.get<IndicatorInfoResponse>(url);
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
      `/api/refresh-analyze/${symbol.toUpperCase()}?${params.toString()}`,
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
