import axios from 'axios';
import {
  Dataset,
  DatasetTable,
  UploadResponse,
  PaginatedPreviewResponse,
  DatasetSchemaResponse,
  Relationship,
  TableStatistics,
  HealthResponse
} from '../types/dataset';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const getSessionId = (): string => {
  let sid = localStorage.getItem('sqlens_session_id');
  if (!sid) {
    sid = 'session_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
    localStorage.setItem('sqlens_session_id', sid);
  }
  return sid;
};

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
});

apiClient.interceptors.request.use((config) => {
  config.headers['X-Session-ID'] = getSessionId();
  return config;
});

export const datasetService = {
  async checkHealth(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/health');
    return response.data;
  },

  async uploadDataset(
    file: File,
    onUploadProgress?: (progressEvent: any) => void
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    // Omit explicit Content-Type so browser sets correct boundary header
    const response = await apiClient.post<UploadResponse>('/datasets/upload', formData, {
      onUploadProgress,
    });
    return response.data;
  },

  async getDatasets(): Promise<Dataset[]> {
    const response = await apiClient.get<Dataset[]>('/datasets');
    return response.data;
  },

  async getDataset(datasetId: string): Promise<Dataset> {
    const response = await apiClient.get<Dataset>(`/datasets/${datasetId}`);
    return response.data;
  },

  async getDatasetSchema(datasetId: string): Promise<DatasetSchemaResponse> {
    const response = await apiClient.get<DatasetSchemaResponse>(`/datasets/${datasetId}/schema`);
    return response.data;
  },

  async refreshSchema(datasetId: string): Promise<DatasetSchemaResponse> {
    const response = await apiClient.post<DatasetSchemaResponse>(`/datasets/${datasetId}/schema/refresh`);
    return response.data;
  },

  async getDatasetTables(datasetId: string): Promise<DatasetTable[]> {
    const response = await apiClient.get<DatasetTable[]>(`/datasets/${datasetId}/tables`);
    return response.data;
  },

  async getTableDetails(datasetId: string, tableName: string): Promise<DatasetTable> {
    const response = await apiClient.get<DatasetTable>(`/datasets/${datasetId}/tables/${tableName}`);
    return response.data;
  },

  async getTableStatistics(datasetId: string, tableName: string): Promise<TableStatistics> {
    const response = await apiClient.get<TableStatistics>(`/datasets/${datasetId}/tables/${tableName}/statistics`);
    return response.data;
  },

  async getRelationships(datasetId: string): Promise<Relationship[]> {
    const response = await apiClient.get<Relationship[]>(`/datasets/${datasetId}/relationships`);
    return response.data;
  },

  async getTablePreview(
    datasetId: string,
    tableName: string,
    page: number = 1,
    pageSize: number = 20
  ): Promise<PaginatedPreviewResponse> {
    const response = await apiClient.get<PaginatedPreviewResponse>(
      `/datasets/${datasetId}/preview/${tableName}`,
      {
        params: { page, page_size: pageSize },
      }
    );
    return response.data;
  },

  async deleteDataset(datasetId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.delete<{ success: boolean; message: string }>(
      `/datasets/${datasetId}`
    );
    return response.data;
  },

  async loadSampleDataset(): Promise<UploadResponse> {
    const response = await apiClient.post<UploadResponse>('/datasets/sample');
    return response.data;
  }
};

import {
  AIAnalysisRequest,
  AIClarificationRequest,
  AIAnalysisResponse,
  AIHealthResponse,
  SQLGenerationRequest,
  SQLGenerationResponse,
  SQLValidationRequest,
  SQLValidationResponse,
  QueryExecutionRequest,
  QueryExecutionResponse,
  FullAnalysisRequest,
  FullQueryAnalysisResponse,
  QueryHistoryListResponse,
  QueryHistoryItem,
  FollowupQueryRequest,
  InsightRequest,
  AIInsightResult
} from '../types/ai';

export const aiService = {
  async getAIHealth(): Promise<AIHealthResponse> {
    const response = await apiClient.get<AIHealthResponse>('/ai/health');
    return response.data;
  },

  async analyzeQuestion(payload: AIAnalysisRequest): Promise<AIAnalysisResponse> {
    const response = await apiClient.post<AIAnalysisResponse>('/ai/analyze', payload);
    return response.data;
  },

  async submitClarification(payload: AIClarificationRequest): Promise<AIAnalysisResponse> {
    const response = await apiClient.post<AIAnalysisResponse>('/ai/clarify', payload);
    return response.data;
  },

  async generateSQL(payload: SQLGenerationRequest): Promise<SQLGenerationResponse> {
    const response = await apiClient.post<SQLGenerationResponse>('/ai/generate-sql', payload);
    return response.data;
  },

  async validateSQL(payload: SQLValidationRequest): Promise<SQLValidationResponse> {
    const response = await apiClient.post<SQLValidationResponse>('/ai/validate-sql', payload);
    return response.data;
  },

  async executeQuery(payload: QueryExecutionRequest): Promise<QueryExecutionResponse> {
    const response = await apiClient.post<QueryExecutionResponse>('/query/execute', payload);
    return response.data;
  },

  async executeFullAnalysis(payload: FullAnalysisRequest): Promise<FullQueryAnalysisResponse> {
    const response = await apiClient.post<FullQueryAnalysisResponse>('/query/full-analysis', payload);
    return response.data;
  },

  async generateInsight(payload: InsightRequest): Promise<AIInsightResult | null> {
    const response = await apiClient.post<AIInsightResult | null>('/query/generate-insight', payload);
    return response.data;
  },

  async processFollowup(payload: FollowupQueryRequest): Promise<AIAnalysisResponse> {
    const response = await apiClient.post<AIAnalysisResponse>('/query/follow-up', payload);
    return response.data;
  },

  async getQueryHistory(
    datasetId: string,
    page: number = 1,
    pageSize: number = 20,
    search?: string
  ): Promise<QueryHistoryListResponse> {
    const response = await apiClient.get<QueryHistoryListResponse>(`/query/history/${datasetId}`, {
      params: { page, page_size: pageSize, search }
    });
    return response.data;
  },

  async getQueryHistoryItem(datasetId: string, queryId: string): Promise<QueryHistoryItem> {
    const response = await apiClient.get<QueryHistoryItem>(`/query/history/${datasetId}/${queryId}`);
    return response.data;
  },

  async deleteQueryHistoryItem(datasetId: string, queryId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.delete<{ success: boolean; message: string }>(
      `/query/history/${datasetId}/${queryId}`
    );
    return response.data;
  },

  async rerunQuery(datasetId: string, queryId: string): Promise<FullQueryAnalysisResponse> {
    const response = await apiClient.post<FullQueryAnalysisResponse>(`/query/rerun/${datasetId}/${queryId}`);
    return response.data;
  }
};





