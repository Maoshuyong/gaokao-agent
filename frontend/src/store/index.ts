import { create } from 'zustand'

interface AppState {
  // 用户输入
  province: string
  category: string
  score: number
  rank: number | null

  // 结果数据
  controlScores: Array<{ category: string; batch: string; control_score: number | null }>
  colleges: Array<{
    code: string
    name: string
    province: string
    city?: string
    level?: string
    type?: string
    is_985: boolean
    is_211: boolean
    ranking?: number
  }>
  totalColleges: number
  probabilityMap: Record<string, { probability: number | null; level: string }>

  // 状态
  loading: boolean
  currentStep: number // 1-5

  // 操作
  setProfile: (province: string, category: string, score: number, rank: number | null) => void
  setControlScores: (scores: Array<{ category: string; batch: string; control_score: number | null }>) => void
  setColleges: (colleges: AppState['colleges'], total: number) => void
  setProbability: (code: string, probability: number | null, level: string) => void
  setLoading: (loading: boolean) => void
  setStep: (step: number) => void
  reset: () => void
}

export const useAppStore = create<AppState>((set) => ({
  province: '',
  category: '',
  score: 0,
  rank: null,
  controlScores: [],
  colleges: [],
  totalColleges: 0,
  probabilityMap: {},
  loading: false,
  currentStep: 1,

  setProfile: (province, category, score, rank) =>
    set({ province, category, score, rank }),

  setControlScores: (controlScores) =>
    set({ controlScores }),

  setColleges: (colleges, totalColleges) =>
    set({ colleges, totalColleges }),

  setProbability: (code, probability, level) =>
    set((state) => ({
      probabilityMap: { ...state.probabilityMap, [code]: { probability, level } },
    })),

  setLoading: (loading) => set({ loading }),
  setStep: (currentStep) => set({ currentStep }),

  reset: () =>
    set({
      province: '',
      category: '',
      score: 0,
      rank: null,
      controlScores: [],
      colleges: [],
      totalColleges: 0,
      probabilityMap: {},
      loading: false,
      currentStep: 1,
    }),
}))
