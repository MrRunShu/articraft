import request from '@/utils/request'
import type {
  UserRegisterRequest,
  UserLoginRequest,
  LoginUserVo,
  UserVo,
  UserQueryRequest,
  UserAddRequest,
  UserUpdateRequest,
} from './types.gen'

export const userRegister = (data: UserRegisterRequest) =>
  request.post<any, { data: number }>('/user/register', data)

export const userLogin = (data: UserLoginRequest) =>
  request.post<any, { data: LoginUserVo }>('/user/login', data)

export const userLogout = () =>
  request.post<any, { data: boolean }>('/user/logout')

export const getLoginUser = () =>
  request.get<any, { data: LoginUserVo }>('/user/get/login')

export const getUserById = (id: number) =>
  request.get<any, { data: UserVo }>('/user/get', { params: { id } })

export const listUsers = (data: UserQueryRequest) =>
  request.post<any, { data: { records: UserVo[]; total: number; current: number; size: number } }>(
    '/user/list/page',
    data,
  )

export const addUser = (data: UserAddRequest) =>
  request.post<any, { data: number }>('/user/add', data)

export const updateUser = (data: UserUpdateRequest) =>
  request.post<any, { data: boolean }>('/user/update', data)

export const deleteUser = (id: number) =>
  request.post<any, { data: boolean }>('/user/delete', { id })
