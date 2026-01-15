/**
 * API服务 - 封装所有后端API调用
 */
import axios, { type AxiosResponse } from 'axios';
import type {
  ApiResponse,
  AnalysisResult,
  HotStock,
  IndicatorInfoResponse,
  NewsItem,
  OptionsData,
} from '../types/index';

// API基础URL
// 规则：
// - 浏览器环境：默认走当前域名（通常由 Nginx 代理），使用相对路径
// - Tauri 环境：必须使用绝对路径，优先环境变量，其次回退到本地 Nginx 端口 8086
const getApiBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_URL;
  const isHttps = window.location.protocol === 'https:';
  const isTauri = (window as any).__TAURI_INTERNALS__ !== undefined;

  if (envUrl) {
    let url = envUrl;
    // 如果页面是 HTTPS，强制将 http:// 升级为 https://
    if (isHttps && url.startsWith('http://')) {
      url = url.replace('http://', 'https://');
    }
    return url;
  }
  
  // Tauri 环境下必须显式指定 HTTP 地址，默认指向本机 Nginx 8086
  if (isTauri) {
    return isHttps ? 'https://localhost:8086' : 'http://localhost:8086';
  }

  // 浏览器环境：始终使用相对路径，交给 Nginx 或当前前端服务器转发
  // 例如：/api/xxx -> 由 Nginx 代理到后端
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
    const response = await api.get<ApiResponse<OptionsData>>(`/api/options/${symbol.toUpperCase()}`);
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 获取股票新闻
 */
export const getNews = async (symbol: string): Promise<ApiResponse<NewsItem[]>> => {
  try {
    const response = await api.get<ApiResponse<NewsItem[]>>(`/api/news/${symbol.toUpperCase()}`);
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
    const response = await api.get(`/api/search?${params.toString()}`);
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
    const response = await api.get('/api/chat/sessions');
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
    const response = await api.post('/api/chat/sessions', { model });
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
    const response = await api.get(`/api/chat/sessions/${sessionId}`);
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
    await api.delete(`/api/chat/sessions/${sessionId}/delete`);
  } catch (error) {
    handleError(error);
    throw error;
  }
};
