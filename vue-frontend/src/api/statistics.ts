import request from '@/utils/request'

export interface StatisticsVO {
  todayCount: number
  weekCount: number
  monthCount: number
  totalCount: number
  successRate: number
  avgDurationMs: number
  activeUserCount: number
  totalUserCount: number
  vipUserCount: number
  quotaUsed: number
}

export function getStatisticsOverview() {
  return request.get<any, { data: StatisticsVO }>('/statistics/overview')
}
