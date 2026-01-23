export interface ExampleItem {
  id: number;
  name: string;
  value: string;
  item_type: string;
  created_at: string;
  updated_at: string;
}

export interface SystemStatus {
  cpu_usage: string;
  memory_usage: string;
  uptime: string;
  status: string;
}

export interface GenerateRandomParams {
  min_val?: number;
  max_val?: number;
}
