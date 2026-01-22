/**
 * API服务 - 封装所有后端API调用
 */
import axios, { type AxiosResponse } from 'axios';
import type {
  ApiResponse,
  AnalysisResult,
  SubscriptionStock,
  OptionsData,
  IndicatorInfoResponse,
} from '../types/index';

// API基础URL
// 规则：
// - 浏览器环境：默认走当前域名（通常由 Nginx 代理），使用相对路径
// - Tauri 环境：必须使用绝对路径，优先环境变量，其次回退到本地 Nginx 端口 8086
const getApiBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_URL;
  const isHttps = window.location.protocol === 'https:';
  const isTauri = (window as any).__TAURI_INTERNALS__ !== undefined;
  const hostname = window.location.hostname;
  const ua = navigator.userAgent || '';
  const isAndroid = /Android/.test(ua);
  const isLocalHost =
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname === '0.0.0.0' ||
    hostname === 'tauri.localhost';

  if (isTauri) {
    if (envUrl) {
      let url = envUrl;
      if (isAndroid && (url.includes('localhost') || url.includes('127.0.0.1'))) {
        url = url.replace('localhost', '10.0.2.2').replace('127.0.0.1', '10.0.2.2');
      }
      if (isHttps && url.startsWith('http://')) {
        url = url.replace('http://', 'https://');
      }
      return url;
    }
    if (isAndroid) {
      return isHttps ? 'https://10.0.2.2:8086' : 'http://10.0.2.2:8086';
    }
    return isHttps ? 'https://localhost:8086' : 'http://localhost:8086';
  }

  if (envUrl && isLocalHost) {
    let url = envUrl;
    if (isHttps && url.startsWith('http://')) {
      url = url.replace('http://', 'https://');
    }
    return url;
  }

  return '';
};

const API_BASE_URL = getApiBaseUrl();

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

// ============= AI 聊天会话管理 API =============

/**
 * 会话信息接口
 */
export interface ChatSession {
  session_id: string;
  summary: string | null;
  model: string | null;
  context_symbols: string[];
  message_count: number;
  last_message: {
    role: string;
    content: string;
    created_at: string;
  } | null;
  created_at: string;
  updated_at: string;
}

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

/**
 * 获取热门股票列表（仅美股）
 */
export const getChatSessions = async (): Promise<ChatSession[]> => {
  try {
    const response = await api.get('/api/chat/sessions/');
    return response.data.sessions;
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 创建新会话
 * @param model - 使用的模型名称（可选）
 */
export const createChatSession = async (model?: string): Promise<ChatSession> => {
  try {
    const response = await api.post('/api/chat/sessions/', { model });
    return response.data.session;
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 获取会话详情
 */
export const getChatSessionDetail = async (sessionId: string) => {
  try {
    const response = await api.get(`/api/chat/sessions/${sessionId}/`);
    return response.data.session;
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 删除会话
 */
export const deleteChatSession = async (sessionId: string): Promise<void> => {
  try {
    await api.delete(`/api/chat/sessions/${sessionId}/`);
  } catch (error) {
    handleError(error);
    throw error;
  }
};
