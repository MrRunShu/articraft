import request from '@/utils/request'

export interface CheckoutVO {
  checkoutUrl: string
  sessionId: string
}

export const createCheckout = (productType: string) =>
  request.post<any, { data: CheckoutVO }>('/payment/checkout', { productType })
