import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, useModel } from '@umijs/max';
import { Alert, App, Space, Typography } from 'antd';
import React from 'react';
import { flushSync } from 'react-dom';
import { Footer } from '@/components';
import {
  authStorage,
  getCurrentUser,
  loginByPassword,
} from '@/services/voltiq/auth';

type LoginFormValues = {
  username: string;
  password: string;
};

const LoginPage: React.FC = () => {
  const { message } = App.useApp();
  const { setInitialState } = useModel('@@initialState');

  const handleLogin = async (values: LoginFormValues) => {
    try {
      const response = await loginByPassword(values);
      authStorage.setTokens(response);
      const currentUser = await getCurrentUser();
      flushSync(() => {
        setInitialState((state) => ({
          ...state,
          currentUser,
        }));
      });

      message.success('登录成功');
      const redirect = new URLSearchParams(window.location.search).get('redirect');
      history.push(redirect || '/welcome');
    } catch (_error) {
      authStorage.clear();
      message.error('登录失败，请检查账号或密码');
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ flex: 1, paddingTop: 96 }}>
        <LoginForm<LoginFormValues>
          title="VoltIQ"
          subTitle="AI 售电业务平台"
          onFinish={handleLogin}
          initialValues={{
            username: 'operator_demo',
            password: 'voltiq123',
          }}
        >
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
            message="Step 16 测试账号"
            description={
              <Space direction="vertical" size={2}>
                <Typography.Text>operator_demo / voltiq123</Typography.Text>
                <Typography.Text>sales_demo / voltiq123</Typography.Text>
                <Typography.Text>manager_demo / voltiq123</Typography.Text>
              </Space>
            }
          />
          <ProFormText
            name="username"
            fieldProps={{
              prefix: <UserOutlined />,
              size: 'large',
            }}
            placeholder="请输入用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
          />
          <ProFormText.Password
            name="password"
            fieldProps={{
              prefix: <LockOutlined />,
              size: 'large',
            }}
            placeholder="请输入密码"
            rules={[{ required: true, message: '请输入密码' }]}
          />
        </LoginForm>
      </div>
      <Footer />
    </div>
  );
};

export default LoginPage;
