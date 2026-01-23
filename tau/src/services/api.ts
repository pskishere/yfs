/**
 * API服务 - 封装所有后端API调用
 */
import axios, { type AxiosResponse } from 'axios';
import type {
  ApiResponse,
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
export const api = axios.create({
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
export const handleResponse = <T = any>(response: AxiosResponse<ApiResponse<T>>): ApiResponse<T> => {
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
export const handleError = (error: any): never => {
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

// ============= AI 聊天会话管理 API =============

/**
 * 会话信息接口
 */
export interface ChatSession {
  session_id: string;
  title: string | null;
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
 * 获取 AI 模型列表
 */
export interface AIModel {
  id: string;
  name: string;
  provider: string;
}

export const getAiModels = async (): Promise<AIModel[]> => {
  try {
    const response = await api.get('/api/chat/models/');
    const data = handleResponse(response);
    if (Array.isArray(data)) {
      return data as unknown as AIModel[];
    }
    return [];
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 上传文件
 */
export const uploadFile = async (file: File): Promise<{ name: string; url: string; path: string }> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/chat/upload/`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Upload failed');
  }

  return response.json();
};
export const getChatSessions = async (): Promise<ChatSession[]> => {
  try {
    const response = await api.get('/api/chat/sessions/');
    const data = handleResponse(response);
    // DRF 分页返回结构 { count: number, next: string, previous: string, results: [] }
    if (data.results && Array.isArray(data.results)) {
      return data.results;
    }
    // 如果未开启分页，直接返回数组
    if (Array.isArray(data)) {
      return data as unknown as ChatSession[];
    }
    return [];
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
    return handleResponse(response) as unknown as ChatSession;
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
