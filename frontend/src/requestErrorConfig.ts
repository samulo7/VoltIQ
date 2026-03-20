import type { RequestConfig } from '@umijs/max';
import { history } from '@umijs/max';
import { message } from 'antd';
import type { RequestOptions } from '@@/plugin-request/request';
import { authStorage } from '@/services/voltiq/auth';

const redirectToLogin = () => {
  const redirect = `${window.location.pathname}${window.location.search}`;
  history.push({
    pathname: '/user/login',
    search: new URLSearchParams({ redirect }).toString(),
  });
};

export const errorConfig: RequestConfig = {
  errorConfig: {
    errorHandler: (error: any) => {
      const status = error?.response?.status;
      if (status === 401) {
        authStorage.clear();
        if (window.location.pathname !== '/user/login') {
          redirectToLogin();
        }
        return;
      }

      if (status === 403) {
        message.error('当前角色无权限执行该操作。');
        return;
      }

      const detail = error?.response?.data?.detail;
      if (typeof detail === 'string' && detail.trim()) {
        message.error(detail);
        return;
      }

      message.error('请求失败，请稍后重试。');
    },
  },
  requestInterceptors: [
    (config: RequestOptions) => {
      const token = authStorage.getAccessToken();
      if (!token) return config;
      return {
        ...config,
        headers: {
          ...(config.headers || {}),
          Authorization: `Bearer ${token}`,
        },
      };
    },
  ],
};
