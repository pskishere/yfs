import { api, handleResponse, handleError } from '../../../services/api';
import type { ExampleItem, SystemStatus, GenerateRandomParams } from '../types';
import type { ApiResponse } from '../../../types';

const BASE_URL = '/api/example/items';

export const exampleService = {
  /**
   * Get list of example items
   */
  getItems: async (): Promise<ExampleItem[]> => {
    try {
      const response = await api.get<ApiResponse<ExampleItem[]>>(BASE_URL + '/');
      // The backend viewset returns standard DRF paginated response or list depending on config
      // But based on common DRF setup it might return { count: ..., results: ... } or just [...]
      // Let's assume list for now, or check how handleResponse handles it.
      // Actually, handleResponse expects ApiResponse<T> which usually wraps the data.
      // If backend uses default DRF ViewSet, it returns direct JSON.
      // Let's handle it safely.
      const data = handleResponse(response);
      return Array.isArray(data) ? data : (data as any).results || [];
    } catch (error) {
      handleError(error);
      return [];
    }
  },

  /**
   * Generate a random number
   */
  generateRandomNumber: async (params?: GenerateRandomParams): Promise<ExampleItem> => {
    try {
      const response = await api.post<ApiResponse<ExampleItem>>(
        `${BASE_URL}/generate_random/`,
        params
      );
      return handleResponse(response) as unknown as ExampleItem;
    } catch (error) {
      handleError(error);
      throw error;
    }
  },

  /**
   * Check system status
   */
  checkSystemStatus: async (): Promise<ExampleItem> => {
    try {
      const response = await api.get<ApiResponse<ExampleItem>>(`${BASE_URL}/system_status/`);
      return handleResponse(response) as unknown as ExampleItem;
    } catch (error) {
      handleError(error);
      throw error;
    }
  }
};
