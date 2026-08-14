import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AppState {
  model: string;
  setModel: (model: string) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      model: 'deepseek-v3.1:671b-cloud',
      setModel: (model) => set({ model }),
    }),
    { name: 'app-settings' }
  )
);
