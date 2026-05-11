import request from '@/utils/request'

export interface ArticleVO {
  id: number
  taskId: string
  topic: string
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

export function createArticle(topic: string) {
  return request.post<any, { data: string }>('/article/create', { topic })
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
