import request from '@/utils/request'

export interface ArticleVO {
  id: number
  taskId: string
  topic: string
  style?: string
  mainTitle?: string
  subTitle?: string
  outline?: string
  content?: string
  fullContent?: string
  coverImage?: string
  images?: string
  status: string
  errorMessage?: string
  createTime: string
  completedTime?: string
}

export interface ArticleQueryRequest {
  current?: number
  pageSize?: number
  topic?: string
  status?: string
  [key: string]: unknown
}

export interface PageResult<T> {
  records: T[]
  total: number
  current: number
  size: number
}

export interface ArticleCreateRequest {
  topic: string
  style?: string
}

export const ARTICLE_STYLES = [
  { value: 'POPULAR', label: '爆款新媒体', icon: '🔥' },
  { value: 'PROFESSIONAL', label: '专业深度', icon: '📊' },
  { value: 'HUMOROUS', label: '轻松幽默', icon: '😄' },
  { value: 'STORYTELLING', label: '故事叙述', icon: '📖' },
]

export const IMAGE_METHOD_LABELS: Record<string, string> = {
  PEXELS: 'Pexels 图库',
  PICSUM: 'Picsum 随机',
  NANO_BANANA: 'AI 生图',
  MERMAID: 'Mermaid 流程图',
  ICONIFY: 'Iconify 图标',
  EMOJI_PACK: '表情包',
  SVG_DIAGRAM: 'SVG 示意图',
}

export function createArticle(params: ArticleCreateRequest) {
  return request.post<any, { data: string }>('/article/create', params)
}

export function getArticleDetail(taskId: string) {
  return request.get<any, { data: ArticleVO }>(`/article/${taskId}`)
}

export function listArticle(params: ArticleQueryRequest) {
  return request.post<any, { data: PageResult<ArticleVO> }>('/article/list', params)
}

export function deleteArticle(id: number) {
  return request.post<any, { data: boolean }>('/article/delete', { id })
}

export interface TitleOption {
  mainTitle: string
  subTitle: string
}

export interface OutlineSection {
  section: number
  title: string
  points: string[]
}

export interface ConfirmTitleRequest {
  taskId: string
  selectedMainTitle: string
  selectedSubTitle: string
  userDescription?: string
}

export interface ConfirmOutlineRequest {
  taskId: string
  outline: OutlineSection[]
}

export interface AiModifyOutlineRequest {
  taskId: string
  modifySuggestion: string
}

export function confirmTitle(params: ConfirmTitleRequest) {
  return request.post<any, { data: null }>('/article/confirm-title', params)
}

export function confirmOutline(params: ConfirmOutlineRequest) {
  return request.post<any, { data: null }>('/article/confirm-outline', params)
}

export function aiModifyOutline(params: AiModifyOutlineRequest) {
  return request.post<any, { data: OutlineSection[] }>('/article/ai-modify-outline', params)
}
